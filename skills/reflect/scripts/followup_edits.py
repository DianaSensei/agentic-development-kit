#!/usr/bin/env python3
"""Lines you rewrote that the agent wrote: the strongest signal of your code style.

For every commit of yours (by --author, not carrying the agent's trailer), each
hunk that removes or replaces lines is blamed against the commit before it. A
hunk whose removed lines came from an agent commit is a pair - what the agent
wrote, what you made of it - and that is what `reflect` reads.

  followup_edits.py [--repo .] [--since "90 days ago"] [--author EMAIL]
                    [--agent-pattern REGEX] [--max-pairs 40] [--format json|md]

Agent commits are the ones whose message matches --agent-pattern (by default
Claude Code's trailers). Output stays on this machine: it is printed, never
sent anywhere. Standard library only.
"""

import argparse
import json
import re
import subprocess
import sys

AGENT_PATTERN = r"(?im)^(co-authored-by: claude\b|claude-session:)|generated with \[claude code\]"
MAX_HUNK_LINES = 40
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def git(repo, *args, check=True):
    out = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, errors="replace")
    if check and out.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {out.stderr.strip()}")
    return out.stdout


def commits(repo, since, author=None):
    """[(sha, parents, date, subject, body)] newest first."""
    args = ["log", "--no-color", f"--since={since}", "--format=%H%x1f%P%x1f%as%x1f%s%x1f%B%x1e"]
    if author:
        args.append(f"--author={author}")
    out = []
    for rec in git(repo, *args).split("\x1e"):
        rec = rec.strip("\n")
        if not rec:
            continue
        sha, parents, date, subject, body = rec.split("\x1f", 4)
        out.append((sha, parents.split(), date, subject, body))
    return out


def hunks(repo, sha):
    """Yield (old_path, old_start, old_lines, new_lines) for each hunk that removes lines."""
    diff = git(repo, "diff", "--no-color", "--no-ext-diff", "-U0", "-M", f"{sha}^", sha)
    old_path, cur = None, None
    for line in diff.splitlines():
        if line.startswith("diff --git "):
            if cur:
                yield cur
            old_path, cur = None, None
        elif line.startswith("--- "):
            old_path = None if line == "--- /dev/null" else line[6:] if line.startswith("--- a/") else line[4:]
        elif line.startswith("@@ "):
            if cur:
                yield cur
            m = HUNK.match(line)
            start, count = int(m.group(1)), int(m.group(2) if m.group(2) is not None else 1)
            cur = (old_path, start, [], []) if (old_path and count > 0) else None
        elif cur is not None:
            if line.startswith("-"):
                cur[2].append(line[1:])
            elif line.startswith("+"):
                cur[3].append(line[1:])
    if cur:
        yield cur


def blame_commits(repo, sha, path, start, count):
    out = git(repo, "blame", "--porcelain", "-L", f"{start},+{count}", f"{sha}^", "--", path, check=False)
    return {line.split()[0] for line in out.splitlines() if re.match(r"^[0-9a-f]{40} \d+ \d+", line)}


def pairs(repo, since, author, agent_pattern, max_pairs):
    agent_re = re.compile(agent_pattern)
    agent = {sha: (date, subj) for sha, _, date, subj, body in commits(repo, since) if agent_re.search(body)}
    found = []
    for sha, parents, date, subject, body in commits(repo, since, author):
        if sha in agent or len(parents) != 1:
            continue
        for path, start, old, new in hunks(repo, sha):
            from_agent = blame_commits(repo, sha, path, start, len(old)) & agent.keys()
            if not from_agent:
                continue
            a = sorted(from_agent, key=lambda s: agent[s][0])[-1]
            found.append({
                "file": path,
                "agent_commit": a[:10], "agent_subject": agent[a][1], "agent_date": agent[a][0],
                "your_commit": sha[:10], "your_subject": subject, "your_date": date,
                "agent_wrote": old[:MAX_HUNK_LINES], "you_made_it": new[:MAX_HUNK_LINES],
                "truncated": len(old) > MAX_HUNK_LINES or len(new) > MAX_HUNK_LINES,
            })
            if len(found) >= max_pairs:
                return found
    return found


def markdown(found):
    if not found:
        return "No lines of an agent commit were rewritten by you in this range.\n"
    out = []
    for p in found:
        out.append(f"### {p['file']} - {p['your_date']} {p['your_commit']} \"{p['your_subject']}\"")
        out.append(f"Rewrites lines from {p['agent_commit']} \"{p['agent_subject']}\" ({p['agent_date']})\n")
        out.append("```diff")
        out += [f"-{l}" for l in p["agent_wrote"]] + [f"+{l}" for l in p["you_made_it"]]
        out.append("```\n")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", default=".")
    ap.add_argument("--since", default="90 days ago")
    ap.add_argument("--author", help="your git author email or name (default: git config user.email)")
    ap.add_argument("--agent-pattern", default=AGENT_PATTERN)
    ap.add_argument("--max-pairs", type=int, default=40)
    ap.add_argument("--format", choices=["json", "md"], default="md")
    args = ap.parse_args(argv)
    author = args.author or git(args.repo, "config", "user.email", check=False).strip()
    if not author:
        print("followup_edits: no --author and no git user.email here", file=sys.stderr)
        return 2
    found = pairs(args.repo, args.since, author, args.agent_pattern, args.max_pairs)
    sys.stdout.write(json.dumps(found, indent=2) + "\n" if args.format == "json" else markdown(found))
    return 0


if __name__ == "__main__":
    sys.exit(main())
