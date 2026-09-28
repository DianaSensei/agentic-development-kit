#!/usr/bin/env python3
"""Replay the orchestration scenarios against this kit and check what the workflow did.

    python3 scenarios/run.py                       every scenario
    python3 scenarios/run.py waves-and-resume      one or more by name
    options: --model <id>  --keep  --timeout <seconds>

Each scenario directory holds fixture.sh (builds a small repository), prompt.md (what the user says)
and check.py (asserts on the transcript and the repository afterwards). A scenario is a real headless
Claude Code session with this plugin loaded - it costs money (about $1-2 each) and takes minutes, so it
runs before a release and by hand, not on every pull request. See scenarios/README.md.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from lib import Run  # noqa: E402
TOOLS = "Read,Write,Edit,Grep,Glob,Bash,Agent,Task,Skill,SendMessage,ToolSearch,ReadNotifications"


def scenarios():
    return sorted(d for d in os.listdir(HERE)
                  if os.path.isfile(os.path.join(HERE, d, "check.py")))


def run_one(name, model, timeout, keep):
    src = os.path.join(HERE, name)
    work = tempfile.mkdtemp(prefix=f"adk-scenario-{name}-")
    repo = os.path.join(work, "repo")
    transcript = os.path.join(work, "transcript.jsonl")
    subprocess.run(["bash", os.path.join(src, "fixture.sh"), repo], check=True)
    start = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True, text=True,
                           check=True).stdout.strip()
    with open(os.path.join(src, "prompt.md"), encoding="utf-8") as f:
        prompt = f.read().strip()

    cmd = ["claude", "-p", prompt, "--plugin-dir", KIT, "--add-dir", KIT, "--allowedTools", TOOLS,
           "--permission-mode", "acceptEdits", "--output-format", "stream-json", "--verbose"]
    if model:
        cmd += ["--model", model]
    began = time.time()
    with open(transcript, "w") as out, open(os.path.join(work, "stderr.txt"), "w") as err:
        try:
            subprocess.run(cmd, cwd=repo, stdin=subprocess.DEVNULL, stdout=out, stderr=err, timeout=timeout)
        except subprocess.TimeoutExpired:
            print(f"{name}: timed out after {timeout}s - checking what it left")
    minutes = (time.time() - began) / 60

    cost = Run(transcript).cost() if os.path.getsize(transcript) else 0
    print(f"\n=== {name} ({minutes:.1f} min, ${cost:.2f}) ===")
    rc = subprocess.run([sys.executable, os.path.join(src, "check.py"), transcript, repo, start],
                        env=dict(os.environ, PYTHONPATH=HERE)).returncode
    if keep or rc:
        print(f"kept: {work}")
    else:
        shutil.rmtree(work, ignore_errors=True)
    return rc


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("names", nargs="*", help="scenarios to run (default: all)")
    p.add_argument("--model", default=os.environ.get("MODEL", ""), help="model for the session under test")
    p.add_argument("--timeout", type=int, default=2400)
    p.add_argument("--keep", action="store_true", help="keep each run's repo and transcript")
    a = p.parse_args()
    names = a.names or scenarios()
    unknown = set(names) - set(scenarios())
    if unknown:
        raise SystemExit(f"unknown scenario(s): {', '.join(sorted(unknown))}; have: {', '.join(scenarios())}")
    failed = [n for n in names if run_one(n, a.model, a.timeout, a.keep)]
    print(f"\n{len(names) - len(failed)}/{len(names)} scenarios passed" + (f"; failed: {', '.join(failed)}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
