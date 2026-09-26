#!/usr/bin/env python3
"""Turn a real independent-review failure into an eval case.

When the reviewer misses a defect on a real pull request, or reports one that is
not there, that change is the best test the kit can have: it is the kind of
diff that actually fooled it. This copies the change into a self-contained case
under evals/independent-review/<name>/:

  seed/base/...       the files the change touches and the other files in
                      their directories, as they were at --base, plus the
                      context a reviewer reads (CLAUDE.md, REVIEW.md,
                      docs/intents/, docs/plans/ - whatever of those exists;
                      --context adds more)
  seed/change.patch   the change itself, --base to --head
  fixture.sh          rebuilds the repository and review.diff from those
  prompt.md, case.yaml
  graders/            the usual reviewer checks, plus an llm grader for this
                      failure: the defect it must now report (--missed), or the
                      claim it must no longer make (--false)

The case must FAIL on the kit as it is - that is what proves it captures the
failure. Run it, see it fail, then fix the skill and see it pass.

The seed copies code from the repository you point at: strip anything you
would not commit to the kit's repository before you do.

Usage:
  new-review-case.py --repo PATH --base REV --head REV --name NAME
                     (--missed | --false) --path FILE --line N --what TEXT
                     [--context PATH ...] [--out DIR]
"""

import argparse
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONTEXT = ["CLAUDE.md", "REVIEW.md", "docs/intents", "docs/plans"]


def git(repo, *args, binary=False):
    return subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True,
                          text=not binary).stdout


def exists_at(repo, rev, path):
    return subprocess.run(["git", "-C", repo, "cat-file", "-e", f"{rev}:{path}"],
                          capture_output=True).returncode == 0


def siblings(repo, rev, directory):
    out = git(repo, "ls-tree", rev, "--", directory + "/")
    return [line.split("\t", 1)[1] for line in out.splitlines() if line.split()[1] == "blob"]


def files_under(repo, rev, path):
    out = git(repo, "ls-tree", "-r", "--name-only", rev, "--", path)
    return [p for p in out.splitlines() if p]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", required=True)
    ap.add_argument("--name", required=True, help="case directory name, e.g. missed-null-check-in-refund")
    kind = ap.add_mutually_exclusive_group(required=True)
    kind.add_argument("--missed", action="store_true", help="the reviewer did not report a real defect")
    kind.add_argument("--false", dest="false_finding", action="store_true",
                      help="the reviewer reported a defect that is not there")
    ap.add_argument("--path", required=True, help="file the finding is about")
    ap.add_argument("--line", required=True, type=int)
    ap.add_argument("--what", required=True, help="one sentence: the defect, or the wrong claim")
    ap.add_argument("--context", nargs="*", default=None, help="repo paths to include at --base")
    ap.add_argument("--out", default=os.path.join(HERE, "independent-review"))
    args = ap.parse_args(argv)

    repo = os.path.abspath(args.repo)
    base = git(repo, "rev-parse", args.base).strip()
    head = git(repo, "rev-parse", args.head).strip()
    case = os.path.join(args.out, args.name)
    if os.path.exists(case):
        sys.exit(f"{case} already exists")

    touched = [p for p in git(repo, "diff", "--name-only", base, head).splitlines() if p]
    wanted = set(p for p in touched if exists_at(repo, base, p))
    # The code around the change - the other files in each touched file's
    # directory, not deeper: a diff alone hides the caller that breaks.
    for d in sorted({os.path.dirname(p) for p in touched if os.path.dirname(p)}):
        wanted.update(siblings(repo, base, d))
    for c in (args.context if args.context is not None else DEFAULT_CONTEXT):
        if exists_at(repo, base, c):
            wanted.update(files_under(repo, base, c))

    seed = os.path.join(case, "seed", "base")
    for path in sorted(wanted):
        dest = os.path.join(seed, path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(git(repo, "show", f"{base}:{path}", binary=True))
    with open(os.path.join(case, "seed", "change.patch"), "wb") as f:
        f.write(git(repo, "diff", "--binary", base, head, binary=True))

    origin = f"{os.path.basename(repo)} {base[:7]}..{head[:7]}"
    with open(os.path.join(case, "fixture.sh"), "w") as f:
        f.write(f"""#!/usr/bin/env bash
# Generated by evals/new-review-case.py from {origin}.
# The repository at the base of the change, then the change on a branch, the
# way the reviewer met it - and review.diff, as CI hands it over.
set -euo pipefail
here="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
export GIT_AUTHOR_NAME=eval GIT_AUTHOR_EMAIL=eval@example.com GIT_COMMITTER_NAME=eval GIT_COMMITTER_EMAIL=eval@example.com
# The project opted into the kit, as project-setup leaves it.
mkdir -p .claude && printf '{{"enabledPlugins":{{"adk-sdlc@agentic-development-kit":true}}}}\\n' > .claude/settings.json
git init -q -b main
cp -a "$here/seed/base/." .
git add -A && git commit -qm "Base" --allow-empty
git checkout -qb change
git apply --index "$here/seed/change.patch"
git commit -qm "The change under review"
git diff --no-color main HEAD > review.diff
""")
    os.chmod(os.path.join(case, "fixture.sh"), 0o755)

    with open(os.path.join(case, "case.yaml"), "w") as f:
        f.write(f'schema_version: "1.1"\nname: {args.name}\ncontext:\n  scaffold_script: fixture.sh\n')
    kind_text = "missed" if args.missed else "wrongly reported"
    with open(os.path.join(case, "prompt.md"), "w") as f:
        f.write(f"""---
description: "From a real review ({origin}) that {kind_text} a finding at {args.path}:{args.line} - {args.what.replace('"', "'")}"
tags: [independent-review, from-failure]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill]
---

Do an independent review of this branch against main. There is no shell in this session, so the diff is in review.diff.
""")

    graders = os.path.join(case, "graders")
    os.makedirs(graders)
    common = os.path.join(HERE, "independent-review", "planted-defects", "graders")
    for g in ("read-the-checklist.md", "no-edits.md", "not-an-approval.md"):
        if os.path.exists(os.path.join(common, g)):
            shutil.copy(os.path.join(common, g), graders)
    if args.missed:
        name, body = "reports-the-defect.md", (
            f"PASS if the review reports, at or near `{args.path}:{args.line}`, this problem: {args.what}\n"
            "FAIL if the review does not point it out, or mentions it without saying what goes wrong.\n")
    else:
        name, body = "no-false-finding.md", (
            f"PASS if the review does NOT report, as blocking, this claim about `{args.path}:{args.line}`: "
            f"{args.what} - it is not a real defect.\n"
            "FAIL if the review reports it as blocking.\n")
    with open(os.path.join(graders, name), "w") as f:
        f.write("---\ntype: llm\n---\n\n" + body)

    print(f"Wrote {case}: {len(wanted)} seed file(s), a {len(touched)}-file change.")
    print("Next: confirm it fails today, fix the skill, confirm it passes:")
    print(f"  claude plugin eval . --trust-plugin --scaffold --allow-tools Write Edit --case {args.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
