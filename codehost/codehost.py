#!/usr/bin/env python3
"""Code-host operations for CI, done through the vendor's MCP server.

The kit's pipelines never call a code host's API directly and never hand the
model a tool that writes to one. The model returns data (findings, a summary);
this script posts it, deterministically, by starting the provider's MCP server
(codehost/providers/<provider>.json) and calling its tools as an MCP client.
Supporting another provider is a new profile and a new class below - the
pipelines and skills stay as they are.

Subcommands:
  publish-review  inline comments for the findings + one summary comment,
                  edited in place on every run (found by its marker)
  upsert-comment  the same summary-comment logic for any marker and body
  ensure-change   find the open pull/merge request from --head into --base,
                  or open one

Environment:
  ADK_PROVIDER           github | gitlab
  ADK_PROJECT            owner/repo (GitHub), project ID or path (GitLab)
  ADK_CODEHOST_TOKEN     token the MCP server acts as
  ADK_CODEHOST_URL       GitHub Enterprise host, or GitLab API URL (.../api/v4)
  ADK_CODEHOST_BOT_LOGIN the login that token posts as, when known
                         (github-actions[bot] in GitHub Actions)
  ADK_CODEHOST_SERVER    optional JSON argv replacing the profile's server
                         command (a self-hosted build, or the tests' fake)

Standard library only: this runs on bare CI images.
"""

import argparse
import json
import os
import queue
import re
import subprocess
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
REVIEW_MARKER = "<!-- adk-independent-review -->"
SEVERITIES = ("blocking", "suggestion", "question")


class CodeHostError(Exception):
    pass


class ToolError(CodeHostError):
    def __init__(self, tool, text):
        super().__init__(f"{tool}: {text.strip()[:500]}")
        self.tool = tool


# ---------------------------------------------------------------- profile

def load_profile(provider):
    path = os.path.join(HERE, "providers", f"{provider}.json")
    if not os.path.isfile(path):
        known = sorted(f[:-5] for f in os.listdir(os.path.join(HERE, "providers"))
                       if f.endswith(".json") and not f.endswith(".tools.json"))
        raise CodeHostError(f"unknown provider {provider!r}; profiles exist for: {', '.join(known)}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


_VAR = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(:-([^}]*))?\}")


def expand(value, env, tools):
    """${VAR} and ${VAR:-default} from env; {tools} is the profile's tool list."""
    def sub(m):
        name, default = m.group(1), m.group(3)
        got = env.get(name, "")
        if got:
            return got
        if default is not None:
            return default
        raise CodeHostError(f"{name} is not set")
    return _VAR.sub(sub, value).replace("{tools}", ",".join(tools))


def server_launch(profile, env):
    tools = profile["tools"]
    override = env.get("ADK_CODEHOST_SERVER", "")
    if override:
        argv = json.loads(override)
    else:
        argv = [expand(a, env, tools) for a in profile["server"]["command"]]
    child_env = dict(env)
    for key, value in profile["server"].get("env", {}).items():
        child_env[key] = expand(value, env, tools)
    return argv, child_env


# ------------------------------------------------------------- MCP client

