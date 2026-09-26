#!/usr/bin/env python3
"""Autonomy tiers: may this change merge without a person approving it?

The reviewer model never approves anything - it returns findings and counts.
This decides, deterministically, from a policy the project's people write
(`.claude/autonomy.json`, read from the BASE branch so a change cannot grant
itself autonomy) whether a reviewed change falls in a tier that may skip human
approval:

  {"tiers": [
    {"name": "docs", "mode": "report",
     "paths": ["docs/**", "**/*.md"],      every changed file must match one
     "max_changed_lines": 300, "max_changed_files": 20,
     "authors": ["dependabot[bot]"]}       optional: only changes by these
  ]}

  mode off      the tier is ignored
  mode report   the review summary says what the tier would have done -
                evidence, before anyone lets it act
  mode approve  the pipeline approves the change on the code host; branch
                protection and CI still decide whether it merges

Whatever a policy says, a change is never eligible when:
  - it touches what steers the agent or the pipeline (NEVER below);
  - the review did not run, or reported a blocking finding or a question.

Usage: autonomy.py decide --policy FILE --diff FILE --result FILE
                          [--author LOGIN] [--out decision.json]
Prints a one-paragraph note for the review summary (nothing when no tier
applies in report or approve mode). Standard library only.
"""

import argparse
import json
import re
import sys

# Files that steer the agent, the review or the pipeline. A change to any of
# them is a policy change, and a policy change is a person's to approve.
NEVER = [
    ".claude/**", ".mcp.json", "**/CLAUDE.md", "CLAUDE.md", "REVIEW.md", "**/CODEOWNERS", "CODEOWNERS",
    ".github/**", ".gitlab/**", ".gitlab-ci.yml", "bands.yaml", "docs/intents/**",
]
MODES = ("off", "report", "approve")


def glob_re(pattern):
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif pattern.startswith("**", i):
            out, i = out + ".*", i + 2
        elif pattern[i] == "*":
            out, i = out + "[^/]*", i + 1
        elif pattern[i] == "?":
            out, i = out + "[^/]", i + 1
        else:
            out, i = out + re.escape(pattern[i]), i + 1
    return re.compile(out + r"\Z")


def matches(path, patterns):
    return any(glob_re(p).match(path) for p in patterns)


def diff_stats(text):
    files, lines = set(), 0
    for raw in text.splitlines():
        if raw.startswith("diff --git "):
            m = re.match(r"diff --git a/(.*) b/(.*)$", raw)
            if m:
                files.update(m.groups())
        elif raw.startswith(("+++", "---")):
            continue
        elif raw.startswith(("+", "-")):
            lines += 1
    return sorted(files), lines


def decide(policy, diff_text, result, author=""):
    files, lines = diff_stats(diff_text)
    tiers = [t for t in (policy or {}).get("tiers", []) if t.get("mode", "off") in ("report", "approve")]
    if not tiers:
        return {"tier": None, "mode": "off", "eligible": False, "reasons": ["no tier in report or approve mode"]}
    blockers = []
    if not isinstance(result, dict) or "blocking" not in result:
        blockers.append("the review did not produce a result")
    else:
        if result.get("blocking", 1):
            blockers.append(f"the review reported {result['blocking']} blocking finding(s)")
        if result.get("questions", 1):
            blockers.append(f"the review left {result['questions']} question(s) for a person")
    steering = [f for f in files if matches(f, NEVER)]
    if steering:
        blockers.append("it changes what steers the agent or the pipeline: " + ", ".join(f"`{f}`" for f in steering[:5]))
    if not files:
        return {"tier": None, "mode": "report", "eligible": False, "reasons": ["the diff names no files"]}

    reasons = []
    for t in tiers:
        name = t.get("name", "?")
        if t.get("mode") not in MODES:
            reasons.append(f"`{name}`: mode must be one of {', '.join(MODES)}")
            continue
        outside = [f for f in files if not matches(f, t.get("paths", []))]
        if outside:
            reasons.append(f"`{name}`: {len(outside)} file(s) outside its paths, e.g. `{outside[0]}`")
            continue
        if lines > t.get("max_changed_lines", 0):
            reasons.append(f"`{name}`: {lines} changed lines, over its {t.get('max_changed_lines', 0)}")
            continue
        if len(files) > t.get("max_changed_files", 10 ** 9):
            reasons.append(f"`{name}`: {len(files)} files, over its {t['max_changed_files']}")
            continue
        if t.get("authors") and author not in t["authors"]:
            reasons.append(f"`{name}`: author `{author or 'unknown'}` is not one of its authors")
            continue
        if blockers:
            return {"tier": name, "mode": t["mode"], "eligible": False, "reasons": blockers}
        return {"tier": name, "mode": t["mode"], "eligible": True,
                "reasons": [f"{len(files)} file(s), {lines} changed lines, all within `{name}`; review: 0 blocking, 0 questions"]}
    return {"tier": None, "mode": "report", "eligible": False, "reasons": reasons}


def note(d):
    if d["mode"] == "off" and d["tier"] is None:
        return ""
    if d["eligible"] and d["mode"] == "approve":
        head = f"**Autonomy:** within tier `{d['tier']}` - approved by the project's autonomy policy, not by a person."
    elif d["eligible"]:
        head = f"**Autonomy:** within tier `{d['tier']}` (report mode) - would have been approved without a person."
    elif d["tier"]:
        head = f"**Autonomy:** tier `{d['tier']}` would apply, but a person must approve:"
    else:
        head = "**Autonomy:** no tier applies - a person approves:"
    body = "" if d["eligible"] else " " + "; ".join(d["reasons"]) + "."
    return head + body + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("decide")
    p.add_argument("--policy", required=True)
    p.add_argument("--diff", required=True)
    p.add_argument("--result", required=True)
    p.add_argument("--author", default="")
    p.add_argument("--out")
    args = ap.parse_args(argv)

    try:
        with open(args.policy, encoding="utf-8") as f:
            policy = json.load(f)
    except (OSError, ValueError) as e:
        print(f"autonomy: cannot read the policy ({e}) - treated as no tiers", file=sys.stderr)
        policy = {}
    with open(args.diff, encoding="utf-8", errors="replace") as f:
        diff_text = f.read()
    try:
        with open(args.result, encoding="utf-8") as f:
            result = json.load(f)
    except (OSError, ValueError):
        result = None
    d = decide(policy, diff_text, result, args.author)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(d, f)
    sys.stdout.write(note(d))
    return 0


if __name__ == "__main__":
    sys.exit(main())
