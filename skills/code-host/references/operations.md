# Code-host operations

What the kit asks of a code host, and the tool that does it on each provider. Tools show up as
`mcp__<server>__<tool>` - `mcp__codehost__pull_request_read` for a server named `codehost`. The
GitHub and GitLab-community names below were read from the servers' own `tools/list`
(`codehost/providers/*.tools.json`); the GitLab-official names come from GitLab's documentation.

| Operation | GitHub (official server) | GitLab (official, `/api/v4/mcp`) | GitLab (community, `@zereight/mcp-gitlab`) |
|---|---|---|---|
| **read change** - title, description, branches, head SHA | `pull_request_read` `method: get` | `get_merge_request` | `get_merge_request` |
| **read diff** | `pull_request_read` `method: get_diff` | `get_merge_request_diffs` | `get_merge_request_diffs`, or `list_merge_request_changed_files` then `get_merge_request_file_diff` for a large one |
| **list comments** | `pull_request_read` `method: get_comments` | `get_merge_request_notes` | `get_merge_request_notes` |
| **post a finding on a line** | the pending-review sequence below | `save_merge_request_review` `method: create_diff_note` (GitLab 19.4+) | `create_merge_request_thread` with `position` |
| **post a comment** | `add_issue_comment` (`issue_number` = the PR number) | `save_note` | `create_merge_request_note` |
| **edit a comment** | `update_issue_comment` | not offered - post a new one | `update_merge_request_note` |
| **find an open change request** | `list_pull_requests` `head: <owner>:<branch>`, `state: open` | `list_merge_requests` | `list_merge_requests` `source_branch`, `state: opened` |
| **open a change request** | `create_pull_request` | `save_merge_request` (GitLab 18.5+) | `create_merge_request` |

## GitHub: inline findings are a pending review

1. `pull_request_review_write` `method: create`, no `event` - opens a pending review.
2. `add_comment_to_pending_review` once per finding: `path`, `line`, `side: RIGHT` (a line in the new
   file) or `LEFT` (a deleted line), `subjectType: LINE`, `body`.
3. `pull_request_review_write` `method: submit_pending`, `event: COMMENT`.

Known limitation (github-mcp-server 1.12): the server finds "the latest review" with
`reviews(first: 1, author: <you>)` - your *oldest* review on that pull request. Once you have submitted
any review there, steps 2 and 3 fail with "latest review ... is not pending", and so does
`delete_pending`. Before step 1, list `pull_request_read` `method: get_reviews`; if you already have a
submitted review on it, put the findings in a comment instead of inline.

## GitLab: a line needs a position

GitLab's discussions API places a line with a `position`. The community server's
`create_merge_request_thread` takes it as below; for the official server's `create_diff_note`, read the
tool's input schema for its field names - the rules are the same API's:
- `base_sha`, `start_sha`, `head_sha` - from the merge request's `diff_refs`
  (`get_merge_request`); never guessed;
- `position_type: text`, `new_path` and `old_path` (the same unless the file was renamed);
- an added line: `new_line` only; a deleted line: `old_line` only; an unchanged line inside a hunk:
  **both** - GitLab rejects a context line given one number.

A line outside the diff's hunks cannot carry a thread on either provider: put that finding in the
summary comment.

## The summary comment

One comment per change, found again by a marker on its first line (`<!-- adk-independent-review -->`
for the reviewer) and edited in place rather than posted again - on GitLab's official server, which
cannot edit, a new one is posted. Only edit a marked comment written by the same account; a person
quoting the marker must not have their comment overwritten.
