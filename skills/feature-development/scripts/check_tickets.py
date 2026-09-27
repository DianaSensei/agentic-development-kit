#!/usr/bin/env python3
"""check_tickets.py - hold solution-architect's tickets to the ticket format, and grade them.

    check_tickets.py <tickets.json>    list what each ticket is missing, then each ticket's tier;
                                       exit 1 if anything is missing

The input is the architect's tickets output - {"proposal_id", "tickets": [...]} - or text holding
it in a ```json block. The format, the tiers and what a tier decides are
references/tickets.md. A ticket is tight when an implementer on a cheaper model can build it without
redesigning it: an interface (or a reason for none), a pattern to follow at a path:line (or a
reason for none), tests in Given/When/Then, and a done_when. Anything else is loose, and is built on
the session's model.
"""

import json
import re
import sys

PATH_LINE = re.compile(r"[\w./-]+\.\w+:\d+")
REQUIRED = ("id", "task", "files")


def load(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    block = re.search(r"```json\s*\n(.*?)\n```", text, re.S)
    if not block:
        raise SystemExit(f"{path}: neither JSON nor a ```json block")
    return json.loads(block.group(1))


def text(value):
    return isinstance(value, str) and bool(value.strip())


def nonempty_list(value):
    return isinstance(value, list) and len(value) > 0


def gwt(test):
    """A test written as Given/When/Then - a string, or an object with those keys."""
    if isinstance(test, dict):
        return all(text(test.get(k)) for k in ("given", "when", "then"))
    if not text(test):
        return False
    t = test.lower()
    return "when" in t and "then" in t


def check_ticket(t):
    """(problems, gaps): problems are malformed fields; gaps are what keeps the ticket from tight."""
    tid = t.get("id", "?") if isinstance(t, dict) else "?"
    problems, gaps = [], []
    if not isinstance(t, dict):
        return [f"{tid}: not an object"], ["everything"]
    for key in REQUIRED:
        if not (text(t.get(key)) or nonempty_list(t.get(key))):
            problems.append(f"{tid}: {key} missing")

    if nonempty_list(t.get("interface")):
        if not all(text(i) for i in t["interface"]):
            problems.append(f"{tid}: interface has an empty entry")
    elif not text(t.get("no_interface_reason")):
        gaps.append("interface")

    patterns = t.get("follow_pattern")
    if nonempty_list(patterns):
        for p in patterns:
            at = p.get("at") if isinstance(p, dict) else None
            if not (text(at) and PATH_LINE.search(at)):
                problems.append(f"{tid}: follow_pattern entry {p!r} has no path:line in `at`")
            if isinstance(p, dict) and not text(p.get("what")):
                problems.append(f"{tid}: follow_pattern entry at {at!r} does not say what to copy")
    elif not text(t.get("no_pattern_reason")):
        gaps.append("follow_pattern")

    tests = t.get("tests")
    if nonempty_list(tests):
        bad = [x for x in tests if not gwt(x)]
        if bad:
            problems.append(f"{tid}: tests not written as Given/When/Then: {bad!r}")
    else:
        gaps.append("tests")

    if not (text(t.get("done_when")) or nonempty_list(t.get("done_when"))):
        gaps.append("done_when")

    for key in ("must_not", "stop_if"):
        if key in t and not isinstance(t[key], list):
            problems.append(f"{tid}: {key} must be a list")
    return problems, gaps


def check(data):
    tickets = data.get("tickets") if isinstance(data, dict) else None
    if not nonempty_list(tickets):
        return ["tickets: none"], {}
    problems, tiers = [], {}
    ids = [t.get("id") for t in tickets if isinstance(t, dict)]
    for t in tickets:
        p, gaps = check_ticket(t)
        problems += p
        tid = t.get("id", "?") if isinstance(t, dict) else "?"
        tiers[tid] = ("tight", []) if not gaps and not p else ("loose", gaps)
        for dep in (t.get("depends_on") or []) if isinstance(t, dict) else []:
            if dep not in ids:
                problems.append(f"{tid}: depends_on {dep!r}, which is not a ticket")
    if len(set(ids)) != len(ids):
        problems.append("two tickets share an id")
    return problems, tiers


def main(argv):
    if len(argv) != 1:
        print("usage: check_tickets.py <tickets.json>", file=sys.stderr)
        return 2
    data = load(argv[0])
    problems, tiers = check(data)
    for p in problems:
        print(f"problem: {p}")
    for tid, (tier, gaps) in tiers.items():
        why = f" - missing {', '.join(gaps)}" if gaps else ""
        print(f"tier: {tid} {tier}{why}")
    missing = any(gaps for _, gaps in tiers.values())
    if problems or missing:
        return 1
    print(f"OK: {len(tiers)} ticket(s), all tight")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
