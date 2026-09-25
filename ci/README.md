# CI: independent review

Every pull or merge request gets a second reviewer that did not write it: a fresh Claude session
running this kit's [`independent-review`](../skills/independent-review/SKILL.md) skill. It checks the
change against its own intent and plan (`docs/intents/`, `docs/plans/`), applies `code-review-skill`'s
checklist plus the technical skill that owns each changed file, and leaves:

- an **inline comment per finding**, each starting with **blocking**, **suggestion**, or **question**;
- **one summary comment** - intent met or not, every finding, risk for the approver, what was not
  checked - edited in place on every push instead of piling up.

It never edits, pushes, or approves. The summary gives counts, not a yes/no, so nobody mistakes it for
the approval: a person still approves, and can spend that attention on intent and risk instead of on
every line.

## How it runs

The same runner, [`review.sh`](./review.sh), on GitHub Actions and GitLab CI:

1. `git diff` of the change - no code-host API needed to read it;
2. Claude reviews it **read-only, with no MCP server and nothing it can post with**, and returns the
   summary, the counts and each finding as structured output;
3. [`codehost/codehost.py`](../codehost/README.md) posts them through the provider's own MCP server;
4. optionally, the job fails on blocking findings.

The model reads the pull request - text anyone can write into - so it gets no tool that writes
anywhere. What it returns is posted by a script.

## GitHub Actions

1. **A credential**, as a repository secret (Settings → Secrets and variables → Actions), either
   `ANTHROPIC_API_KEY` (an API key from the Anthropic Console) or `CLAUDE_CODE_OAUTH_TOKEN` (from
   `claude setup-token`, to bill a Claude subscription instead).
2. **The caller**: copy [`independent-review.yml`](./independent-review.yml) to your project's
   `.github/workflows/`.

No GitHub App to install: the job posts as `github-actions[bot]` with its own token, through
[GitHub's MCP server](https://github.com/github/github-mcp-server) (a pinned, checksum-verified release).

Until a secret is set the job passes with a warning instead of failing, so adding the caller first is
safe. PRs from forks never receive secrets and are skipped the same way - that is GitHub's rule, and the
reason this workflow does not use `pull_request_target`, which would hand a secret to code from a fork.

GitHub's MCP server can attach inline comments only to the reviewer's first review of a pull request
([details](../codehost/README.md#known-limitation-github-inline-comments-on-a-re-review)): later pushes
update the summary comment, which always lists every finding.

## GitLab CI

1. **Two masked CI/CD variables** (Settings → CI/CD → Variables):
   - `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN`, as above;
   - `ADK_GITLAB_TOKEN` - a project access token (Settings → Access tokens) with the **Reporter** role and
     the **`api`** scope. The review is posted as that token's bot user.
2. **The include**, in your `.gitlab-ci.yml`:

   ```yaml
   include:
     - remote: https://raw.githubusercontent.com/DianaSensei/agentic-development-kit/main/ci/gitlab/independent-review.yml
       inputs:
         kit_ref: main
   ```

The job runs on merge request pipelines, skips drafts, and uses the `node:22-bookworm` image. It posts
through [`@zereight/mcp-gitlab`](https://github.com/zereight/gitlab-mcp), pinned: GitLab's own MCP server
only accepts OAuth sign-in, which a pipeline cannot complete. A missing variable is a warning (exit code
3, allowed to fail), not a red pipeline.

## Options

| GitHub input / GitLab input | Default | |
|---|---|---|
| `kit_ref` | `main` | Branch or tag of the kit the reviewer's skills come from. Pin it to the same tag as the `uses:` line or the include URL. |
| `fail_on_blocking` | `false` | Fail the check when the review reports blocking findings. Turn it on once the findings have earned your trust on a few weeks of changes, then make the check required. |
| `model` | Claude Code's default | Model for the reviewer. |
| `extra_instructions` | - | Project-specific instructions appended to the prompt, e.g. which paths are high risk. |
| `kit_repository` / `kit_repository_url` | this repo | Only for a fork or an internal mirror of the kit. |
| - / `stage` | `test` | GitLab only: the stage the job runs in, when your `stages:` has no `test`. |

## Another CI or another host

`review.sh` is plain bash plus Python's standard library; a CI template only maps its variables onto
the environment the script documents. Another code host needs a profile and a class in `codehost/` -
see [Adding a provider](../codehost/README.md#adding-a-provider).

## Getting good reviews

The reviewer is only as specific as what it can read:
- **A `CLAUDE.md`** with your conventions - a broken `CLAUDE.md` rule is a blocking finding.
- **An intent and plan per change** (`intent-capture`, `feature-development`) - without them it can only
  check that the code is correct, not that it is the right change. It says "no intent or plan linked" when
  it finds none.
- **Your stack in `skill_map`** (`.claude/quality-check.config.json`), so it reads the technical skill
  that owns each changed file.

## What it does not do

- **Run your tests.** Your existing CI does that; the summary always says tests were not run by the
  review.
- **Gate on its own honesty.** `fail_on_blocking` trusts the count the model reports. Text in a change
  can try to talk a reviewer out of a finding; the prompt treats all of it as data, but a person reading
  the diff remains the last line.
- **Review drafts.** Marking the change ready for review triggers it.
