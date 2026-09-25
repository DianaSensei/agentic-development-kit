#!/usr/bin/env python3
"""A fake code-host MCP server for tests: no network, no account.

It serves the real tools/list captured from each vendor's server
(providers/<provider>.tools.json), so a client sees the real names and input
schemas, and answers calls from a JSON state file that persists between runs -
enough to test re-reviews and "find the open request". Every call is appended
to FAKE_LOG as one JSON line.

Behaviour that matters is copied from the real servers, including GitHub's
pending-review lookup (reviews(first: 1, author: viewer) - the viewer's oldest
review).

Environment: FAKE_PROVIDER (github | gitlab), FAKE_STATE, FAKE_LOG,
FAKE_VIEWER (the login the token belongs to), FAKE_REJECT_PATHS (comma list:
inline comments on these paths fail, as a line outside the diff would).
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROVIDER = os.environ.get("FAKE_PROVIDER", "github")
STATE_FILE = os.environ["FAKE_STATE"]
LOG_FILE = os.environ.get("FAKE_LOG", os.devnull)
VIEWER = os.environ.get("FAKE_VIEWER", "github-actions[bot]")
REJECT = {p for p in os.environ.get("FAKE_REJECT_PATHS", "").split(",") if p}

with open(os.path.join(HERE, "..", "providers", f"{PROVIDER}.tools.json"), encoding="utf-8") as f:
    TOOLS = {t["name"]: t for t in json.load(f)}


class Fail(Exception):
    pass


def load():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1)


def next_id(state):
    state["seq"] = state.get("seq", 1000) + 1
    return state["seq"]


def page(items, args, size_key, page_key="page"):
    size = int(args.get(size_key) or 30)
    n = int(args.get(page_key) or 1)
    return items[(n - 1) * size:n * size]


# ------------------------------------------------------------------ GitHub

def github(tool, a, s):
    s.setdefault("comments", [])
    s.setdefault("reviews", [])
    s.setdefault("prs", [])
    pr = int(a.get("pullNumber") or a.get("issue_number") or 0)

    def viewer_first():
        mine = [r for r in s["reviews"] if r["pr"] == pr and r["user"]["login"] == VIEWER]
        if not mine:
            raise Fail("No pending review found for the viewer")
        return mine[0]  # first: 1 - the oldest

    if tool == "pull_request_read":
        if a["method"] == "get_comments":
            items = [{k: c[k] for k in ("id", "body", "user", "html_url")} for c in s["comments"] if c["pr"] == pr]
            return page(items, a, "perPage")
        if a["method"] == "get_reviews":
            items = [{"id": r["id"], "state": r["state"], "user": r["user"],
                      "html_url": f"https://github.test/r/{r['id']}"} for r in s["reviews"] if r["pr"] == pr]
            return page(items, a, "perPage")
        raise Fail(f"fake: method {a['method']} not modelled")
    if tool == "add_issue_comment":
        c = {"id": next_id(s), "pr": pr, "body": a["body"], "user": {"login": VIEWER},
             "html_url": f"https://github.test/c/{s['seq']}"}
        s["comments"].append(c)
        return {"id": str(c["id"]), "url": c["html_url"]}
    if tool == "update_issue_comment":
        for c in s["comments"]:
            if c["id"] == int(a["comment_id"]):
                c["body"] = a["body"]
                return {"id": str(c["id"]), "url": c["html_url"]}
        raise Fail("failed to update comment: 404 Not Found")
    if tool == "pull_request_review_write":
        m = a["method"]
        if m == "create":
            if any(r["pr"] == pr and r["user"]["login"] == VIEWER and r["state"] == "PENDING" for r in s["reviews"]):
                raise Fail("User can only have one pending review per pull request")
            state = "COMMENTED" if a.get("event") else "PENDING"
            s["reviews"].append({"id": next_id(s), "pr": pr, "state": state, "user": {"login": VIEWER},
                                 "body": a.get("body", ""), "comments": []})
            return "pending pull request created" if state == "PENDING" else "pull request review submitted successfully"
        review = viewer_first()
        if review["state"] != "PENDING":
            raise Fail(f"The latest review, found at https://github.test/r/{review['id']} is not pending")
        if m == "submit_pending":
            review["state"] = "COMMENTED"
            review["body"] = a.get("body", "")
            return "pending pull request review successfully submitted"
        if m == "delete_pending":
            s["reviews"].remove(review)
            return "pending pull request review successfully deleted"
        raise Fail(f"fake: method {m} not modelled")
    if tool == "add_comment_to_pending_review":
        review = viewer_first()
        if review["state"] != "PENDING":
            raise Fail(f"The latest review, found at https://github.test/r/{review['id']} is not pending")
        if a["path"] in REJECT:
            raise Fail("Line could not be resolved")
        review["comments"].append({k: a.get(k) for k in ("path", "line", "side", "body")})
        return "pull request review comment successfully added to pending review"
    if tool == "list_pull_requests":
        head = a.get("head", "")
        items = [p for p in s["prs"] if p["state"] == a.get("state", "open")
                 and (not head or f"{a['owner']}:{p['head']}" == head)
                 and (not a.get("base") or p["base"] == a["base"])]
        return [{"number": p["number"], "title": p["title"], "state": p["state"], "html_url": p["html_url"],
                 "head": {"ref": p["head"]}, "base": {"ref": p["base"]}} for p in items]
    if tool == "create_pull_request":
        if any(p["head"] == a["head"] and p["state"] == "open" for p in s["prs"]):
            raise Fail("A pull request already exists")
        n = len(s["prs"]) + 1
        s["prs"].append({"number": n, "head": a["head"], "base": a["base"], "title": a["title"],
                         "body": a.get("body", ""), "state": "open",
                         "html_url": f"https://github.test/pull/{n}"})
        return {"id": str(next_id(s)), "url": f"https://github.test/pull/{n}"}
    raise Fail(f"fake: tool {tool} not modelled")


# ------------------------------------------------------------------ GitLab

def gitlab(tool, a, s):
    s.setdefault("notes", [])
    s.setdefault("threads", [])
    s.setdefault("mrs", [])
    refs = s.setdefault("diff_refs", {"base_sha": "b" * 40, "start_sha": "s" * 40, "head_sha": "h" * 40})
    iid = str(a.get("merge_request_iid", ""))

    if tool == "get_merge_request":
        return {"iid": int(iid), "title": "fake", "diff_refs": refs, "web_url": f"https://gitlab.test/mr/{iid}"}
    if tool == "get_merge_request_notes":
        items = [{k: n[k] for k in ("id", "body", "system", "author")} for n in s["notes"] if n["iid"] == iid]
        return page(items, a, "per_page")
    if tool == "create_merge_request_note":
        n = {"id": next_id(s), "iid": iid, "body": a["body"], "system": False, "author": {"username": VIEWER}}
        s["notes"].append(n)
        return {k: n[k] for k in ("id", "body", "author")}
    if tool == "update_merge_request_note":
        for n in s["notes"]:
            if str(n["id"]) == str(a["note_id"]):
                n["body"] = a["body"]
                return {k: n[k] for k in ("id", "body", "author")}
        raise Fail("GitLab API error: 404 Not Found")
    if tool == "create_merge_request_thread":
        pos = a.get("position") or {}
        for k in ("base_sha", "start_sha", "head_sha"):
            if pos.get(k) != refs[k]:
                raise Fail(f"GitLab API error: 400 position {k} does not match the merge request")
        if pos.get("position_type") != "text" or not pos.get("new_path"):
            raise Fail("GitLab API error: 400 position is invalid")
        if pos.get("new_path") in REJECT:
            raise Fail("GitLab API error: 400 line_code can't be blank")
        if pos.get("new_line") is None and pos.get("old_line") is None:
            raise Fail("GitLab API error: 400 position needs a line")
        t = {"id": f"d{next_id(s)}", "iid": iid, "body": a["body"], "position": pos}
        s["threads"].append(t)
        return {"id": t["id"], "notes": [{"body": a["body"], "position": pos}]}
    if tool == "list_merge_requests":
        items = [m for m in s["mrs"] if m["state"] == a.get("state", "opened")
                 and (not a.get("source_branch") or m["source_branch"] == a["source_branch"])
                 and (not a.get("target_branch") or m["target_branch"] == a["target_branch"])]
        return items
    if tool == "create_merge_request":
        n = len(s["mrs"]) + 1
        m = {"iid": n, "source_branch": a["source_branch"], "target_branch": a["target_branch"],
             "title": a["title"], "description": a.get("description", ""), "state": "opened",
             "web_url": f"https://gitlab.test/mr/{n}"}
        s["mrs"].append(m)
        return m
    raise Fail(f"fake: tool {tool} not modelled")


def check_args(tool, args):
    schema = TOOLS[tool]["inputSchema"]
    for key in schema.get("required", []):
        if key not in args:
            raise Fail(f"missing required parameter: {key}")
    for key, value in args.items():
        spec = schema.get("properties", {}).get(key)
        if spec is None:
            raise Fail(f"unknown parameter: {key}")
        if "enum" in spec and value not in spec["enum"]:
            raise Fail(f"{key} must be one of {spec['enum']}")


def handle_call(name, args):
    if name not in TOOLS:
        return {"isError": True, "content": [{"type": "text", "text": f"unknown tool {name}"}]}
    state = load()
    try:
        check_args(name, args)
        out = (github if PROVIDER == "github" else gitlab)(name, args, state)
        save(state)
        text = out if isinstance(out, str) else json.dumps(out)
        error = False
    except Fail as e:
        text, error = str(e), True
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps({"tool": name, "args": args, "error": error, "result": text[:300]}) + "\n")
    result = {"content": [{"type": "text", "text": text}]}
    if error:
        result["isError"] = True
    return result


def main():
    for line in sys.stdin:
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        if "id" not in msg:
            continue
        method = msg.get("method")
        if method == "initialize":
            result = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}},
                      "serverInfo": {"name": f"fake-{PROVIDER}", "version": "0"}}
        elif method == "tools/list":
            result = {"tools": list(TOOLS.values())}
        elif method == "tools/call":
            result = handle_call(msg["params"]["name"], msg["params"].get("arguments") or {})
        elif method == "ping":
            result = {}
        else:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg["id"],
                                         "error": {"code": -32601, "message": f"{method} not supported"}}) + "\n")
            sys.stdout.flush()
            continue
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg["id"], "result": result}) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
