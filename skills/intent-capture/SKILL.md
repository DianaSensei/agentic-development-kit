---
name: intent-capture
description: Captures an idea, problem, or request that is NOT yet being built as a version-controlled `docs/intents/<slug>.md` - the problem, who it hurts and the evidence, the desired outcome and how success would be observed, non-goals, affected systems, constraints, open questions - with no solution design and no code. Use when the user has an idea, a pain point, user complaints, or an alert/incident worth following up, or says "capture/record/write up this idea", "write an intent", "add this to the backlog", "we should...", "what if we..."; also to review the intent backlog or record a decision on one ("what intents are open", "accept/reject intent X"). Do NOT use when the user wants the change built now - that goes to `workflow-router`, which takes an existing intent as its input; and not for a document arguing an already-chosen technical approach to approvers - that is `technical-proposal-writer`.
metadata:
  domain: requirements
  triggers: capture idea, write intent, backlog, problem statement, triage intents, ý tưởng
  role: specialist
  scope: documentation
  output-format: document
  related-skills: workflow-router, feature-development, bug-fix, refactor, technical-proposal-writer
---

# Intent Capture

The first file in the chain `docs/intents/<slug>.md` → `docs/plans/<slug>.md` → `docs/changelog/<slug>.md`.
An intent records *why* a change should exist, before anyone decides *how*. It is written with the
person who had the idea (the originator), committed to the repo, and later read by `workflow-router`
and the orchestrators as their starting input - so the reason behind a change outlives the chat it was
raised in.

This skill writes Markdown under `docs/intents/` only. It never edits code and never starts
implementation.

Input: `$ARGUMENTS`

## Pick the mode

| The user... | Mode |
|---|---|
| has a new idea, pain point, request, or an alert/incident to follow up | **Capture** |
| asks what intents exist, or which are waiting on a decision | **Review** |
| accepts, rejects, or supersedes an intent | **Decide** |

## Capture

### Step 1 - Look for an existing intent

List `docs/intents/*.md` and read the frontmatter and `## Problem` of any whose title or slug overlaps
the request. Same problem → update that file (new evidence, sharper outcome, a Decision log line)
instead of creating a second one. Partial overlap → ask the user whether it is the same intent.
Duplicates split the evidence and make every later decision twice.

### Step 2 - Read just enough code to be concrete

Read `CLAUDE.md` if present, then a quick pass over the code the problem touches - which modules,
services, screens, or data. This is orientation, not design; `business-analyst` goes deep later. Every
row in *Affected systems* needs a source (a path, a doc, or "originator said"), the same provenance rule
`business-analyst` follows. No codebase in reach (a pure product idea) → write "not yet checked" rather
than guessing.

### Step 3 - Interview the originator

Work through the template's sections (`references/intent-template.md`) using what the user already
said first, then ask only for what is missing. Batch it: one `AskUserQuestion` call (up to 4 questions) for anything with enumerable answers -
who is affected, urgency, which system - and plain chat for the rest. One or two rounds is the target:
an intent is a starting point, not a specification.

Press on four things:

- **Problem, not solution.** "Add a Redis cache" is a solution; "the product page takes seconds to load
  on mobile and users leave" is a problem. When the originator arrives with a solution, ask what it
  fixes, and keep their idea under *Originator's idea (non-binding)* - recorded, but design stays open.
- **Evidence.** A ticket, a log line, a metric, a customer quote, a count of support requests. None →
  write "none yet"; never imply evidence exists.
- **An observable outcome.** How would someone other than the originator tell, after the change, that it
  worked? A target number the originator did not give is "needs confirmation", never an invented one.
- **Non-goals.** What this intent deliberately leaves out - the cheapest scope control available.

### Step 4 - Check it against the readiness bar

- The Problem names no solution.
- Evidence lists at least one source, or says "none yet" explicitly.
- The Desired outcome is observable by someone other than the originator.
- Every Affected systems row has a source.
- No number, date, or name appears that the user did not give or the code did not show.

All pass → status `proposed`. Any fail → status `draft`, and say which item failed.

### Step 5 - Write the file

