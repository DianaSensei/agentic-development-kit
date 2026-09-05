---
name: technical-proposal-writer
description: Writes and structures technical proposal documents (RFCs, đề xuất kỹ thuật, đề xuất giải pháp, đề xuất dự án) that argue for a technical decision to stakeholders or approvers - problem/context, goals, proposed solution, alternatives considered, risks, implementation plan, timeline and resources. Use whenever the user asks to write, draft, or review a technical proposal, RFC, design doc meant for approval, project proposal, or any "đề xuất" document - in Vietnamese or English - especially when it needs to persuade a reader (lead, leadership, another team) to approve a course of action, not just describe how a system works.
metadata:
  domain: requirements
  triggers: decision document, persuasive writing, kế hoạch triển khai
  role: specialist
  scope: documentation
  output-format: document
  related-skills: architecture-designer, api-contract-skill, code-documenter
---

# Technical Proposal Writer

The document that asks someone to say yes to a technical decision - an RFC, a design doc awaiting
approval, a Vietnamese "đề xuất kỹ thuật" / "đề xuất dự án". The job is argument and structure, not the
engineering choice: the technical direction is assumed settled (or being settled in
`architecture-designer`) and turned into something a specific reader can evaluate and approve.

## Workflow

1. **Name the decision and the approver.** What decision does this document exist to get made, who
   approves it (technical peer? leadership with no deep context? another team?), what's already been
   informally ruled out. A doc written without knowing the reader lands either too technical for
   leadership or too shallow for engineers - the single biggest cause of an unconvincing proposal.
2. **Pull the substance from real artifacts** - `architecture-designer` output, ADRs, prior discussion,
   the codebase. Never invent justification to fill a section. If the approach itself isn't decided,
   that's `architecture-designer`'s job first.
3. **Structure** per the table below. Drop a section only when genuinely not applicable, never because
   it's inconvenient to fill.
4. **Draft under House Style.** Style is not a polish pass - a padded first draft gets rewritten
   anyway, so write tight and concrete from sentence one.
5. **Self-review** against House Style's checks, then the three structural failure modes.
6. **Match the output language to the request** - Vietnamese if the user asked in Vietnamese or the
   reader is Vietnamese-speaking (`references/vietnamese-writing.md`), English otherwise. Don't default
   to English just because this file is in English.

## Standard Structure

| Section | Tiêu đề tiếng Việt | Purpose |
|---|---|---|
| Context & Problem | Bối cảnh & Vấn đề | Why this document exists now. More than one problem → list them separately with short IDs (P1, P2...) rather than blending them into a paragraph; those IDs are what Proposed Solution references back to. |
| Goals & Non-Goals | Mục tiêu & Ngoài phạm vi | What success looks like, and explicitly what this does *not* try to solve - this is what stops scope-creep arguments later. |
| Proposed Solution | Giải pháp đề xuất | The approach at the depth this reader needs; push full implementation detail to an appendix. State which problem ID(s) each component resolves. |
| Alternatives Considered | Phương án thay thế đã xem xét | Real alternatives with real tradeoffs, including the strongest competing option. This is what makes a proposal read as *considered* rather than *asserted*. |
| Risks & Mitigations | Rủi ro & Biện pháp giảm thiểu | Honest costs and failure modes, each with what would be done about it. No risks section reads as naive to any experienced reviewer. |
| Implementation Plan | Kế hoạch triển khai | Phases in the order they'd actually happen, with what unblocks what. |
| Timeline & Resources | Timeline & Nguồn lực | Effort, headcount/roles, external dependencies - the concrete "what it costs to say yes." |
| Success Metrics *(when measurable)* | Đo lường thành công | How the reader will later know whether this worked. |
| Open Questions *(when any remain)* | Câu hỏi mở | Unresolved points named explicitly - this invites the reviewer in instead of asking for blind trust. |

## House Style

The user's own five rules. Not preferences to weigh against other considerations - the standard every
proposal here is held to. Each carries its own self-review check.

1. **Súc tích, ngắn gọn.** If a sentence can be deleted without the reader losing something they need
   to decide, delete it. Length is not evidence of rigor; a bloated section signals unfinished
   thinking, not complete thinking.
   → *Check:* any sentence or section cuttable with no loss - cut it.
2. **Đi thẳng vào vấn đề.** Open the document, and each section, on the substance - not a lead-in
   ("Trong bối cảnh phát triển hiện nay...", "As part of our ongoing effort to..."). Context's first
   sentence states the problem; Solution's first sentence states the solution.
   → *Check:* any opening sentence that's a run-up rather than the point.
3. **Chứng minh.** Every claim about severity, impact, or a tradeoff's cost needs a number, benchmark,
   log excerpt, code reference, incident, or citation behind it. An unbacked claim reads as an opinion,
   and opinions don't get approved.
   → *Check:* any claim with nothing attached - attach evidence, or mark it explicitly as an estimate.
