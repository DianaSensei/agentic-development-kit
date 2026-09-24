# CI: independent review

Every pull request gets a second reviewer that did not write it: a fresh Claude session running this
kit's [`independent-review`](../skills/independent-review/SKILL.md) skill. It checks the change against
its own intent and plan (`docs/intents/`, `docs/plans/`), applies `code-review-skill`'s checklist plus
the technical skill that owns each changed file, and leaves:

- an **inline comment per finding**, each starting with **blocking**, **suggestion**, or **question**;
- **one summary comment** - intent met or not, findings, risk for the approver, what was not checked -
  edited in place on every push instead of piling up.

It never edits, pushes, or approves. The summary gives counts, not a yes/no, so nobody mistakes it for
the approval: a person still approves, and can spend that attention on intent and risk instead of on
every line.

## Setup

1. **A credential**, as a repository secret (Settings → Secrets and variables → Actions), either:
   - `ANTHROPIC_API_KEY` - an API key from the Anthropic Console, or
   - `CLAUDE_CODE_OAUTH_TOKEN` - from `claude setup-token`, to bill a Claude subscription instead.
2. **The caller**: copy [`independent-review.yml`](./independent-review.yml) to your project's
   `.github/workflows/`.

That's all. No GitHub App to install: the workflow comments as `github-actions[bot]` using the job's own
token.

Until a secret is set, the job passes with a warning instead of failing, so adding the caller first is
safe. PRs from forks never receive secrets, so they are skipped the same way - that is GitHub's rule, and
the reason this workflow does not use `pull_request_target`, which would hand a secret to code from a
fork.

## Options

| Input | Default | |
|---|---|---|
| `kit_ref` | `main` | Branch or tag of the kit the reviewer's skills come from. Pin it to the same tag as the `uses:` line. |
| `fail_on_blocking` | `false` | Fail the check when the review reports blocking findings. Turn it on once the findings have earned your trust on a few weeks of PRs, then make the check required in branch protection. |
| `model` | action default | Model for the reviewer. |
| `extra_instructions` | - | Project-specific instructions appended to the prompt, e.g. which paths are high risk. |
| `kit_repository` | this repo | Only for running a fork of the kit. |

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
- **Gate on its own honesty.** `fail_on_blocking` trusts the count the model reports. Text in a PR can
  try to talk a reviewer out of a finding; the prompt treats all PR content as data, but a person
  reading the diff remains the last line.
- **Review drafts.** Marking the PR ready for review triggers it.