`Read` `references/intent-template.md` now, even if its shape seems obvious, and write
`docs/intents/<slug>.md` in exactly that shape: the same frontmatter keys (no additions, empty ones left
empty), the `# <title>` heading, and every section in the same order. A section with nothing known
still appears, saying "none stated" / "needs confirmation" / "none yet" - never dropped. Review mode and
the orchestrators find statuses and links by those fixed keys and headings; an intent shaped
differently is one they silently miss. *Decision log* always starts with the `created` line.

Then run `scripts/check-intent.sh docs/intents/<slug>.md` (the script sits in this skill's directory,
next to this `SKILL.md`). Fix every line it prints and re-run until it exits 0. Do not report the intent
as captured before it passes - models drift from a template they have just read, and this check is how
that drift gets caught instead of reaching Review mode.

The slug is the filename, not a frontmatter key. It names the problem, not a solution
(`mobile-product-page-slow`, not `add-redis-cache`), because downstream workflows reuse it as
`<feature-slug>` / `<bug-slug>` / `<refactor-slug>` - choose it once.

Do not commit unless the user asks. Do say that the file is meant to be committed: it is the audit
trail for why the change was made.

### Step 6 - Hand off

Report the path, the status, and any open questions, then stop. The next move belongs to the user:
- `proposed` → someone decides (Decide mode).
- `accepted` and wanted now → "implement `docs/intents/<slug>.md`", which enters `workflow-router`.
  If the user asks for that in the same breath, hand off to `workflow-router` with the path.

### Machine-raised intents

When the input is an alert, log excerpt, failing job, or incident thread rather than a person (the
maintain end of the loop - the kit's `maintain/` workflow raises these on its own), there may be
nobody to interview:
- `originator` is the source (`monitoring/<alert name>`, `incident/<id>`) - a slash, not a colon, so
  the frontmatter stays valid YAML.
- *Evidence* quotes the raw signal, trimmed to what matters, with secrets and personal data redacted.
- Skip Step 3; everything the signal cannot answer goes to *Open questions*.
- `type` is usually `bug`, but leave the call to `workflow-router`.

## Review

Read-only. Run `scripts/check-intent.sh docs/intents/*.md` first and list any file it flags - a
malformed intent would otherwise be missing from the table without anyone noticing. Then read the
frontmatter of every `docs/intents/*.md` and present one table grouped by status,
`proposed` first (they are waiting on a decision), with title, originator, created, and age. Then flag:
- the oldest `proposed` intents;
- `plan` or `changelog` links pointing at a file that does not exist;
- counts of `accepted` vs `rejected` - the acceptance rate says whether intents are being raised at the
  right level of readiness.

## Decide

Accepting or rejecting is a person's decision. This skill records it and never makes it. Update
`status` and `updated`, and append to *Decision log*: the date, who decided (the name the user gives,
otherwise "user"), and the reason. Ask for the reason when a rejection has none - "rejected, no reason"
teaches the next originator nothing.

Rejected intents stay in the repo. Deleting one loses the record that the idea was considered and why
it was turned down. `superseded` also sets `superseded_by: <slug>`. Run `scripts/check-intent.sh` on the
file after the edit.

## Status lifecycle

| Status | Set by | Means |
|---|---|---|
| `draft` | this skill | captured; readiness bar not met |
| `proposed` | this skill | ready for a decision |
| `accepted` | a person, via Decide | approved to build |
| `rejected` | a person, via Decide | turned down, reason recorded |
| `in-progress` | the orchestrator, at its CHECKPOINT | an approach was chosen; `plan` linked |
| `done` | the orchestrator, at knowledge capture | shipped; `changelog` linked |
| `superseded` | a person, via Decide | replaced by `superseded_by` |

## Boundaries

- Problem and outcome only. Acceptance criteria, edge cases, and DoD belong to `business-analyst` in
  `feature-development` Step 1; approaches belong to `solution-architect`. An intent that grows
  acceptance criteria is doing the next step's job without the code context to do it well.
- Feature vs. bug vs. refactor is `workflow-router`'s call. The `type` field is the originator's hint,
  not a classification.
- `technical-proposal-writer` argues for an approach that has already been chosen; an intent comes
  before any approach exists. An accepted intent can seed a proposal's problem section.
- Writes only under `docs/intents/`. Never edits code, never commits unless asked.
