#!/usr/bin/env python3
"""Judge shipped intents' bets from the control bands - the loop's last step.

An intent is a bet: a problem, and a success signal that says whether solving
it worked. Marking it `done` records that the change shipped, not that the bet
paid off. This closes that gap without a model: an intent whose `signal_band`
names a band in bands.yaml is judged by that band once it has been done for a
while (`--after-days`, default 14):

  band ok     -> resolution: met
  band breach -> resolution: not-met
  band error, or no such band -> left open, reported

The verdict goes into the intent's frontmatter (`resolution`, `updated`) and a
Decision log line. Nothing else in the file is touched.

Usage: resolve-bets.py <results.json> [--intents DIR] [--after-days N]
                       [--today YYYY-MM-DD] [--run-url URL] [--dry-run]

Prints one line per intent it looked at:
  resolved <path> met|not-met <detail>     (would-resolve with --dry-run)
  waiting <path> <detail>                  done too recently to judge
  open <path> <detail>                     the band could not give a verdict
Standard library only.
"""

import argparse
import datetime
import json
import os
import re
import sys

FM = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def frontmatter(text):
    m = FM.match(text)
    fm = {}
    for line in (m.group(1).splitlines() if m else []):
        k, sep, v = line.partition(":")
        if sep:
            fm[k.strip()] = v.strip()
    return fm


def set_keys(text, values):
    """Set frontmatter keys in place; a key not present is added before the closing ---."""
    m = FM.match(text)
    lines = m.group(1).splitlines()
    for key, value in values.items():
        for i, line in enumerate(lines):
            if line.split(":", 1)[0].strip() == key:
                lines[i] = f"{key}: {value}"
                break
        else:
            lines.append(f"{key}: {value}")
    return "---\n" + "\n".join(lines) + "\n---\n" + text[m.end():]


def number(v):
    if v is None:
        return ""
    return str(int(v)) if float(v).is_integer() else str(v)


def band_range(r):
    lo, hi = r.get("min"), r.get("max")
    if lo is not None and hi is not None:
        return f"{number(lo)}..{number(hi)}"
    return f">= {number(lo)}" if lo is not None else f"<= {number(hi)}"


def judge(path, text, bands, today, after_days):
    """(action, verdict, detail): action is resolve | waiting | open | skip."""
    fm = frontmatter(text)
    band = fm.get("signal_band", "")
    if fm.get("status") != "done" or not band or fm.get("resolution"):
        return "skip", None, ""
    try:
        shipped = datetime.date.fromisoformat(fm.get("updated", ""))
    except ValueError:
        return "open", None, f"`updated` is not a date: {fm.get('updated')!r}"
    due = shipped + datetime.timedelta(days=after_days)
    if today < due:
        return "waiting", None, f"`{band}` judged from {due.isoformat()}"
    r = bands.get(band)
    if r is None:
        return "open", None, f"no band named `{band}` in the results"
    if r["status"] == "error":
        return "open", None, f"`{band}` could not measure: {r.get('reason') or 'error'}"
    verdict = "met" if r["status"] == "ok" else "not-met"
    return "resolve", verdict, f"`{band}` = {number(r.get('value'))} (band {band_range(r)})"


def resolve(text, verdict, detail, today, run_url):
    text = set_keys(text, {"resolution": verdict, "updated": today.isoformat()})
    line = f"- {today.isoformat()} - bet resolved as {verdict.replace('-', ' ')}: {detail} - maintain loop"
    if run_url:
        line += f", {run_url}"
    return text.rstrip("\n") + "\n" + line + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("results")
    ap.add_argument("--intents", default="docs/intents")
    ap.add_argument("--after-days", type=int, default=14)
    ap.add_argument("--today", default="")
    ap.add_argument("--run-url", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    with open(args.results, encoding="utf-8") as f:
        bands = {r["name"]: r for r in json.load(f)}
    today = datetime.date.fromisoformat(args.today) if args.today else datetime.date.today()
    if not os.path.isdir(args.intents):
        return 0
    for name in sorted(os.listdir(args.intents)):
        if not name.endswith(".md"):
            continue
        path = os.path.join(args.intents, name)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        action, verdict, detail = judge(path, text, bands, today, args.after_days)
        if action == "skip":
            continue
        if action != "resolve":
            print(f"{action} {path} {detail}")
            continue
        if args.dry_run:
            print(f"would-resolve {path} {verdict} {detail}")
            continue
        with open(path, "w", encoding="utf-8") as f:
            f.write(resolve(text, verdict, detail, today, args.run_url))
        print(f"resolved {path} {verdict} {detail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
