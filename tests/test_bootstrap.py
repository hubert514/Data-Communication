"""Setup safety checks against disposable Git repositories, with no network."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "ns3_tools", Path(__file__).resolve().parents[1] / "scripts/ns3_tools.py"
)
tools = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tools)


class CommandRunner:
    def command(self, args, cwd=None):
        subprocess.run([str(arg) for arg in args], cwd=cwd, check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)


class SetupSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        upstream = root / ".local/ns-3"
        upstream.mkdir(parents=True)
        (root / "patches").mkdir()
        (root / "patches/series").write_text("# no patches\n", encoding="utf-8")
        self.upstream = upstream
        self.root = root
        self.git("init", "--quiet")
        self.git("config", "user.name", "Bootstrap test")
        self.git("config", "user.email", "bootstrap-test@example.invalid")
        self.git("config", "core.autocrlf", "false")
        (upstream / "NOTICE").write_bytes(b"original\n")
        self.git("add", "NOTICE")
        self.git("commit", "--quiet", "-m", "fixture")
        commit = self.git("rev-parse", "HEAD").strip().decode()
        self.override = patch.multiple(
            tools, ROOT=root, LOCAL=root / ".local", UPSTREAM=upstream,
            STATE=root / ".local/ns3-state.json", LOCK={"commit": commit}
        )
        self.override.start()
        self.addCleanup(self.override.stop)

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.upstream,
                                       stderr=subprocess.PIPE)

    def test_clean_setup_is_idempotent(self):
        tools.setup(CommandRunner())
        state = tools.STATE.read_bytes()
        tools.setup(CommandRunner())
        self.assertEqual(state, tools.STATE.read_bytes())
        self.assertEqual(b"", self.git("status", "--porcelain"))

    def test_unknown_tracked_edits_are_preserved_and_rejected(self):
        tools.setup(CommandRunner())
        notice = self.upstream / "NOTICE"
        notice.write_bytes(b"engineer local edits\n")
        with self.assertRaisesRegex(RuntimeError, "Unrecognized upstream changes"):
            tools.setup(CommandRunner())
        self.assertEqual(b"engineer local edits\n", notice.read_bytes())

    def test_untracked_files_are_preserved_and_rejected(self):
        local_file = self.upstream / "unfinished-work.txt"
        local_file.write_bytes(b"keep me")
        with self.assertRaisesRegex(RuntimeError, "untracked files"):
            tools.setup(CommandRunner())
        self.assertEqual(b"keep me", local_file.read_bytes())

    def test_wrong_commit_is_rejected_without_reset(self):
        actual = self.git("rev-parse", "HEAD")
        with patch.dict(tools.LOCK, {"commit": "0" * 40}):
            with self.assertRaisesRegex(RuntimeError, "HEAD differs"):
                tools.setup(CommandRunner())
        self.assertEqual(actual, self.git("rev-parse", "HEAD"))

    def test_managed_patch_repeats_and_changed_patch_is_rejected(self):
        notice = self.upstream / "NOTICE"
        notice.write_bytes(b"original\nreviewed addition\n")
        patch_data = self.git("diff", "--binary")
        notice.write_bytes(b"original\n")
        patch_file = self.root / "patches/001-notice.patch"
        patch_file.write_bytes(patch_data)
        (self.root / "patches/series").write_text("001-notice.patch\n", encoding="utf-8")
        tools.setup(CommandRunner())
        expected = notice.read_bytes()
        tools.setup(CommandRunner())
        self.assertEqual(expected, notice.read_bytes())
        patch_file.write_bytes(patch_data + b"\n")
        with self.assertRaisesRegex(RuntimeError, "changed patch inputs"):
            tools.setup(CommandRunner())
        self.assertEqual(expected, notice.read_bytes())

    def test_patch_can_add_a_file_without_becoming_unknown_work(self):
        patch_file = self.root / "patches/001-new-file.patch"
        patch_file.write_bytes(
            b"diff --git a/added.txt b/added.txt\n"
            b"new file mode 100644\n"
            b"--- /dev/null\n+++ b/added.txt\n"
            b"@@ -0,0 +1 @@\n+reviewed addition\n"
        )
        (self.root / "patches/series").write_text("001-new-file.patch\n", encoding="utf-8")
        tools.setup(CommandRunner())
        tools.setup(CommandRunner())
        tools.verify_checkout()
        self.assertEqual(b"reviewed addition\n", (self.upstream / "added.txt").read_bytes())


if __name__ == "__main__":
    unittest.main()
