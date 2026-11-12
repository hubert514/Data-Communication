#!/usr/bin/env bash
# Recompute A-ENV-01 counts from raw logs. Usage: recompute.sh <sched_log> <phy_log>
# sched_log = manual-dlmu-01/run.log (or smoke 01.log); phy_log = manual-dlmu-02/run.log
set -euo pipefail
S="${1:?scheduler log}"; P="${2:?phy log}"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT

echo "== scheduler decisions =="
grep "stations are being assigned" "$S" | cut -d' ' -f1 > "$T/sched_t"
wc -l < "$T/sched_t"

echo "== PHY HE_MU Send (MU path, single line each) =="
grep "WifiPhy:Send(" "$P" | grep "preamble: HE_MU" > "$T/phy_mu"
cut -d' ' -f1 "$T/phy_mu" > "$T/phy_t"
wc -l < "$T/phy_mu"

echo "== timestamps identical? =="
diff "$T/sched_t" "$T/phy_t" && echo "all times match"

echo "== users per HE_MU =="
grep -o "num User Infos: [0-9]*" "$T/phy_mu" | sort | uniq -c
echo "== RU types =="
grep -o "RU{[0-9]*-tones" "$T/phy_mu" | sort | uniq -c
echo "== RU index per STA-ID =="
grep -o "{STA-ID: [0-9]*, RU{[0-9]*-tones/[0-9]*" "$T/phy_mu" | sort | uniq -c
echo "== sending PHY pointers =="
grep -o "WifiPhy:Send(0x[0-9a-f]*" "$T/phy_mu" | sort | uniq -c

echo "== Trigger frames: raw vs wrapper-deduplicated =="
grep "WifiPhy:Send(" "$P" | grep "CTL_TRIGGER" > "$T/trig"
echo "raw lines: $(wc -l < "$T/trig")  unique lines: $(sort -u "$T/trig" | wc -l)"

echo "== BlockAck: raw vs deduplicated =="
grep "WifiPhy:Send(" "$P" | grep "CTL_BACKRESP" > "$T/ba"
echo "raw lines: $(wc -l < "$T/ba")  PSDU-map lines: $(grep -c '\[PSDU for' "$T/ba")"

echo "== last HE_MU / last trigger =="
tail -n 1 "$T/phy_t"
tail -n 1 "$T/trig" | cut -d' ' -f1
