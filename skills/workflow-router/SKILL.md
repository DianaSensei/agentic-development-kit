---
name: workflow-router
description: Use FIRST for any request asking Claude to WRITE OR CHANGE code - new feature, bug fix, refactor, enhancement, "improve", "add capability", etc. Classifies the request as feature-development, bug-fix, or refactor by its true nature (does external behavior change, and if so is it fixing a defect or adding/changing capability?), asking the user only if genuinely ambiguous, then hands off. Skip when the request type is already obvious. Do NOT use for no-code-change requests - pure questions/explanations, read-only exploration, or explicit review requests ("review this PR/diff") - handle those directly instead.
metadata:
  domain: workflow
  triggers: write code, add feature, fix bug, implement, classify request
  role: orchestrator
  scope: routing
  output-format: handoff
  related-skills: feature-development, bug-fix, refactor
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

## Process

1. Read the request and cross-check it against the existing code - a quick read, not the depth the
   target workflow will go to. Whatever gets read stays in the session; the target's Step 0 reuses it
   rather than starting over.
2. Clearly one of the three → state the classification in one sentence and hand off. Don't ask.
3. Still ambiguous after reading the code → ask exactly one single-select question: is this (a) new
   capability or a spec change, (b) fixing behavior that is currently wrong, or (c) improving code
   without changing external behavior?
4. Always say which workflow was chosen before handing off - never hand off silently.

## When it fits none of the three

Rare, e.g. a pure tooling/CI/infra change touching no business behavior. There is no dedicated workflow
for that case. Say so plainly as a known gap and ask how the user wants to proceed - usually closest to
`refactor` (checkpoint, verification, no new acceptance criteria) - rather than picking unilaterally.
