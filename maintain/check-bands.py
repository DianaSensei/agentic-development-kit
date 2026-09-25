#!/usr/bin/env python3
"""Deterministic control-band check - the detection half of the maintain loop.

Each band in bands.yaml is a command whose stdout is one number, and the range
that number must stay in. This script runs every command and reports each band
as ok, breach, or error. No model is involved here: the playbook's rule is that
detection is deterministic and the model is invoked only after it, on what it
found.

Usage: check-bands.py <bands.yaml> [--out results.json]
Exit: 0 when the file was valid (whatever the bands found), 2 when it was not.
"""
import json
import os
import subprocess
import sys

try:
    import yaml
except ImportError:
    sys.exit("check-bands: needs PyYAML (pip install pyyaml)")

TIERS = ("observe", "propose")
OUTPUT_LIMIT = 2000  # characters of command output kept as evidence

# Output becomes evidence in an intent file that gets committed. GitHub masks
# secrets in logs, not in files, so every secret value the commands could see is
# replaced before anything is written. CHECK_BANDS_REDACT holds those values,
# one per line; the workflow fills it from BANDS_ENV and GH_TOKEN.
SECRETS = sorted({v for v in os.environ.get("CHECK_BANDS_REDACT", "").splitlines() if len(v) >= 6},
                 key=len, reverse=True)


def redact(text):
    for value in SECRETS:
        text = text.replace(value, "[redacted]")
    return text


def fail(msg):
    print(f"check-bands: {msg}", file=sys.stderr)
    sys.exit(2)


def load(path):
    try:
        with open(path) as f:
            doc = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError) as e:
        fail(f"cannot read {path}: {e}")
    bands = doc.get("bands")
    if not isinstance(bands, list) or not bands:
        fail(f"{path}: needs a non-empty 'bands' list")
    names = set()
    for i, b in enumerate(bands):
        where = f"{path}: bands[{i}]"
        if not isinstance(b, dict):
            fail(f"{where} is not a mapping")
        for key in ("name", "command"):
            if not isinstance(b.get(key), str) or not b[key].strip():
                fail(f"{where} needs a non-empty '{key}'")
        if b["name"] in names:
            fail(f"{where}: duplicate name '{b['name']}'")
        names.add(b["name"])
        if "min" not in b and "max" not in b:
            fail(f"{where} ('{b['name']}') needs 'min', 'max', or both")
        for key in ("min", "max"):
            if key in b and (isinstance(b[key], bool) or not isinstance(b[key], (int, float))):
                fail(f"{where} ('{b['name']}'): '{key}' must be a number")
        if "min" in b and "max" in b and b["min"] > b["max"]:
            fail(f"{where} ('{b['name']}'): min is above max")
        b.setdefault("tier", "propose")
        if b["tier"] not in TIERS:
            fail(f"{where} ('{b['name']}'): tier must be one of {', '.join(TIERS)}")
        timeout = b.setdefault("timeout_seconds", 60)
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
            fail(f"{where} ('{b['name']}'): timeout_seconds must be a positive number")
    return bands


def check(band):
    result = {k: band.get(k) for k in ("name", "command", "min", "max", "tier", "owner", "runbook")}
    result["command"] = redact(result["command"])
    try:
        proc = subprocess.run(band["command"], shell=True, capture_output=True, text=True,
                              timeout=band["timeout_seconds"])
    except subprocess.TimeoutExpired:
        return {**result, "status": "error", "value": None,
                "reason": f"timed out after {band['timeout_seconds']}s", "output": ""}
    output = redact((proc.stdout + ("\n" + proc.stderr if proc.stderr else "")).strip())[-OUTPUT_LIMIT:]
    if proc.returncode != 0:
        return {**result, "status": "error", "value": None,
                "reason": f"command exited {proc.returncode}", "output": output}
    try:
        value = float(proc.stdout.strip())
    except ValueError:
        return {**result, "status": "error", "value": None,
                "reason": "stdout is not a single number", "output": output}
    breached = ("min" in band and value < band["min"]) or ("max" in band and value > band["max"])
    reason = ""
    if breached:
        reason = f"{value:g} is below min {band['min']:g}" if "min" in band and value < band["min"] \
            else f"{value:g} is above max {band['max']:g}"
    return {**result, "status": "breach" if breached else "ok", "value": value,
            "reason": reason, "output": output}


def main(argv):
    if not argv or argv[0].startswith("-"):
        fail("usage: check-bands.py <bands.yaml> [--out results.json]")
    out = None
    if "--out" in argv:
        i = argv.index("--out")
        if i + 1 >= len(argv):
            fail("--out needs a path")
        out = argv[i + 1]
    results = [check(b) for b in load(argv[0])]
    doc = json.dumps(results, indent=2)
    if out:
        with open(out, "w") as f:
            f.write(doc + "\n")
    print(doc)
    for r in results:
        detail = f"{r['value']:g}" if r["value"] is not None else r["reason"]
        print(f"{r['status']:>6}  {r['name']}  ({detail})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