class McpClient:
    """A minimal MCP client over stdio: newline-delimited JSON-RPC."""

    def __init__(self, argv, env, timeout=180):
        self.timeout = timeout
        try:
            self.proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE, env=env, text=True, bufsize=1)
        except OSError as e:
            raise CodeHostError(f"cannot start the MCP server {argv[0]!r}: {e}")
        self.lines = queue.Queue()
        self.stderr_tail = []
        threading.Thread(target=self._pump_stdout, daemon=True).start()
        threading.Thread(target=self._pump_stderr, daemon=True).start()
        self.next_id = 0
        self._request("initialize", {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "adk-codehost", "version": "1"},
        })
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _pump_stdout(self):
        for line in self.proc.stdout:
            self.lines.put(line)
        self.lines.put(None)

    def _pump_stderr(self):
        for line in self.proc.stderr:
            self.stderr_tail = (self.stderr_tail + [line.rstrip()])[-20:]

    def _send(self, msg):
        try:
            self.proc.stdin.write(json.dumps(msg) + "\n")
            self.proc.stdin.flush()
        except (BrokenPipeError, OSError):
            raise CodeHostError("the MCP server exited: " + self._stderr())

    def _stderr(self):
        return " | ".join(self.stderr_tail[-5:]) or "(no output)"

    def _request(self, method, params):
        self.next_id += 1
        want = self.next_id
        self._send({"jsonrpc": "2.0", "id": want, "method": method, "params": params})
        while True:
            try:
                line = self.lines.get(timeout=self.timeout)
            except queue.Empty:
                raise CodeHostError(f"no answer to {method} within {self.timeout}s: " + self._stderr())
            if line is None:
                raise CodeHostError("the MCP server exited: " + self._stderr())
            try:
                msg = json.loads(line)
            except ValueError:
                continue  # a server logging to stdout; not protocol
            if "method" in msg and "id" in msg:  # a request from the server
                result = {"roots": []} if msg["method"] == "roots/list" else {}
                self._send({"jsonrpc": "2.0", "id": msg["id"], "result": result})
                continue
            if msg.get("id") != want:
                continue
            if "error" in msg:
                raise CodeHostError(f"{method}: {msg['error'].get('message', msg['error'])}")
            return msg.get("result", {})

    def call(self, tool, args):
        result = self._request("tools/call", {"name": tool, "arguments": args})
        text = "\n".join(c.get("text", "") for c in result.get("content", []) if c.get("type") == "text")
        if result.get("isError"):
            raise ToolError(tool, text)
        return text

    def call_json(self, tool, args):
        text = self.call(tool, args)
        try:
            return json.loads(text)
        except ValueError:
            raise CodeHostError(f"{tool} returned something other than JSON: {text[:200]!r}")

    def close(self):
        try:
            self.proc.stdin.close()
        except OSError:
            pass
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()


# ------------------------------------------------------------------- diff

def parse_diff(text):
    """Map each changed file's commentable lines, from a unified diff.

    Returns {new_path: {"old_path": str, "new": {line: old_line_or_None},
    "old": {deleted_old_line, ...}}}. A line the diff does not show cannot
    carry an inline comment on any code host.
    """
    files, cur = {}, None
    old_no = new_no = 0
    old_path = new_path = None
    for raw in text.splitlines():
        if raw.startswith("diff --git "):
            cur, old_path, new_path = None, None, None
            m = re.match(r"diff --git a/(.*) b/(.*)$", raw)
            if m:
                old_path, new_path = m.group(1), m.group(2)
        elif raw.startswith("--- "):
            p = raw[4:].split("\t")[0]
            old_path = None if p == "/dev/null" else re.sub(r"^a/", "", p)
        elif raw.startswith("+++ "):
            p = raw[4:].split("\t")[0]
            new_path = None if p == "/dev/null" else re.sub(r"^b/", "", p)
            key = new_path or old_path
            cur = files.setdefault(key, {"old_path": old_path or key, "new": {}, "old": set()})
        elif raw.startswith("@@") and cur is not None:
            m = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw)
            if m:
                old_no, new_no = int(m.group(1)), int(m.group(2))
        elif cur is not None and raw[:1] in ("+", "-", " ") and not raw.startswith(("+++", "---")):
            if raw[0] == "+":
                cur["new"][new_no] = None
                new_no += 1
            elif raw[0] == "-":
                cur["old"].add(old_no)
                old_no += 1
            else:
                cur["new"][new_no] = old_no
                old_no += 1
                new_no += 1
    return files


