---
name: technical-proposal-writer
description: Writes and structures technical proposal documents (RFCs, đề xuất kỹ thuật, đề xuất giải pháp, đề xuất dự án) that argue for a technical decision to stakeholders or approvers - problem/context, goals, proposed solution, alternatives considered, risks, implementation plan, timeline and resources. Use whenever the user asks to write, draft, or review a technical proposal, RFC, design doc meant for approval, project proposal, or any "đề xuất" document - in Vietnamese or English - especially when it needs to persuade a reader (lead, leadership, another team) to approve a course of action, not just describe how a system works.
metadata:
  domain: requirements
  triggers: technical proposal, RFC, đề xuất kỹ thuật, đề xuất giải pháp, đề xuất dự án, design doc, proposal document, decision document, project proposal, persuasive writing, kế hoạch triển khai
  role: specialist
  scope: documentation
  output-format: document
  related-skills: architecture-designer, api-contract-skill, code-documenter
---

# Technical Proposal Writer

Specialist for the document that asks someone to say yes to a technical decision - an RFC, a design
doc awaiting approval, or a Vietnamese-style "đề xuất kỹ thuật" / "đề xuất dự án". The job here is
argument and structure, not the underlying engineering choice: this skill assumes the technical
direction is basically settled (or being settled alongside `architecture-designer`) and turns it into
a document a specific reader can evaluate and approve.

## When to Use This Skill

- Writing an RFC or design doc that needs sign-off from peers, a tech lead, or leadership.
- Writing a Vietnamese "đề xuất kỹ thuật" / "đề xuất giải pháp" / "đề xuất dự án" for stakeholders.
- Turning an already-decided architecture (e.g. `architecture-designer` output, an ADR, a discussion
  thread) into a stakeholder-facing document.
- Writing a project/technical proposal that needs a timeline, resourcing, and risk section, not just a
  technical description.
- Reviewing a draft proposal for gaps - missing alternatives, hidden assumptions, no risk section -
  before it goes out.

## Core Workflow

1. **Clarify the decision at stake.** Before drafting, find out: what decision is this document trying
   to get made, who actually approves it (a technical peer? leadership without deep technical context?
   another team?), and how much has already been informally discussed/ruled out. A doc written without
   knowing the reader ends up either too technical for leadership or too shallow to satisfy engineers -
   this is the single biggest cause of a proposal that reads as unconvincing.
2. **Gather the technical substance from real sources.** Pull the rationale from existing design
   artifacts - `architecture-designer` output, ADRs, prior discussion, the actual codebase - rather than
   inventing justification to fill a section. If the technical approach itself isn't decided yet, that's
   `architecture-designer`'s job first; this skill argues for a decision, it doesn't make one.
3. **Structure the document** using the Standard Structure below, adapted to what the reader needs -
   drop a section only when it's genuinely not applicable, not because it's inconvenient to fill in.
4. **Draft** applying the Mandatory Writing Style below first, then the supporting Persuasive & Precise
   principles - style is not a polish pass done at the end, a padded or vague first draft still has to
   be rewritten, so write tight and concrete from the first sentence.
5. **Self-review before handing it back.** Run the Conciseness & Evidence Check *and* check for the
   three structural failure modes that make proposals fail even when the underlying idea is sound: an
   Alternatives section that's a strawman, a Risks section that's empty or all upside, and an ask that's
   buried instead of stated up front.
6. **Match the output language to the request.** Write in Vietnamese when the user asked in Vietnamese
   or the target reader is Vietnamese-speaking (see `references/vietnamese-writing.md` for terminology
   and tone); write in English otherwise. Don't default to English just because this skill file is in
   English.

## Standard Structure (Technical Proposal / Đề xuất kỹ thuật)

