# Code host

How the kit's pipelines reach GitHub or GitLab: through the provider's own MCP server, never its CLI or
REST API, and never through the model.

```
ci/review.sh ────┐                         ┌─► github-mcp-server (GitHub's official)
                 ├─► codehost.py ── MCP ───┤
maintain/run.sh ─┘   (deterministic)       └─► @zereight/mcp-gitlab (GitLab)
```

In CI, Claude returns data - review findings, a summary - and has no code-host tool at all.
[`codehost.py`](./codehost.py) posts that data by starting the provider's MCP server from its profile and
calling its tools as an MCP client. That keeps the pipelines provider-neutral and keeps a write-capable
tool out of reach of a model that is reading untrusted pull request content.

Interactive sessions reach the code host through the same kind of server, connected by the
[`code-host`](../skills/code-host/SKILL.md) skill, which also maps each operation to each provider's tools.

## Operations

| Command | What it does | GitHub tools | GitLab tools |
|---|---|---|---|
| `publish-review` | an inline comment per finding the diff can place, then one summary comment, edited in place on every run | `pull_request_read`, `pull_request_review_write`, `add_comment_to_pending_review`, `add_issue_comment`, `update_issue_comment` | `get_merge_request`, `create_merge_request_thread`, `get_merge_request_notes`, `create_merge_request_note`, `update_merge_request_note` |
| `upsert-comment` | the summary-comment logic alone, for any marker | the comment tools above | the note tools above |
| `ensure-change` | find the open pull/merge request from a branch, or open one | `list_pull_requests`, `create_pull_request` | `list_merge_requests`, `create_merge_request` |

A finding the diff cannot place (a line outside every hunk, a file not in the diff) or the server
refuses is never lost: the summary lists every finding, and says which ones are not inline and why.

## Providers

| Provider | Server in CI | Token |
|---|---|---|
| GitHub (and GitHub Enterprise Server) | [github/github-mcp-server](https://github.com/github/github-mcp-server) `v1.12.2`, the release binary, checked against the sha256 in [`providers/github.json`](./providers/github.json) | the job's own `GITHUB_TOKEN` |
| GitLab (gitlab.com and self-managed) | [`@zereight/mcp-gitlab`](https://github.com/zereight/gitlab-mcp) `2.1.66` through `npx` | a project access token, `ADK_GITLAB_TOKEN` |

**Why not GitLab's own MCP server in CI**: it signs in with OAuth only, which needs a browser; a
pipeline cannot complete it
([gitlab-org/gitlab#586184](https://gitlab.com/gitlab-org/gitlab/-/issues/586184), open). People at
their desks use GitLab's own server (`code-host` connects it); pipelines use the community server,
pinned, with a token scoped to one project. When GitLab accepts tokens, switching is a profile change.

Each profile lists the only tools the kit calls. The server is started with just those enabled where it
supports that (`--tools` on GitHub's; `GITLAB_TOOLS` on the community GitLab server, which also forbids
deletes with `GITLAB_PERMISSION_MODE=modify`).

## Known limitation: GitHub inline comments on a re-review

GitHub's server finds "the latest review" with `reviews(first: 1, author: <viewer>)`, which is the
viewer's *oldest* review. Once the reviewer has submitted one review on a pull request, it can no longer
add comments to a new one. So on GitHub the first review of a pull request carries inline comments and
later pushes update the summary comment only; `publish-review` checks first rather than leaving a
stranded pending review behind. GitLab has no such limit.

## Adding a provider

1. `providers/<provider>.json` - how to start its MCP server and the tools the kit may call, and
   `providers/<provider>.tools.json` - the server's real `tools/list` for those tools.
2. A class in `codehost.py` with `upsert_comment`, `inline`, `find_change` and `open_change`.
3. The fake server's behaviour for those tools in `tests/fake_server.py`, and tests.
4. A CI template that maps the CI's variables onto `ci/review.sh` and `maintain/run.sh`.

## Tests

```bash
python3 -m unittest discover -s codehost/tests
```

No network and no account: [`tests/fake_server.py`](./tests/fake_server.py) serves the real tool
schemas and copies the behaviour that matters, GitHub's pending-review lookup included. The kit's
`skill-evals.yml` runs them on every pull request.