def locate(finding, diff_map):
    """(placement, reason). placement is None when the line is not in the diff."""
    path, line = finding["path"], int(finding["line"])
    side = finding.get("side", "new")
    if diff_map is None:
        return {"path": path, "old_path": path, "side": side, "line": line, "old_line": None}, None
    entry = diff_map.get(path)
    if entry is None:
        return None, "file not in the diff"
    if side == "old":
        if line in entry["old"]:
            return {"path": path, "old_path": entry["old_path"], "side": "old", "line": line,
                    "old_line": line}, None
        return None, "deleted line not in the diff"
    if line in entry["new"]:
        return {"path": path, "old_path": entry["old_path"], "side": "new", "line": line,
                "old_line": entry["new"][line]}, None
    return None, "line not in the diff"


def finding_body(f):
    return f"**{f['severity']}** - {f['body'].strip()}"


# -------------------------------------------------------------- providers

class GitHub:
    def __init__(self, mcp, project, bot_login):
        if "/" not in project:
            raise CodeHostError(f"ADK_PROJECT must be owner/repo for GitHub, got {project!r}")
        self.mcp = mcp
        self.owner, self.repo = project.split("/", 1)
        self.bot = bot_login

    def _repo(self, **kw):
        return dict(owner=self.owner, repo=self.repo, **kw)

    def _pages(self, method, change):
        out = []
        for page in range(1, 21):
            batch = self.mcp.call_json("pull_request_read", self._repo(
                method=method, pullNumber=int(change), page=page, perPage=100))
            out += batch
            if len(batch) < 100:
                break
        return out

    def upsert_comment(self, change, marker, body):
        mine = [c for c in self._pages("get_comments", change)
                if (c.get("body") or "").startswith(marker)
                and (not self.bot or (c.get("user") or {}).get("login") == self.bot)]
        if mine:
            self.mcp.call("update_issue_comment", self._repo(comment_id=int(mine[-1]["id"]), body=body))
            return "updated"
        self.mcp.call("add_issue_comment", self._repo(issue_number=int(change), body=body))
        return "created"

    def inline(self, change, placed, head_sha):
        """Returns (posted, failed) lists of (finding, placement[, reason])."""
        if not placed:
            return [], []
        # The server finds "the latest review" with reviews(first: 1, author: <viewer>),
        # which is the viewer's OLDEST review. Once the reviewer has submitted one review
        # on a pull request, it can no longer add comments to, submit, or delete a new
        # pending one. Check first instead of leaving a stranded pending review behind.
        if self.bot:
            reviews = [r for r in self._pages("get_reviews", change)
                       if (r.get("user") or {}).get("login") == self.bot]
            if any(r.get("state") != "PENDING" for r in reviews):
                why = (f"{self.bot} already reviewed this pull request, and GitHub's MCP server "
                       "can add inline comments only to a reviewer's first review")
                return [], [(f, p, why) for f, p in placed]
            if reviews:  # a pending review stranded by an earlier failed run
                self.mcp.call("pull_request_review_write", self._repo(
                    method="delete_pending", pullNumber=int(change)))
        args = self._repo(method="create", pullNumber=int(change))
        if head_sha:
            args["commitID"] = head_sha
        try:
            self.mcp.call("pull_request_review_write", args)
        except ToolError as e:
            return [], [(f, p, f"could not open a review: {e}") for f, p in placed]
        posted, failed = [], []
        for f, p in placed:
            args = self._repo(pullNumber=int(change), path=p["path"], body=finding_body(f),
                              subjectType="LINE", line=p["line"],
                              side="LEFT" if p["side"] == "old" else "RIGHT")
            try:
                self.mcp.call("add_comment_to_pending_review", args)
                posted.append((f, p))
            except ToolError as e:
                failed.append((f, p, str(e)))
        if posted:
            try:
                self.mcp.call("pull_request_review_write", self._repo(
                    method="submit_pending", pullNumber=int(change), event="COMMENT",
                    body="Inline findings from the independent review. The summary comment lists all of them."))
                return posted, failed
            except ToolError as e:
                failed += [(f, p, f"review not submitted: {e}") for f, p in posted]
                posted = []
        try:
            self.mcp.call("pull_request_review_write", self._repo(method="delete_pending", pullNumber=int(change)))
        except ToolError:
            pass
        return posted, failed

    def find_change(self, head, base):
        prs = self.mcp.call_json("list_pull_requests", self._repo(
            head=f"{self.owner}:{head}", base=base, state="open", perPage=10))
        return prs[0].get("html_url") if prs else None

    def open_change(self, head, base, title, body):
        pr = self.mcp.call_json("create_pull_request", self._repo(head=head, base=base, title=title, body=body))
        return pr.get("url") or pr.get("html_url")


