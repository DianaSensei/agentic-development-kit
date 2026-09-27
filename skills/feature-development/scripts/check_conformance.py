#!/usr/bin/env python3
"""check_conformance.py - does the change do what its tickets said, and nothing else?

    check_conformance.py [--base <commit>] <plan.md | tickets.json>

Run from the project root, after the units are applied and before Step 3.2's review. It compares the
working tree against <commit> (default HEAD) - tracked changes and untracked, non-ignored files -
with the tickets: the plan's `## Tickets` JSON block, or a tickets file.

It checks what a machine can:
  - every changed path is inside some ticket's `files` (the workflow's own records - docs/plans,
    docs/intents, docs/changelog, docs/knowledge, .claude/ - are not code and never count);
  - every file a ticket names was changed;
  - every name in a ticket's `interface` appears in that ticket's files.
Whether the pattern was followed, the tests written and `must_not` respected is judgment: the lead
reads those against each ticket (references/tickets.md, "Conformance").
"""

import json
import os
import re
import subprocess
import sys

WORKFLOW_PATHS = re.compile(r"^(docs/(plans|intents|changelog|knowledge)/|\.claude/)")
CALLABLE = re.compile(r"([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\s*\(")
BACKTICKED = re.compile(r"`([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)")
DOTTED = re.compile(r"\b([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+)\b")


def load(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for block in re.findall(r"```json\s*\n(.*?)\n```", text, re.S):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and "tickets" in data:
            return data
    raise SystemExit(f"{path}: no JSON with \"tickets\" - the plan's ## Tickets keeps them in a ```json block")


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def changed_paths(base):
    tracked = git("diff", "--name-only", base).splitlines()
    untracked = git("ls-files", "--others", "--exclude-standard").splitlines()
    return sorted({p for p in tracked + untracked if p and not WORKFLOW_PATHS.match(p)})


def covers(entry, path):
    entry = entry[2:] if entry.startswith("./") else entry
    return path == entry or (entry.endswith("/") and path.startswith(entry))


def interface_name(entry):
    """The name to look for: the callable, else the first backticked or dotted name. None: unchecked."""
    for pattern in (CALLABLE, BACKTICKED, DOTTED):
        m = pattern.search(entry)
        if m:
            return m.group(1).split(".")[-1]
    return None


def ticket_text(files):
    chunks = []
    for entry in files:
        paths = [entry] if not entry.endswith("/") else [
            os.path.join(d, f) for d, _, fs in os.walk(entry) for f in fs]
        for p in paths:
            if os.path.isfile(p):
                with open(p, encoding="utf-8", errors="replace") as f:
                    chunks.append(f.read())
    return "\n".join(chunks)


def check(tickets, changed):
    problems, rows = [], []
    for path in changed:
        if not any(covers(e, path) for t in tickets for e in t.get("files") or []):
            problems.append(f"{path}: changed, but in no ticket's files")
    for t in tickets:
        tid = t.get("id", "?")
        files = t.get("files") or []
        untouched = [e for e in files if not any(covers(e, p) for p in changed)]
        for e in untouched:
            problems.append(f"{tid}: {e} is in its files but was not changed")
        text = ticket_text(files)
        found, missing, unchecked = [], [], []
        for entry in t.get("interface") or []:
            name = interface_name(entry)
            if name is None:
                unchecked.append(entry)
            elif re.search(rf"\b{re.escape(name)}\b", text):
                found.append(name)
            else:
                missing.append(name)
                problems.append(f"{tid}: interface `{name}` does not appear in its files")
        rows.append((tid, len(files) - len(untouched), len(files), found, missing, unchecked))
    return problems, rows


def main(argv):
    base = "HEAD"
    if argv[:1] == ["--base"] and len(argv) >= 2:
        base, argv = argv[1], argv[2:]
    if len(argv) != 1:
        print("usage: check_conformance.py [--base <commit>] <plan.md | tickets.json>", file=sys.stderr)
        return 2
    tickets = load(argv[0]).get("tickets") or []
    problems, rows = check(tickets, changed_paths(base))
    print("| Ticket | Files changed | Interface found | Interface missing |")
    print("|---|---|---|---|")
    for tid, done, total, found, missing, unchecked in rows:
        extra = f" (not checkable: {len(unchecked)})" if unchecked else ""
        print(f"| {tid} | {done}/{total} | {', '.join(found) or '-'}{extra} | {', '.join(missing) or '-'} |")
    for p in problems:
        print(f"problem: {p}")
    if problems:
        return 1
    print("OK: every change is inside a ticket, every ticket's files changed, every interface name present")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