4. **Giải pháp cụ thể.** State exactly what would be done - which component changes, what the new
   config/API/schema looks like, what command or migration runs. Not a direction of travel ("cải thiện
   hiệu năng hệ thống") with no mechanism. Approving a vague solution is approving a promise, not a plan.
   → *Check:* any solution given by direction rather than mechanism.
5. **Ánh xạ vấn đề–giải pháp.** The moment Context lists more than one problem, the reader needs to know
   which part of the solution resolves which - otherwise a multi-part solution reads as a bundle of work
   with no visible justification per piece. Reference the ID inline ("Giải pháp A giải quyết P1, P3"),
   or past two or three problems add a mapping table right after Proposed Solution:

   | Vấn đề | Giải pháp tương ứng |
   |---|---|
   | P1 - [tên ngắn vấn đề] | [tên ngắn giải pháp/thành phần] |

   → *Check:* every problem has a component pointing at it, and every component names its target
   problem. A problem with no component means the solution is incomplete or the problem doesn't belong
   here; a component with no problem means it may not belong in this proposal at all (see Non-Goals).
   Never leave either silently unaddressed.

### Rich content - use, without lạm dụng

Before adding one, ask: does this convey something a sentence or two couldn't, at least as fast? If
not, cut it and say it in prose.

| Element | Use it for | Not for |
|---|---|---|
| Code block | An exact command, config, contract, schema, or error the reader must see verbatim to trust or reproduce it | Logic a short bullet list conveys just as fast |
| Quote block | An exact citation - a stakeholder requirement, log line, spec excerpt - where the wording *is* the evidence | Emphasis on a sentence you wrote yourself; that's what headings/bold are for |
| Diagram | A relationship genuinely hard to state in a sentence - data flow, sequence, before/after architecture | A structure a numbered list or table already shows |
| Image | Visual evidence that *is* the proof - a monitoring graph, a UI state, a trace | Decoration, or restating a number already in the text |

Zero rich content is fine if prose and tables carry the argument. One well-chosen diagram beats five
decorative ones.
→ *Check:* any block that just repeats an adjacent sentence - remove one or the other.

## Three structural failure modes

These sink a proposal even when the underlying idea is sound. Check all three before handing back:

1. **Strawman alternatives** - the strongest competing option gets its real argument before you explain
   why yours wins anyway. A reviewer who spots a strawman stops trusting the whole document.
2. **An empty or all-upside Risks section** - naming real costs is evidence of having thought it
   through, not a weakness to hide.
3. **A buried ask** - state plainly and early what decision or resource is being requested; don't make
   the reader infer it.

## Also

- **Lead with the reader's stake, not the mechanism.** Someone who doesn't yet know why they should
  care will skim past the part meant to convince them.
- **Quantify or flag.** Replace "nhanh hơn"/"đáng kể"/"significant" with a number, or mark it
  explicitly as an estimate when no number exists yet.
- **State assumptions instead of hiding them** (traffic stays flat, team X ships on time) - this lets a
  reviewer challenge the right thing instead of the whole proposal.
- **Every claim falsifiable.** If a reviewer can't imagine what would prove it wrong, it isn't a claim
  yet - tighten it or cut it.
- **Headings, tables, short paragraphs, active voice** - especially for a leadership reader skimming
  under time pressure.
- **Vietnamese: be direct.** Prefer concrete phrasing over the softened business register ("có thể xem
  xét việc..." → say what you actually recommend). A proposal earns trust by being decisive, not by
  hedging every sentence.
- **Vietnamese: keep everyday engineering jargon in English** - issue, bug, flow and similar terms the
  reader already thinks in English. Forcing a Vietnamese equivalent reads as unfamiliar, not more
  proper. Full list and reasoning in `references/vietnamese-writing.md`.

## Reference Guide

| Topic | Reference | Load When |
|---|---|---|
| Vietnamese technical writing conventions | `references/vietnamese-writing.md` | Drafting/reviewing in Vietnamese - terminology, tone, common mistranslations |
| Full copy-paste template | `references/proposal-template.md` | Need the complete structure with placeholder prompts, VI + EN |

## Boundaries

- Writes and structures the proposal; does not make the underlying technical decision - that's
  `architecture-designer`. If the approach isn't settled yet, go there first, then bring the result
  here to be turned into a proposal.
- Overlaps `code-documenter` by purpose: that skill documents how an already-existing system behaves,
  for other developers; this one argues for a not-yet-made decision, to an approver.
- Overlaps `api-contract-skill` when the proposal is specifically about an API's shape - the full
  request/response contract design is that skill's; this one covers the surrounding proposal document
  (why, alternatives, risks, rollout) that contract may need to live inside.