class GitLab:
    def __init__(self, mcp, project, bot_login):
        self.mcp = mcp
        self.project = project
        self.bot = bot_login

    def _mr(self, change, **kw):
        return dict(project_id=self.project, merge_request_iid=str(change), **kw)

    def upsert_comment(self, change, marker, body):
        notes = []
        for page in range(1, 21):
            batch = self.mcp.call_json("get_merge_request_notes", self._mr(
                change, sort="asc", order_by="created_at", per_page=100, page=page))
            notes += batch
            if len(batch) < 100:
                break
        mine = [n for n in notes
                if not n.get("system") and (n.get("body") or "").startswith(marker)
                and (not self.bot or (n.get("author") or {}).get("username") == self.bot)]
        if mine:
            self.mcp.call("update_merge_request_note", self._mr(change, note_id=str(mine[-1]["id"]), body=body))
            return "updated"
        self.mcp.call("create_merge_request_note", self._mr(change, body=body))
        return "created"

    def inline(self, change, placed, head_sha):
        if not placed:
            return [], []
        try:
            refs = self.mcp.call_json("get_merge_request", self._mr(change)).get("diff_refs") or {}
        except CodeHostError as e:
            return [], [(f, p, f"could not read the merge request: {e}") for f, p in placed]
        if not all(refs.get(k) for k in ("base_sha", "start_sha", "head_sha")):
            return [], [(f, p, "the merge request has no diff_refs yet") for f, p in placed]
        posted, failed = [], []
        for f, p in placed:
            position = {"base_sha": refs["base_sha"], "start_sha": refs["start_sha"],
                        "head_sha": refs["head_sha"], "position_type": "text",
                        "new_path": p["path"], "old_path": p["old_path"]}
            if p["side"] == "old":
                position["old_line"] = p["line"]
            else:
                position["new_line"] = p["line"]
                if p["old_line"] is not None:  # an unchanged line needs both
                    position["old_line"] = p["old_line"]
            try:
                self.mcp.call("create_merge_request_thread", self._mr(
                    change, body=finding_body(f), position=position))
                posted.append((f, p))
            except ToolError as e:
                failed.append((f, p, str(e)))
        return posted, failed

    def find_change(self, head, base):
        mrs = self.mcp.call_json("list_merge_requests", dict(
            project_id=self.project, source_branch=head, target_branch=base, state="opened"))
        return mrs[0].get("web_url") if mrs else None

    def open_change(self, head, base, title, body):
        mr = self.mcp.call_json("create_merge_request", dict(
            project_id=self.project, source_branch=head, target_branch=base, title=title, description=body))
        return mr.get("web_url")


PROVIDERS = {"github": GitHub, "gitlab": GitLab}


def connect(env):
    provider = env.get("ADK_PROVIDER", "")
    if provider not in PROVIDERS:
        raise CodeHostError(f"ADK_PROVIDER must be one of {', '.join(PROVIDERS)}, got {provider!r}")
    project = env.get("ADK_PROJECT", "")
    if not project:
        raise CodeHostError("ADK_PROJECT is not set")
    argv, child_env = server_launch(load_profile(provider), env)
    mcp = McpClient(argv, child_env)
    return mcp, PROVIDERS[provider](mcp, project, env.get("ADK_CODEHOST_BOT_LOGIN", ""))


