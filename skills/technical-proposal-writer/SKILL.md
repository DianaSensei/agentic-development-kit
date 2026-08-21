---
name: technical-proposal-writer
description: Writes and structures technical proposal documents (RFCs, đề xuất kỹ thuật, đề xuất giải pháp, đề xuất dự án) that argue for a technical decision to stakeholders or approvers — problem/context, goals, proposed solution, alternatives considered, risks, implementation plan, timeline and resources. Use whenever the user asks to write, draft, or review a technical proposal, RFC, design doc meant for approval, project proposal, or any "đề xuất" document — in Vietnamese or English — especially when it needs to persuade a reader (lead, leadership, another team) to approve a course of action, not just describe how a system works.
metadata:
  domain: requirements
  triggers: technical proposal, RFC, đề xuất kỹ thuật, đề xuất giải pháp, đề xuất dự án, design doc, proposal document, decision document, project proposal, persuasive writing, kế hoạch triển khai
  role: specialist
  scope: documentation
  output-format: document
  related-skills: architecture-designer, api-contract-skill, code-documenter
---

# Technical Proposal Writer

Specialist for the document that asks someone to say yes to a technical decision — an RFC, a design
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
- Reviewing a draft proposal for gaps — missing alternatives, hidden assumptions, no risk section —
  before it goes out.

## Core Workflow

1. **Clarify the decision at stake.** Before drafting, find out: what decision is this document trying
   to get made, who actually approves it (a technical peer? leadership without deep technical context?
   another team?), and how much has already been informally discussed/ruled out. A doc written without
   knowing the reader ends up either too technical for leadership or too shallow to satisfy engineers —
   this is the single biggest cause of a proposal that reads as unconvincing.
2. **Gather the technical substance from real sources.** Pull the rationale from existing design
   artifacts — `architecture-designer` output, ADRs, prior discussion, the actual codebase — rather than
   inventing justification to fill a section. If the technical approach itself isn't decided yet, that's
   `architecture-designer`'s job first; this skill argues for a decision, it doesn't make one.
3. **Structure the document** using the Standard Structure below, adapted to what the reader needs —
   drop a section only when it's genuinely not applicable, not because it's inconvenient to fill in.
4. **Draft** applying the Persuasive & Precise Writing principles below.
5. **Self-review before handing it back.** Check specifically for the three failure modes that make
   proposals fail even when the underlying idea is sound: an Alternatives section that's a strawman, a
   Risks section that's empty or all upside, and an ask that's buried instead of stated up front.
6. **Match the output language to the request.** Write in Vietnamese when the user asked in Vietnamese
   or the target reader is Vietnamese-speaking (see `references/vietnamese-writing.md` for terminology
   and tone); write in English otherwise. Don't default to English just because this skill file is in
   English.

## Standard Structure (Technical Proposal / Đề xuất kỹ thuật)

| Section | Tiêu đề tiếng Việt | Purpose |
|---|---|---|
| Context & Problem | Bối cảnh & Vấn đề | Why this document exists now — what's broken, costly, blocking, or about to become one of those. |
| Goals & Non-Goals | Mục tiêu & Ngoài phạm vi | What success looks like, and explicitly what this proposal does *not* try to solve — this is what stops scope-creep arguments later. |
| Proposed Solution | Giải pháp đề xuất | The actual approach, at the depth the target reader needs — not full implementation detail (push that to an appendix or linked design doc). |
| Alternatives Considered | Phương án thay thế đã xem xét | Real alternatives with real tradeoffs, including the strongest competing option, not a strawman. This section is what makes a proposal read as *considered* rather than merely *asserted*. |
| Risks & Mitigations | Rủi ro & Biện pháp giảm thiểu | Honest costs and failure modes, each with what would be done about it. A proposal with no risks section reads as naive to any experienced reviewer — it's evidence of thinking it through, not a weakness to hide. |
| Implementation Plan | Kế hoạch triển khai | Phases/milestones, in the order they'd actually happen, with what unblocks what. |
| Timeline & Resources | Timeline & Nguồn lực | Effort estimate, headcount/roles needed, external dependencies — the concrete "what it costs to say yes." |
| Success Metrics *(when measurable)* | Đo lường thành công | How the reader will later know whether this worked — skip only when the change is genuinely not measurable. |
| Open Questions *(when any remain)* | Câu hỏi mở | Unresolved points named explicitly, rather than smoothed over — this invites the reviewer in instead of asking for blind trust. |

