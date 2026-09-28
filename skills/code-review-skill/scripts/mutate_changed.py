#!/usr/bin/env python3
"""mutate_changed.py - do the tests catch a broken version of the code this change wrote?

    mutate_changed.py --test "<the project's test command>" [--base <commit>] [--max 20] [--timeout 300]

Run from the project root. A test that ran and passed is no proof it tests anything: a test that
asserts whatever the code happens to do, or only that it does not crash, passes against wrong code too.
This takes the lines the change added or edited in non-test source files (the working tree against
<commit>, default HEAD, untracked files included), makes one small change at a time - a comparison
flipped, `and`/`or` swapped, a boolean or a number changed, a returned value dropped - and runs the
test command on each. A mutant the tests fail on is killed. One they pass is a survivor: a way this
code can be wrong that no test notices.

It never touches the working tree: everything runs in a temporary copy (without .git). At most --max
mutants, spread over the changed lines; the unchanged suite must pass first.

Exit: 0 every mutant killed; 1 a survivor; 2 nothing could be run (usage, or the suite fails as is).
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

SOURCE = re.compile(r"\.(py|js|jsx|ts|tsx|mjs|cjs|java|kt|kts|go|rs|rb|php|cs|swift|scala|c|cc|cpp|h|hpp)$")
TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec|specs)/|(^|/)test_[^/]*$|_test\.\w+$|\.(test|spec)\.\w+$|Tests?\.(java|kt|cs)$")
COMMENT = re.compile(r"^\s*(#|//|/\*|\*|--)")
IMPORT = re.compile(r"^\s*(import |from \S+ import |#include|using |package |require\(|use )")

# (label, pattern, replacement) - one occurrence at a time, never inside a string literal.
OPERATORS = [
    ("== to !=", r"==", "!="),
    ("!= to ==", r"!=", "=="),
    ("<= to <", r"<=", "<"),
    (">= to >", r">=", ">"),
    ("and to or", r"\band\b", "or"),
    ("or to and", r"\bor\b", "and"),
    ("&& to ||", r"&&", "||"),
    ("|| to &&", r"\|\|", "&&"),
    ("True to False", r"\bTrue\b", "False"),
    ("False to True", r"\bFalse\b", "True"),
    ("true to false", r"\btrue\b", "false"),
    ("false to true", r"\bfalse\b", "true"),
    ("+ to -", r"(?<=\s)\+(?=\s)", "-"),
    ("- to +", r"(?<=\s)-(?=\s)", "+"),
    ("number + 1", r"(?<![\w.])\d+(?![\w.])", None),
]
RETURN = {"py": ("return None", re.compile(r"^(\s*)return\s+(?!None\b)\S.*$")),
          "js": ("return null", re.compile(r"^(\s*)return\s+(?!null\b|undefined\b)\S.*$"))}


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def changed_lines(base):
    """{path: [1-based line numbers]} added or changed in non-test source files."""
    out = {}
    for path in git("ls-files", "--others", "--exclude-standard").splitlines():
        if SOURCE.search(path) and not TEST_PATH.search(path) and os.path.isfile(path):
            with open(path, encoding="utf-8", errors="replace") as f:
                out[path] = list(range(1, sum(1 for _ in f) + 1))
    path = None
    for line in git("diff", "-U0", "--no-color", base, "--").splitlines():
        if line.startswith("+++ "):
            p = line[4:]
            path = p[2:] if p.startswith("b/") else None
            if path and (not SOURCE.search(path) or TEST_PATH.search(path)):
                path = None
        elif line.startswith("@@") and path:
            m = re.search(r"\+(\d+)(?:,(\d+))?", line)
            start, count = int(m.group(1)), int(m.group(2) or 1)
            out.setdefault(path, []).extend(range(start, start + count))
    return {p: sorted(set(ls)) for p, ls in out.items() if ls}


def string_spans(line):
    spans, quote, start, i = [], None, 0, 0
    while i < len(line):
        ch = line[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                spans.append((start, i + 1))
                quote = None
        elif ch in "\"'`":
            quote, start = ch, i
        i += 1
    if quote:
        spans.append((start, len(line)))
    return spans


def mutants_for(path, number, text):
    """Every single-edit mutant of one line: (label, mutated line)."""
    body = text.rstrip("\n")
    if not body.strip() or COMMENT.match(body) or IMPORT.match(body):
        return []
    strings = string_spans(body)
    inside = lambda a, b: any(s <= a and b <= e for s, e in strings)  # noqa: E731
    out = []
    for label, pattern, repl in OPERATORS:
        for m in re.finditer(pattern, body):
            if inside(m.start(), m.end()):
                continue
            new = str(int(m.group(0)) + 1) if repl is None else repl
            out.append((label, body[:m.start()] + new + body[m.end():]))
    lang = "py" if path.endswith(".py") else "js" if re.search(r"\.(m|c)?[jt]sx?$", path) else None
    if lang:
        replacement, pattern = RETURN[lang]
        m = pattern.match(body)
        if m:
            out.append(("drop the returned value", m.group(1) + replacement))
    return [(label, line + "\n") for label, line in out]


def spread(per_line, limit):
    """Round-robin over lines, so --max covers as many changed lines as it can."""
    chosen, queues = [], [list(ms) for ms in per_line if ms]
    while queues and len(chosen) < limit:
        for q in list(queues):
            if len(chosen) >= limit:
                break
            chosen.append(q.pop(0))
            if not q:
                queues.remove(q)
    return chosen


def run(cmd, cwd, timeout):
    try:
        r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return "pass" if r.returncode == 0 else "fail"
    except subprocess.TimeoutExpired:
        return "timeout"


def main(argv):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--test", required=True, help="the project's test command, as CLAUDE.md gives it")
    p.add_argument("--base", default="HEAD")
    p.add_argument("--max", type=int, default=20)
    p.add_argument("--timeout", type=int, default=300, help="seconds per test run")
    a = p.parse_args(argv)

    lines = changed_lines(a.base)
    if not lines:
        print("No changed lines in non-test source files: nothing to mutate.")
        return 0
    per_line = []
    for path, numbers in sorted(lines.items()):
        with open(path, encoding="utf-8", errors="replace") as f:
            content = f.readlines()
        for n in numbers:
            if n <= len(content):
                per_line.append([(path, n, label, content[n - 1], new)
                                 for label, new in mutants_for(path, n, content[n - 1])])
    chosen = spread(per_line, a.max)
    if not chosen:
        print(f"{sum(map(len, lines.values()))} changed line(s), none with a mutable operator, literal or return.")
        return 0

    tmp = tempfile.mkdtemp(prefix="adk-mutants-")
    try:
        copy = os.path.join(tmp, "tree")
        shutil.copytree(".", copy, symlinks=True,
                        ignore=shutil.ignore_patterns(".git", "worktrees") if os.path.isdir(".git") else None)
        if run(a.test, copy, a.timeout) != "pass":
            print("The test command fails on the unchanged code: fix the suite before measuring it.")
            return 2
        killed, survivors = 0, []
        for path, n, label, original, new in chosen:
            target = os.path.join(copy, path)
            with open(target, encoding="utf-8", errors="replace") as f:
                content = f.readlines()
            mutated = content[:n - 1] + [new] + content[n:]
            with open(target, "w", encoding="utf-8") as f:
                f.writelines(mutated)
            outcome = run(a.test, copy, a.timeout)
            with open(target, "w", encoding="utf-8") as f:
                f.writelines(content)
            if outcome == "pass":
                survivors.append((path, n, label, original.strip(), new.strip()))
            else:
                killed += 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    total = len(chosen)
    print(f"Mutants: {total} over {len({(c[0], c[1]) for c in chosen})} changed line(s) - {killed} killed, "
          f"{len(survivors)} survived.")
    for path, n, label, before, after in survivors:
        print(f"survived: {path}:{n}  {label}:  {before}  ->  {after}")
    if survivors:
        print("Each survivor is a way this code can be wrong that no test notices: add the test that "
              "catches it, or say why the mutant behaves the same (an equivalent mutant).")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