| Section | Tiêu đề tiếng Việt | Purpose |
|---|---|---|
| Context & Problem | Bối cảnh & Vấn đề | Why this document exists now - what's broken, costly, blocking, or about to become one of those. When there's more than one distinct problem, list them separately with a short ID (P1, P2, ...) instead of blending them into one paragraph - the ID is what Proposed Solution below references back to. |
| Goals & Non-Goals | Mục tiêu & Ngoài phạm vi | What success looks like, and explicitly what this proposal does *not* try to solve - this is what stops scope-creep arguments later. |
| Proposed Solution | Giải pháp đề xuất | The actual approach, at the depth the target reader needs - not full implementation detail (push that to an appendix or linked design doc). When Context listed multiple problems, state which problem ID(s) each solution component resolves (inline, or via the mapping table - see Mandatory Writing Style below); never leave the reader to guess which fix addresses which pain point. |
| Alternatives Considered | Phương án thay thế đã xem xét | Real alternatives with real tradeoffs, including the strongest competing option, not a strawman. This section is what makes a proposal read as *considered* rather than merely *asserted*. |
| Risks & Mitigations | Rủi ro & Biện pháp giảm thiểu | Honest costs and failure modes, each with what would be done about it. A proposal with no risks section reads as naive to any experienced reviewer - it's evidence of thinking it through, not a weakness to hide. |
| Implementation Plan | Kế hoạch triển khai | Phases/milestones, in the order they'd actually happen, with what unblocks what. |
| Timeline & Resources | Timeline & Nguồn lực | Effort estimate, headcount/roles needed, external dependencies - the concrete "what it costs to say yes." |
| Success Metrics *(when measurable)* | Đo lường thành công | How the reader will later know whether this worked - skip only when the change is genuinely not measurable. |
| Open Questions *(when any remain)* | Câu hỏi mở | Unresolved points named explicitly, rather than smoothed over - this invites the reviewer in instead of asking for blind trust. |

## Mandatory Writing Style (User's House Style)

This is not a style preference to weigh against other considerations - it is the standard every
proposal produced by this skill is held to, on top of whatever structure is used. Four rules, in the
user's own words, drive everything below:

1. **Súc tích, ngắn gọn (concise).** Every sentence earns its place. If a sentence can be deleted
   without the reader losing information they need to decide, delete it. This is the opposite of
   "write more to look thorough" - length is not evidence of rigor, and a bloated section is a sign the
   thinking isn't finished, not that it's complete.
