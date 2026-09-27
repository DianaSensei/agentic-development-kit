---
name: workflow-router
description: Use FIRST for any request asking Claude to WRITE OR CHANGE code - new feature, bug fix, refactor, enhancement, "improve", "add capability", etc. Classifies the request as feature-development, bug-fix, or refactor by its true nature (does external behavior change, and if so is it fixing a defect or adding/changing capability?), asking the user only if genuinely ambiguous, and picks the depth the change deserves - quick-change for a small change with nothing to decide, light or full process otherwise - then hands off. Skip when the request type is already obvious. Also the entry point for "implement/build/fix docs/intents/<slug>.md". Do NOT use for no-code-change requests - pure questions/explanations, read-only exploration, or explicit review requests ("review this PR/diff") - handle those directly instead; and not for recording an idea to build later - that is `intent-capture`.
metadata:
  domain: workflow
  triggers: write code, add feature, fix bug, implement, classify request
  role: orchestrator
  scope: routing
  output-format: handoff
  related-skills: feature-development, bug-fix, refactor, quick-change, intent-capture, project-setup
---

# Dev Request Router

Classify, then hand off. This skill does no analysis and no implementation itself - that belongs to
`feature-development` / `bug-fix` / `refactor`.

## Classify by true nature, not by keywords

The deciding question: **is the system's current behavior actually WRONG relative to its intended
design, and does the request change external behavior at all?**

| Answer | Workflow | Example |
|---|---|---|
| Current behavior is **wrong** | `bug-fix` | "improve the retry mechanism that's currently looping infinitely" |
| Current behavior is **correct**; new or deliberately changed capability, external behavior changes on purpose | `feature-development` | "change loyalty points from per-order to per-value" |
| Current behavior is **correct and must stay identical**; only structure/performance/maintainability improves | `refactor` | "restructure order processing to be easier to test, no behavior change" |

Words like **"improve" / "enhance" / "change mechanism X"** land in all three depending on context, so
they can never be classified from the wording alone - that ambiguity is the reason this skill exists.

## Then pick the depth - proportional to the change

The type says which workflow; the depth says how much process it gets. Full process on a two-line fix
is waste, and a quick edit on a migration is a risk - decide from what the change touches, not from
how the request is worded.

| Tier | When | Goes to |
|---|---|---|
| **quick** | Every `quick-change` entry criterion holds: one obvious form with nothing to decide, about 3 files and 60 lines at most, no expensive path (schema/migration, public API or message contract, auth/security, money, CI/deploy config, dependencies, `.claude/`, `CLAUDE.md`) | `quick-change` |
| **standard** | Clear and within one area, no expensive path - but there is a decision to make, or it is bigger than quick | the workflow at **light** depth |
| **full** | Crosses services or layers, touches an expensive path, starts from an intent, or the request is ambiguous | the workflow at **full** depth |

**Decide the tier from the paths, not the size of the fix.** List the files the change will touch, and
check each against the expensive paths - a directory or file named for migrations, auth, security,
crypto, payments, billing or checkout; CI and deployment files; API and message contracts
(`openapi`, `asyncapi`, `.proto`); dependency manifests; `.claude/` and `CLAUDE.md`; and the project's
own `quick_change.sensitive_paths` in `.claude/quality-check.config.json` if it sets them. One hit rules
out **quick**, however small the fix: a one-line change in `src/auth/` is still auth. Then ask whether
existing data or other callers are affected - a fix that needs a data migration or changes what
callers receive is not quick either.

When in doubt between two tiers, take the heavier one: an unneeded Checkpoint costs a minute, a
missed one can cost an incident. The user's words override the tier either way - "full process",
"just do it" - and `quick-change` says how to handle "just do it" on a risky change.

Say the tier with the workflow in the handoff sentence: "bug-fix, light depth: ..." or "quick change:
...". The machine checks - owning skill read, convention checks, tests run, self-review - apply at every
tier; only the analysis, documents and agents scale.

## Process

1. Read the request and cross-check it against the existing code - a quick read with `Grep` and `Read`
   yourself, not a subagent and not the depth the target workflow will go to. Whatever gets read stays in the session; the target's Step 0 reuses it
   rather than starting over.
   If the request names an intent (`docs/intents/<slug>.md`, written by `intent-capture`), read it and
   classify from its Problem and Desired outcome. Its `type` is the originator's hint, not the answer -
   a "feature" whose problem is behavior that is wrong today is still a `bug-fix`. Pass the path on in
   the handoff; the target workflow reads it in its Step 0.
2. Clearly one of the three → pick the tier (above), state both in one sentence and hand off. Don't
   ask.
3. Still ambiguous after reading the code → ask exactly one single-select question: is this (a) new
   capability or a spec change, (b) fixing behavior that is currently wrong, or (c) improving code
   without changing external behavior?
4. Always say which workflow was chosen before handing off - never hand off silently.

## When it fits none of the three

Rare, e.g. a pure tooling/CI/infra change touching no business behavior. One common case has an owner:
setting a repository up for this kit (`CLAUDE.md`, `REVIEW.md`, `CODEOWNERS`, `.claude/settings.json`,
the CI reviewer) is `project-setup`, so hand off to it. For anything else there is no dedicated
workflow: say so plainly as a known gap and ask how the user wants to proceed - usually closest to
`refactor` (checkpoint, verification, no new acceptance criteria) - rather than picking unilaterally.
