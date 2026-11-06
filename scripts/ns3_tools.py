#!/usr/bin/env python3
"""Candidate ns-3 setup/build/example probe; no project scheduler is implemented."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local"
UPSTREAM = LOCAL / "ns-3"
STATE = LOCAL / "ns3-state.json"
LOCK = json.loads((ROOT / "configs/ns3-candidate.json").read_text(encoding="utf-8"))


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def probe(args, cwd=ROOT):
    try:
        result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)
        return result.stdout.strip() if result.returncode == 0 else None
    except OSError:
        return None


class Evidence:
    def __init__(self, action):
        self.path = LOCAL / "evidence" / (
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            + "-" + action + "-" + uuid.uuid4().hex[:8]
        )
        self.path.mkdir(parents=True, exist_ok=False)
        self.data = {
            "schema": "bootstrap-operation-v1",
            "operation": action,
            "run_id": self.path.name,
            "status": "running",
            "started_at": now(),
            "finished_at": None,
            "invocation": [sys.executable, *sys.argv],
            "working_directory": str(Path.cwd()),
            "project_sha": probe(["git", "rev-parse", "HEAD"]),
            "project_dirty": probe(["git", "status", "--porcelain"]),
            "candidate": LOCK,
            "upstream_sha": None,
            "upstream_diff_sha256": None,
            "os": platform.platform(),
            "python": sys.version,
            "compiler": None,
            "cmake": None,
            "config": None,
            "scheduler": None,
            "seed": None,
            "run": None,
            "commands": [],
            "checksums": {},
            "dl_mu_gate": "TODO_REVIEW",
        }
        for compiler in (os.environ.get("CXX"), "c++", "g++", "clang++"):
            if compiler and shutil.which(compiler):
                self.data["compiler"] = probe([compiler, "--version"])
                break
        if shutil.which("cmake"):
            self.data["cmake"] = probe(["cmake", "--version"])
        self.save()

    def save(self):
        (self.path / "run_metadata.json").write_text(
            json.dumps(self.data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    def command(self, args, cwd=ROOT, env=None):
        args = [str(arg) for arg in args]
        filename = f"{len(self.data['commands']) + 1:02d}.log"
        record = {"argv": args, "cwd": str(cwd), "log": filename,
                  "started_at": now(), "returncode": None}
        if env is not None:
            record["environment_overrides"] = {
                key: env[key] for key in ("NS_LOG",) if key in env
            }
        self.data["commands"].append(record)
        self.save()
        print("+ " + shlex.join(args), flush=True)
        try:
            with (self.path / filename).open("w", encoding="utf-8") as log:
                result = subprocess.run(args, cwd=cwd, env=env, stdout=log,
                                        stderr=subprocess.STDOUT, check=False)
            record["returncode"] = result.returncode
        finally:
            record["finished_at"] = now()
            self.save()
        if result.returncode:
            tail = (self.path / filename).read_text(encoding="utf-8", errors="replace")
            print("\n".join(tail.splitlines()[-20:]), file=sys.stderr)
            raise RuntimeError(f"Command failed ({result.returncode}); inspect {self.path / filename}")

    def finish(self, status, error=None):
        self.data.update(status=status, error=error, finished_at=now())
        if (UPSTREAM / ".git").exists():
            self.data["upstream_sha"] = probe(["git", "rev-parse", "HEAD"], UPSTREAM)
            try:
                self.data["upstream_diff_sha256"] = worktree_fingerprint()
            except (OSError, subprocess.CalledProcessError):
                pass
        self.data["checksums"] = {
            path.name: digest(path.read_bytes()) for path in self.path.glob("*.log")
        }
        self.data["input_checksums"] = {
            path.relative_to(ROOT).as_posix(): digest(path.read_bytes())
            for path in [ROOT / "configs/ns3-candidate.json", ROOT / "patches/series",
                         ROOT / "scripts/ns3_tools.py"]
        }
        self.save()
        print(f"Evidence: {self.path}", flush=True)


def require_tools(*names):
    missing = [name for name in names if not shutil.which(name)]
    if missing:
        raise RuntimeError("Missing prerequisite(s): " + ", ".join(missing)
                           + ". See docs/ENVIRONMENT.md; no system packages were installed.")


def checked_bytes(args):
    return subprocess.check_output(args, cwd=UPSTREAM, stderr=subprocess.STDOUT)


def worktree_fingerprint():
    # Include staged and unstaged changes against HEAD; build files follow upstream ignores.
    return digest(checked_bytes(["git", "diff", "HEAD", "--binary", "--no-ext-diff"]))


def patch_inputs():
    patch_dir = ROOT / "patches"
    files = []
    for line in (patch_dir / "series").read_text(encoding="utf-8").splitlines():
        name = line.strip()
        if not name or name.startswith("#"):
            continue
        path = (patch_dir / name).resolve()
        if not path.is_relative_to(patch_dir.resolve()) or not path.is_file() or path.suffix != ".patch":
            raise RuntimeError(f"Invalid patch entry: {name}")
        if path in files:
            raise RuntimeError(f"Duplicate patch entry: {name}")
        files.append(path)
    listed = {path.resolve() for path in files}
    actual = {path.resolve() for path in patch_dir.rglob("*.patch")}
    if actual != listed:
        raise RuntimeError("Every tracked .patch must be listed exactly once in patches/series.")
    return files, {path.relative_to(ROOT).as_posix(): digest(path.read_bytes()) for path in files}


def verify_checkout(require_state=True):
    require_tools("git")
    if not (UPSTREAM / ".git").is_dir():
        raise RuntimeError("Missing complete .local/ns-3 checkout; run setup first. Partial paths are preserved.")
    if probe(["git", "rev-parse", "HEAD"], UPSTREAM) != LOCK["commit"]:
        raise RuntimeError("Upstream HEAD differs from candidate pin; review manually. Nothing was reset.")
    if checked_bytes(["git", "ls-files", "--others", "--exclude-standard"]):
        raise RuntimeError("Upstream contains untracked files; review them manually. Nothing was overwritten.")
    files, hashes = patch_inputs()
    fingerprint = worktree_fingerprint()
    old = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else None
    dirty = bool(checked_bytes(["git", "status", "--porcelain"]))
    if dirty and (not old or old.get("commit") != LOCK["commit"]
                  or old.get("patches") != hashes or old.get("diff_sha256") != fingerprint):
        raise RuntimeError("Unrecognized upstream changes or changed patch inputs; commit/export/review manually. Nothing was reset.")
    if require_state and (not old or old.get("commit") != LOCK["commit"]
                          or old.get("patches") != hashes or old.get("diff_sha256") != fingerprint):
        raise RuntimeError("Setup state does not match checkout/patches; run setup or review local changes.")
    return files, hashes, dirty, fingerprint


def setup(evidence):
    require_tools("git")
    if not UPSTREAM.exists():
        evidence.command(["git", "clone", "--depth", "1", "--branch", LOCK["tag"],
                          LOCK["repository"], UPSTREAM])
    files, hashes, dirty, _ = verify_checkout(require_state=False)
    if not dirty:
        for path in files:
            # Index new files too, so managed additions are distinguishable from
            # unrelated untracked work on subsequent invocations.
            evidence.command(["git", "apply", "--check", "--index", path], cwd=UPSTREAM)
            evidence.command(["git", "apply", "--index", path], cwd=UPSTREAM)
    STATE.write_text(json.dumps({"commit": LOCK["commit"], "patches": hashes,
                                 "diff_sha256": worktree_fingerprint()}, indent=2)
                     + "\n", encoding="utf-8")
    print("Candidate checkout prepared. TODO: build, execute example, inspect DL MU evidence and obtain PM acceptance.")


def build(evidence):
    verify_checkout()
    require_tools("cmake")
    if not any(shutil.which(name) for name in ("ninja", "make")):
        raise RuntimeError("Missing Ninja/Make; see docs/ENVIRONMENT.md.")
    if evidence.data["compiler"] is None:
        raise RuntimeError("No C++ compiler found. Set CXX to the chosen compiler executable.")
    evidence.command([sys.executable, "ns3", "configure", "--enable-examples", "--enable-tests",
                      "--build-profile=debug"], cwd=UPSTREAM)
    evidence.command([sys.executable, "ns3", "build", "wifi-he-network"], cwd=UPSTREAM)


def smoke(evidence):
    verify_checkout()
    require_tools("cmake")
    options = {
        "udp": 1, "downlink": 1, "nStations": 8, "maxMuStas": 4,
        "dlAckType": "MU-BAR", "enableUlOfdma": 0, "enableBsrp": 0,
        "frequency": 5, "channelWidth": 20, "mcs": 5,
        "guardInterval": 800, "simulationTime": "2s", "distance": 5,
        "RngSeed": 1, "RngRun": 1,
    }
    evidence.data.update(config=options, scheduler="upstream-RrMultiUserScheduler",
                         seed=1, run=1)
    env = os.environ.copy()
    env["NS_LOG"] = ("RrMultiUserScheduler=level_all|prefix_time:"
                     "MultiUserScheduler=level_all|prefix_time:"
                     "HeFrameExchangeManager=level_debug|prefix_time")
    example = "wifi-he-network " + " ".join(f"--{key}={value}" for key, value in options.items())
    evidence.command([sys.executable, "ns3", "run", example], cwd=UPSTREAM, env=env)
    print("Official example exited zero. TODO: inspect actual DL MU, served STA IDs and RUs; no OFDMA gate is certified.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("setup", "build", "smoke"))
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        parser.error("Python 3.10+ required")
    if LOCAL.is_symlink() or UPSTREAM.is_symlink():
        parser.error("Refusing symlinked .local or ns-3 directory")
    evidence = Evidence(args.operation)
    try:
        {"setup": setup, "build": build, "smoke": smoke}[args.operation](evidence)
    except (RuntimeError, OSError, ValueError, subprocess.CalledProcessError) as error:
        evidence.finish("failed", str(error))
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    evidence.finish("executed_pending_dl_mu_review" if args.operation == "smoke" else "completed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