# --------------------------------------------------------------- commands

def validate_findings(findings):
    ok = []
    for f in findings:
        if not isinstance(f, dict) or f.get("severity") not in SEVERITIES:
            continue
        if not isinstance(f.get("path"), str) or not str(f.get("body", "")).strip():
            continue
        try:
            f["line"] = int(f["line"])
        except (KeyError, TypeError, ValueError):
            continue
        ok.append(f)
    return ok


def publish_review(host, args):
    with open(args.result, encoding="utf-8") as f:
        result = json.load(f)
    findings = validate_findings(result.get("findings") or [])
    diff_map = None
    if args.diff:
        with open(args.diff, encoding="utf-8", errors="replace") as f:
            diff_map = parse_diff(f.read())

    placed, unplaced = [], []
    for finding in findings:
        placement, reason = locate(finding, diff_map)
        if placement:
            placed.append((finding, placement))
        else:
            unplaced.append((finding, reason))
    posted, failed = host.inline(args.change, placed, args.head_sha)
    unplaced += [(f, reason) for f, _, reason in failed]

    lines = [REVIEW_MARKER, (result.get("summary_markdown") or "").rstrip(), ""]
    if unplaced:
        lines += [f"<sub>{len(unplaced)} finding(s) are listed above but not inline:</sub>", ""]
        lines += [f"- `{f['path']}:{f['line']}` - {reason}" for f, reason in unplaced]
        lines.append("")
    footer = "Reviewed"
    if args.head_sha:
        footer += f" commit {args.head_sha[:7]}"
    lines.append(f"<sub>{footer} by the kit's `independent-review` skill. Updated on every push.</sub>")
    body = "\n".join(lines)
    if args.summary_out:
        with open(args.summary_out, "w", encoding="utf-8") as f:
            f.write(body + "\n")
    action = host.upsert_comment(args.change, REVIEW_MARKER, body)
    report = {"findings": len(findings), "inline": len(posted), "not_inline": len(unplaced),
              "summary": action,
              "not_inline_reasons": sorted({reason for _, reason in unplaced})}
    print(json.dumps(report))


def upsert_comment(host, args):
    with open(args.body_file, encoding="utf-8") as f:
        body = f.read()
    if not body.startswith(args.marker):
        body = args.marker + "\n" + body
    print(host.upsert_comment(args.change, args.marker, body))


def ensure_change(host, args):
    url = host.find_change(args.head, args.base)
    if url:
        print(f"existing {url}")
        return
    with open(args.body_file, encoding="utf-8") as f:
        body = f.read()
    print(f"opened {host.open_change(args.head, args.base, args.title, body)}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("publish-review")
    p.add_argument("--change", required=True, help="pull/merge request number")
    p.add_argument("--result", required=True, help="the reviewer's structured output (JSON)")
    p.add_argument("--diff", help="the reviewed diff; findings outside it are not placed inline")
    p.add_argument("--head-sha", default="")
    p.add_argument("--summary-out", help="also write the posted summary here")
    p = sub.add_parser("upsert-comment")
    p.add_argument("--change", required=True)
    p.add_argument("--marker", required=True)
    p.add_argument("--body-file", required=True)
    p = sub.add_parser("ensure-change")
    p.add_argument("--head", required=True)
    p.add_argument("--base", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--body-file", required=True)
    args = ap.parse_args(argv)

    try:
        mcp, host = connect(os.environ)
    except CodeHostError as e:
        print(f"codehost: {e}", file=sys.stderr)
        return 2
    try:
        {"publish-review": publish_review, "upsert-comment": upsert_comment,
         "ensure-change": ensure_change}[args.cmd](host, args)
        return 0
    except CodeHostError as e:
        print(f"codehost: {e}", file=sys.stderr)
        return 1
    finally:
        mcp.close()


if __name__ == "__main__":
    sys.exit(main())
