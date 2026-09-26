#!/usr/bin/env python3
"""Turn a recorded Claude Code session into a case's history_file.

A multi-turn case replays an earlier conversation (`context.history_file` in
case.yaml) and makes its prompt the next user turn - the way to test the second
half of a workflow, after its Checkpoint. Record that conversation by running
the case's fixture in an empty directory and `claude -p` there with this plugin;
the session lands in ~/.claude/projects/<escaped-dir>/<session-id>.jsonl.

That file carries far more than the conversation: the machine's environment,
the account's session context (an email address among it), prompt snapshots,
absolute paths. This keeps only the user and assistant messages, relinks them,
makes the recording directory's paths relative - a replay otherwise reaches back
into a directory that no longer exists - and refuses to write anything that
still looks personal.

Usage: clean-history.py <session.jsonl> <out.jsonl> --workspace <recorded dir>
                        [--plugin-root <path the plugin was loaded from>]
"""

import argparse
import json
import re
import sys

LOOKS_PERSONAL = [
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "an email address"),
    (re.compile(r'/(?:home|Users)/[^/"\s]+'), "a home directory"),
    (re.compile(r"sk-ant-[A-Za-z0-9_-]+"), "an API key"),
]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("session")
    ap.add_argument("out")
    ap.add_argument("--workspace", required=True, help="the directory the session was recorded in")
    ap.add_argument("--plugin-root", default="", help="replaced with /opt/agentic-development-kit")
    args = ap.parse_args(argv)
    workspace = args.workspace.rstrip("/")

    kept, prev = [], None
    with open(args.session, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            if d.get("type") not in ("user", "assistant"):
                continue  # environment, session context, snapshots, titles, cost
            d["parentUuid"] = prev
            prev = d.get("uuid")
            if "sessionId" in d:
                d["sessionId"] = "00000000-0000-0000-0000-000000000000"
            text = json.dumps(d, ensure_ascii=False)
            text = text.replace(workspace + "/", "").replace(workspace, ".")
            if args.plugin_root:
                text = text.replace(args.plugin_root.rstrip("/"), "/opt/agentic-development-kit")
            kept.append(text)

    body = "\n".join(kept) + "\n"
    found = [(label, m.group(0)) for pattern, label in LOOKS_PERSONAL for m in [pattern.search(body)] if m]
    if found:
        for label, sample in found:
            print(f"refusing to write: the history still contains {label} ({sample[:40]!r})", file=sys.stderr)
        return 1
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(body)
    print(f"{len(kept)} messages written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