## Persuasive & Precise Writing Principles

- **Lead with the reader's stake, not the mechanism.** Open with why this matters to the approver
  before explaining how it works — a reader who doesn't yet know why they should care will skim past
  the mechanism that's supposed to convince them.
- **Quantify instead of asserting.** Replace "nhanh hơn", "tốt hơn", "đáng kể" (or "faster", "better",
  "significant") with a number, or explicitly mark it as an estimate when no number exists yet —
  unquantified claims are the fastest way to lose a technical reader's trust.
- **State assumptions instead of hiding them.** Every proposal rests on assumptions (traffic stays
  roughly current, team X ships their part on time); naming them lets the reader challenge the right
  thing instead of the whole proposal.
- **Every claim should be falsifiable.** If a reviewer can't imagine what evidence would prove a claim
  wrong, it's not a claim yet — tighten it or cut it.
- **Steelman the alternatives, don't strawman them.** Give the strongest competing option its real
  argument before explaining why the proposed solution wins anyway; a reviewer who spots a strawman
  stops trusting the rest of the document.
- **Keep the ask visible.** State plainly, early, what decision or resource the reader is being asked
  to approve — don't make them infer it from context.
- **Prefer headings, tables, and short paragraphs over dense prose**, especially for a leadership
  reader skimming under time pressure; active voice over passive.
- **(Vietnamese specific)** Prefer direct, concrete phrasing over the softened/indirect register common
  in Vietnamese business writing ("có thể xem xét việc..." → say what you actually recommend); a
  technical proposal earns trust by being decisive, not by hedging every sentence. See
  `references/vietnamese-writing.md` for terminology and common pitfalls translating English tech terms.

## Reference Guide

| Topic | Reference | Load When |
|---|---|---|
| Vietnamese technical writing conventions | `references/vietnamese-writing.md` | Drafting or reviewing the document in Vietnamese — terminology choices, tone, common mistranslations |
| Full copy-paste template | `references/proposal-template.md` | Need the complete structure with placeholder prompts, in both Vietnamese and English |

## Constraints

### MUST DO

- Clarify the reader/approver and the actual decision at stake before drafting
- Ground technical rationale in real design artifacts, not invented justification
- Include a genuine Alternatives section with real tradeoffs
- Include a Risks & Mitigations section
- Quantify claims where data exists; flag clearly where a number is an estimate
- Match the output language to the user's request (Vietnamese when asked in Vietnamese)
- State the ask (the decision being requested) explicitly and early

### MUST NOT DO

- Invent technical details or rationale not grounded in the actual design — flag as an open question
  instead of guessing
- Write an Alternatives section that's a strawman built just to make the proposed solution look best
- Omit risks or downsides to make the proposal look more attractive
- Bury the actual decision the reader needs to make inside dense prose
- Default to English when the user's request or target audience is Vietnamese

## Boundaries

- This skill writes and structures the proposal; it does not make the underlying technical decision —
  that's `architecture-designer`'s job. When the approach itself isn't settled yet, use
  `architecture-designer` first, then bring the result here to be turned into a proposal.
- Overlaps with `code-documenter`, but the difference is purpose: `code-documenter` documents the
  behavior of a system that already exists, for other developers; this skill argues for a not-yet-made
  decision, to an approver.
- Overlaps with `api-contract-skill` when the proposal is specifically about an API's shape — for a
  full request/response contract design, use `api-contract-skill`; this skill covers the surrounding
  proposal document (why, alternatives, risks, rollout) that contract may need to live inside.

## Knowledge Reference

Technical proposal writing, RFC format, design docs awaiting approval, decision documents, đề xuất kỹ
thuật, đề xuất giải pháp, đề xuất dự án, stakeholder communication, persuasive technical writing,
risk/alternatives framing, Vietnamese business and technical writing conventions.
