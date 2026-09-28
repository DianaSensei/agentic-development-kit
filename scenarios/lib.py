"""Shared helpers for the scenario checks: read a headless run's transcript, look at the repo it left.

A check script gets the run's stream-json transcript and the repository the run worked in, and asserts
what the workflow must have done - in the transcript (which agents were dispatched, with which model,
which scripts ran) and in the repo (tests pass, the user's branch never moved, nothing left behind).
"""

import json
import os
import re
import subprocess
import sys


class Run:
    """One headless run: its events, the lead agent's tool calls, and the results they got back."""

    def __init__(self, transcript):
        self.events = []
        with open(transcript, encoding="utf-8") as f:
            for line in f:
                try:
                    self.events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        self.calls = []      # lead agent's tool calls: {id, msg, name, input}
        self.results = {}    # tool_use_id -> (text, is_error)
        for e in self.events:
            if e.get("type") == "assistant" and not e.get("parent_tool_use_id"):
                for c in e["message"].get("content", []):
                    if c.get("type") == "tool_use":
                        self.calls.append({"id": c["id"], "msg": e["message"].get("id"),
                                           "name": c["name"], "input": c.get("input") or {}})
            if e.get("type") == "user" and isinstance(e.get("message", {}).get("content"), list):
                for c in e["message"]["content"]:
                    if isinstance(c, dict) and c.get("type") == "tool_result":
                        self.results[c.get("tool_use_id")] = (_text(c.get("content")), bool(c.get("is_error")))

    def calls_named(self, *names):
        return [c for c in self.calls if c["name"] in names]

    def dispatches(self, agent_suffix):
        """Agent/Task calls for an agent type ending in agent_suffix, each with `denied` set when a hook
        or the harness refused it."""
        out = []
        for c in self.calls_named("Agent", "Task"):
            if str(c["input"].get("subagent_type", "")).endswith(agent_suffix):
                text, err = self.results.get(c["id"], ("", False))
                out.append(dict(c, denied=err or "[dispatch-gate]" in text or "not found" in text))
        return out

    def bash(self, pattern):
        """The lead's Bash commands matching a regular expression."""
        return [c["input"].get("command", "") for c in self.calls_named("Bash")
                if re.search(pattern, c["input"].get("command", ""))]

    def read(self, suffix):
        return any(str(c["input"].get("file_path", "")).endswith(suffix) for c in self.calls_named("Read"))

    def lead_text(self):
        """Everything the lead said, in order - a report is often split across messages, and the
        last one may be only the question."""
        return "\n".join(c.get("text", "") for e in self.events
                         if e.get("type") == "assistant" and not e.get("parent_tool_use_id")
                         for c in e["message"].get("content", []) if c.get("type") == "text")

    def final_text(self):
        results = [e for e in self.events if e.get("type") == "result"]
        return results[-1].get("result", "") if results else ""

    def cost(self):
        results = [e for e in self.events if e.get("type") == "result"]
        return results[-1].get("total_cost_usd", 0) if results else 0

    def index(self, call):
        return self.calls.index(call)


def _text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
    return ""


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True).stdout.strip()


def tests_pass(repo, command=("python3", "-m", "unittest", "discover", "-s", "tests", "-t", ".")):
    r = subprocess.run(list(command), cwd=repo, capture_output=True, text=True, timeout=300)
    return r.returncode == 0, (r.stdout + r.stderr)[-600:]


def python(repo, code):
    """Run code with the repo's src/ importable; returns (ok, stdout)."""
    env = dict(os.environ, PYTHONPATH=os.path.join(repo, "src"))
    r = subprocess.run([sys.executable, "-c", code], cwd=repo, capture_output=True, text=True, env=env, timeout=60)
    return r.returncode == 0, (r.stdout.strip() or r.stderr.strip()[-300:])


class Checks:
    """Collects results. `must` fails the scenario; `expect` is behaviour the model usually shows but
    may not every run - reported, counted, not failing."""

    def __init__(self, name):
        self.name, self.rows = name, []

    def must(self, ok, what, detail=""):
        self.rows.append(("PASS" if ok else "FAIL", what, detail))

    def expect(self, ok, what, detail=""):
        self.rows.append(("PASS" if ok else "WARN", what, detail))

    def branch_untouched(self, repo, start_sha):
        head = git(repo, "rev-parse", "HEAD")
        self.must(head == start_sha, "the user's branch never moved", f"HEAD {head[:7]}, started {start_sha[:7]}")

    def nothing_left_behind(self, repo):
        worktrees = [l for l in git(repo, "worktree", "list").splitlines()[1:] if l.strip()]
        self.must(not worktrees, "no worktree left behind", "; ".join(worktrees)[:300])
        refs = git(repo, "for-each-ref", "refs/adk/")
        self.must(not refs, "snapshot refs dropped", refs[:200])

    def report(self):
        for status, what, detail in self.rows:
            print(f"{status}  {what}" + (f"  ({detail})" if detail and status != "PASS" else ""))
        failed = [r for r in self.rows if r[0] == "FAIL"]
        print(f"{self.name}: {'FAIL' if failed else 'PASS'} - {sum(r[0] == 'PASS' for r in self.rows)}/{len(self.rows)}"
              f" checks passed, {sum(r[0] == 'WARN' for r in self.rows)} expected behaviour(s) missing")
        return 1 if failed else 0


def args():
    """check.py <transcript.jsonl> <repo> <start-sha>"""
    if len(sys.argv) != 4:
        raise SystemExit("usage: check.py <transcript.jsonl> <repo> <start-sha>")
    return Run(sys.argv[1]), sys.argv[2], sys.argv[3]
