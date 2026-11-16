# Tracker operations

What the kit asks of a tracker, and the tool that does it on each. Tools show up as
`mcp__<server>__<tool>`. Each column names its source, read 2026-11-16; a name marked *summary* came from
a summary of the vendor's page, not its text - confirm it against the server's own tool list before
relying on it, and if the server shows another name, the server is right.

| Operation | GitHub (official server) | GitLab (official, `/api/v4/mcp`) | Jira / Confluence (Atlassian, `/v2/mcp`) |
|---|---|---|---|
| **read the ticket** | `issue_read` `method: get`, then `method: get_comments` | `get_work_item` (GitLab 19.4+; before it, `get_issue`) | `getJiraIssue` |
| **comment** | `add_issue_comment` | `save_note` `method: create_note`, `work_item_iid`, `body` | `addOrEditJiraIssueComment` |
| **statuses it can move to** | `projects_get` `method: get_project_item`, `field_names: ["Status"]` - *summary*; needs the `projects` toolset | `status_id` values (Premium, Ultimate); otherwise the project's workflow labels | `listJiraIssueTransitions` |
| **move the status** | `projects_write` `method: update_project_item`, `updated_field: {"name": "Status", "value": ...}` - *summary* | `save_work_item` `status_id` (Premium, Ultimate), or `add_labels` / `remove_labels` for labels the project already uses | `transitionJiraIssue` - the transition only; pass no sprint or assignee |
| **search** | - | `list_work_items` | `searchJiraIssuesUsingJql`; Confluence `searchConfluence` |
| **read a linked page** | - | - | `getConfluenceContent` |
| **never called** | `issue_write` `state: closed` (closing is the person's) | `save_work_item` `state: closed` | `createJiraIssue`, `editJiraIssue` |

## Per tracker

**GitHub.** An issue is only open or closed. A status such as "In Progress" lives in a GitHub Project
the issue belongs to, as a single-select field, and needs the server's `projects` toolset, which is off
by default (the default set is `context, repos, issues, pull_requests, users`). Not in a project, or no
toolset → comment only.

**GitLab.** A work item's `state` is opened or closed; its status (`status_id`) is a separate field on
Premium and Ultimate. Without it, a project may track status with labels: move only between labels it
already uses, removing the old one as the new one is added. Tool names changed in GitLab 19.4
(`get_issue` → `get_work_item`, `create_issue` → `save_work_item`); use what the server lists.

**Jira.** Atlassian Cloud only - the pages describe no Data Center support. Call
`getAccessibleAtlassianResources` first for the `cloudId`. Workflows differ per project, so read the
transitions every time; a transition's name is not its target status, so match on the status it leads
to. Actions respect the person's own Jira and Confluence permissions.

## Sources

- GitHub: https://github.com/github/github-mcp-server (README; the projects section from its summary).
- GitLab: https://docs.gitlab.com/user/model_context_protocol/mcp_server_tools/ - `save_work_item`:
  "`closed` closes the work item, `opened` reopens it"; `status_id`: "Premium and Ultimate only";
  `get_issue`: "Unlisted in GitLab 19.4. Superseded by get_work_item."
- Atlassian: https://support.atlassian.com/atlassian-rovo-mcp-server/docs/supported-tools/ - tool names
  and groups; https://support.atlassian.com/atlassian-rovo-mcp-server/docs/getting-started-with-the-atlassian-remote-mcp-server/
  - the Claude Code command and "secure OAuth 2.1 authorization";
  https://github.com/atlassian/atlassian-mcp-server - "v2 is now the recommended version".
