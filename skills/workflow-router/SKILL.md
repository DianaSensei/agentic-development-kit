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

This skill's ONLY job: classify the request correctly, then hand off - it does NOT do any analysis or
implementation itself (that's `feature-development`'s/`bug-fix`'s/`refactor`'s job).

## The Problem to Solve
Users phrase requests many different ways, and don't always say clearly "this is a new feature" or
"this is a bug fix":
- Clearly a feature: "build a new feature", "need to add capability X", "add ability Y".
- Clearly a bug: "fix the bug", "fix issue X", "the app crashes when...".
- **AMBIGUOUS, needs careful distinction**: "change mechanism A", "implement B", "improve C", "enhance
  D" - these phrases can mean either a NEW feature or fixing behavior that's CURRENTLY WRONG, depending
  on the actual context - it can't be guessed from the surface wording alone.

## Classification Principle (based on TRUE NATURE, not keywords)
The core question to answer: **is the system's current behavior actually WRONG relative to its original
design/expectation? And does the request change external behavior at all?**

- **Current behavior is actually WRONG** (even if the user says "improve"/"enhance"/"change mechanism")
  → `bug-fix`. E.g. "improve the retry mechanism that's currently looping infinitely."
- **Current behavior is CORRECT, and new/expanded capability is needed, or a deliberate change to a
  different spec (external behavior WILL change on purpose)** → `feature-development`. E.g. "change the
  loyalty-points mechanism from per-order to per-value."
- **Current behavior is CORRECT and MUST stay that way - only code structure/performance/maintainability
  improves (nothing a user can observe from outside changes)** → `refactor`. E.g. "restructure order
  processing to be easier to test, no behavior change", "merge the duplicated logic in OrderService and
  ProductService", "clean up the code structure to be easier to extend."

This is exactly why words like "improve"/"change mechanism"/"enhance" are especially ambiguous - they
can fall into ALL THREE categories depending on context. The deciding question is always: *"does
external behavior change, and if so, is it because something was broken or because capability is being
expanded/changed on purpose?"*

## Process
1. Read the request, cross-check against the existing code/logic (a quick read, not as deep as the
   target workflow will do on its own) to determine: is current behavior actually wrong, and does the
   request change external behavior at all? Whatever was read at this step (files, code, context) stays
   available in the session - the target workflow's own Step 0 reuses it, no need to re-read from
   scratch just because the skill changed.
2. If **clearly** one of the three types → state the chosen classification in one sentence, then hand
   off immediately, no need to ask further.
3. If **still ambiguous** after reading the code - ask back BRIEFLY, exactly one single-select question
   with 3 options: "Is this: (a) NEW capability/spec change (feature), (b) fixing behavior that's
   CURRENTLY WRONG (bug fix), or (c) only improving the code WITHOUT changing external behavior
   (refactor)?"
4. Once determined, state it explicitly: *"Classified as [feature-development/bug-fix/refactor],
   handing off to that workflow."* - never hand off silently.

## When It Doesn't Cleanly Fit Any of the Three
Rare - e.g. a pure tooling/CI/infra change unrelated to business code or behavior. There is currently no
dedicated workflow for this "platform/infra" case. If this comes up, tell the user plainly this is a
current gap, and ask how they'd like to proceed (usually closest to `refactor` in process - has a
checkpoint, has verification, no new AC) rather than choosing unilaterally.