2. **Đi thẳng vào vấn đề (get to the point).** Open each section - and the document as a whole - on the
   substance itself, not a lead-in ("Trong bối cảnh phát triển hiện nay...", "As part of our ongoing
   effort to..."). The first sentence of the Context section states the problem; the first sentence of
   the Solution section states the solution.
3. **Chứng minh (prove it).** Every claim about the problem's severity, the solution's expected impact,
   or a tradeoff's cost needs something backing it - a number, a benchmark, a log excerpt, a code
   reference, an incident, a citation. A claim with no evidence attached reads as an opinion, and
   opinions don't get approved.
4. **Giải pháp cụ thể (concrete solutions).** State exactly what would be done - which component
   changes, what the new config/API/schema looks like, what command or migration runs - not the
   direction of travel ("cải thiện hiệu năng hệ thống") without the mechanism. A reader approving a
   vague solution is approving a promise, not a plan.
5. **Ánh xạ vấn đề – giải pháp rõ ràng khi có nhiều vấn đề (explicit problem-to-solution mapping).**
   The moment Context lists more than one problem, the reader needs to know which part of the solution
   resolves which problem - without this, a multi-part solution reads as a bundle of work with no
   visible justification for each piece. Reference the problem ID inline in each solution component
   ("Giải pháp A giải quyết P1, P3") or, once there are more than two or three problems, add a short
   mapping table right after Proposed Solution:

   | Vấn đề | Giải pháp tương ứng |
   |---|---|
   | P1 - [tên ngắn vấn đề] | [tên ngắn giải pháp/thành phần] |
   | P2 - [tên ngắn vấn đề] | [tên ngắn giải pháp/thành phần] |

   If a listed problem has no solution component pointing back at it, that's a gap - either the
   solution is incomplete or the problem shouldn't be in this proposal; don't leave it unaddressed
   silently. Likewise if a solution component maps to no problem, question whether it belongs in this
   proposal at all (see Non-Goals) rather than leaving it unexplained.

### Using code blocks, quote blocks, images, and diagrams

Rich content is allowed and encouraged where it gets the point across faster or more accurately than
prose - but each one has to earn its place; the user explicitly wants these used **without lạm dụng
(overuse)**. Before adding one, ask: does this convey something a sentence or two couldn't, at least as
fast? If not, cut it and say it in prose instead.

| Element | Use it for | Don't use it for |
|---|---|---|
| Code block | An exact command, config, API contract, schema, or error message the reader needs to see verbatim to trust or reproduce it | Describing logic that a short bullet list already conveys just as fast |
| Quote block | An exact citation - a stakeholder requirement, a log line, a spec excerpt - where the exact wording is the evidence | General emphasis on a sentence you wrote yourself; that's what headings/bold are for |
| Diagram | A relationship that's genuinely hard to state in a sentence - data flow, sequence, before/after architecture | A structure a numbered list or table already shows equally clearly |
| Image/screenshot | Visual evidence that *is* the proof - a monitoring graph, a UI state, a trace | Decoration, or restating a number already given in the text |

A proposal with zero rich content is fine if prose and tables carry the argument; a proposal with one
well-chosen diagram is better than one with five decorative ones. When in doubt, leave it out and see
if the document still reads clearly - it usually does.

### Conciseness & Evidence Check (part of self-review)

Before handing the document back, re-read it specifically for:

- Any sentence or section that could be cut with no loss of information the reader needs - cut it.
- Any claim (problem severity, expected benefit, cost of a tradeoff) with no evidence attached -
  attach evidence or mark it explicitly as an estimate/assumption.
- Any solution described by its direction rather than its mechanism - replace with the concrete
  change.
- Any code block, quote block, image, or diagram that just repeats what an adjacent sentence already
  said - remove it or remove the sentence.
- Any opening sentence (of the document or a section) that's a lead-in rather than the point itself -
  cut straight to the substance.
- If Context lists more than one problem: every problem has a solution component pointing back at it,
  and every solution component's target problem is stated, not implied.

## Supporting Persuasive & Precise Principles

- **Lead with the reader's stake, not the mechanism.** Open with why this matters to the approver
  before explaining how it works - a reader who doesn't yet know why they should care will skim past
  the mechanism that's supposed to convince them.
- **Quantify instead of asserting.** Replace "nhanh hơn", "tốt hơn", "đáng kể" (or "faster", "better",
  "significant") with a number, or explicitly mark it as an estimate when no number exists yet -
  unquantified claims are the fastest way to lose a technical reader's trust.
- **State assumptions instead of hiding them.** Every proposal rests on assumptions (traffic stays
  roughly current, team X ships their part on time); naming them lets the reader challenge the right
  thing instead of the whole proposal.
- **Every claim should be falsifiable.** If a reviewer can't imagine what evidence would prove a claim
  wrong, it's not a claim yet - tighten it or cut it.
- **Steelman the alternatives, don't strawman them.** Give the strongest competing option its real
  argument before explaining why the proposed solution wins anyway; a reviewer who spots a strawman
  stops trusting the rest of the document.
- **Keep the ask visible.** State plainly, early, what decision or resource the reader is being asked
  to approve - don't make them infer it from context.
- **Prefer headings, tables, and short paragraphs over dense prose**, especially for a leadership
  reader skimming under time pressure; active voice over passive.
- **(Vietnamese specific)** Prefer direct, concrete phrasing over the softened/indirect register common
  in Vietnamese business writing ("có thể xem xét việc..." → say what you actually recommend); a
  technical proposal earns trust by being decisive, not by hedging every sentence. See
  `references/vietnamese-writing.md` for terminology and common pitfalls translating English tech terms.
- **(Vietnamese specific, user rule)** Keep everyday engineering jargon in English rather than
  translating it - issue, bug, flow, and similar terms the target reader already thinks in English
  stay as-is; forcing a Vietnamese equivalent reads as unfamiliar, not more proper. Full list and
  reasoning in `references/vietnamese-writing.md`.

## Reference Guide

| Topic | Reference | Load When |
|---|---|---|
| Vietnamese technical writing conventions | `references/vietnamese-writing.md` | Drafting or reviewing the document in Vietnamese - terminology choices, tone, common mistranslations |
| Full copy-paste template | `references/proposal-template.md` | Need the complete structure with placeholder prompts, in both Vietnamese and English |

## Constraints

### MUST DO

- Clarify the reader/approver and the actual decision at stake before drafting
- Ground technical rationale in real design artifacts, not invented justification
- Keep every section as short as it can be while still fully supporting the decision - run the
  Conciseness & Evidence Check before delivering
- Open the document, and each section, on the substance itself, not a lead-in
- Back every claim about problem severity, expected impact, or tradeoff cost with concrete evidence -
  a number, benchmark, log, code reference, or citation - or flag it explicitly as an estimate
- Make the proposed solution concrete and actionable - the exact change, config, command, or code, not
  a direction of travel
- When more than one problem is listed, state explicitly which solution component resolves which
  problem ID - inline reference or a mapping table, never left for the reader to infer
- Include a genuine Alternatives section with real tradeoffs
- Include a Risks & Mitigations section
- Match the output language to the user's request (Vietnamese when asked in Vietnamese)
- In Vietnamese output, keep everyday engineering jargon (issue, bug, flow, and similar terms the
  reader already uses in English) untranslated - see `references/vietnamese-writing.md`
- State the ask (the decision being requested) explicitly and early
- Use code blocks, quote blocks, images, and diagrams only where they convey something faster or more
  accurately than a sentence would

### MUST NOT DO

- Invent technical details or rationale not grounded in the actual design - flag as an open question
  instead of guessing
- Pad a section to look complete - length is not evidence of thoroughness
- Write an Alternatives section that's a strawman built just to make the proposed solution look best
- Omit risks or downsides to make the proposal look more attractive
- Bury the actual decision the reader needs to make inside dense prose
- State a solution's direction without its concrete mechanism ("cải thiện hiệu năng" with no how)
- List multiple problems without mapping each one to the solution component that resolves it
- Translate everyday engineering jargon (issue → "vấn đề", bug → "lỗi", flow → "luồng", etc.) when the
  reader already thinks in the English term
- Add a code block, quote block, image, or diagram that just repeats what an adjacent sentence says
- Default to English when the user's request or target audience is Vietnamese

## Boundaries

- This skill writes and structures the proposal; it does not make the underlying technical decision -
  that's `architecture-designer`'s job. When the approach itself isn't settled yet, use
  `architecture-designer` first, then bring the result here to be turned into a proposal.
- Overlaps with `code-documenter`, but the difference is purpose: `code-documenter` documents the
  behavior of a system that already exists, for other developers; this skill argues for a not-yet-made
  decision, to an approver.
- Overlaps with `api-contract-skill` when the proposal is specifically about an API's shape - for a
  full request/response contract design, use `api-contract-skill`; this skill covers the surrounding
  proposal document (why, alternatives, risks, rollout) that contract may need to live inside.

## Knowledge Reference

Technical proposal writing, RFC format, design docs awaiting approval, decision documents, đề xuất kỹ
thuật, đề xuất giải pháp, đề xuất dự án, stakeholder communication, persuasive technical writing,
risk/alternatives framing, Vietnamese business and technical writing conventions.
