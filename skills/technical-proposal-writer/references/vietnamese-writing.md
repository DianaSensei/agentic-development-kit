# Vietnamese Technical Writing Conventions

Guidance for drafting or reviewing a technical proposal in Vietnamese. This isn't a translation
guide — it's about what reads as credible and direct to a Vietnamese technical/business reader,
which is often not a literal translation of the equivalent English phrasing.

## Tone: direct, not softened

Vietnamese business writing has a strong default toward hedged, indirect phrasing — softening a
recommendation so it doesn't sound like an order. In a technical proposal that register works against
you: the reader is trying to figure out what you actually recommend, and hedging reads as either
uncertainty or evasion.

| Avoid (hedged) | Prefer (direct) |
|---|---|
| Có thể xem xét việc chuyển sang kiến trúc microservices | Đề xuất chuyển sang kiến trúc microservices |
| Việc này có thể sẽ giúp cải thiện hiệu năng | Việc này giúp giảm p95 latency từ 800ms xuống ~200ms (dựa trên benchmark ở mục X) |
| Chúng ta nên cân nhắc một số phương án | Có 3 phương án được xem xét: A, B, C — đề xuất chọn phương án B |
| Có lẽ sẽ cần thêm nhân sự | Cần thêm 1 backend engineer trong 6 tuần |

The pattern: replace "could/might/should consider" (có thể / có lẽ / nên xem xét) with a stated
position, then let the Alternatives and Risks sections carry the nuance — that's where hedging
belongs (as named uncertainty), not in the main recommendation.

## Common section headings

| English | Vietnamese | Notes |
|---|---|---|
| Context / Background | Bối cảnh | Not "Giới thiệu" (Introduction) — that reads as generic preamble, not a problem statement |
| Problem Statement | Vấn đề | Keep this separate from Bối cảnh when the problem needs its own framing |
| Goals | Mục tiêu | |
| Non-Goals / Out of Scope | Ngoài phạm vi | Also seen as "Không thuộc phạm vi" |
| Proposed Solution | Giải pháp đề xuất | Not "Đề xuất" alone — that's the document's title, reusing it as a section header is ambiguous |
| Alternatives Considered | Phương án thay thế (đã xem xét) | |
| Risks | Rủi ro | |
| Mitigations | Biện pháp giảm thiểu | Pair with each risk, not as a separate disconnected list |
| Implementation Plan | Kế hoạch triển khai | |
| Timeline | Lộ trình / Thời gian thực hiện | "Timeline" itself is commonly left in English in practice; both are fine, pick one and stay consistent |
| Resources | Nguồn lực | Covers headcount, budget, external dependencies |
| Success Metrics | Tiêu chí đo lường thành công | |
| Open Questions | Câu hỏi mở / Vấn đề chưa chốt | |

## Terminology: keep everyday engineering jargon in English (user rule)

This is an explicit rule, not a stylistic option: terms that Vietnamese-speaking engineering teams
already use in English day-to-day stay in English. Forcing a Vietnamese translation of a term the
reader already thinks in English doesn't read as more "chuẩn" (proper) — it reads as unfamiliar and
slows the reader down, which cuts directly against the súc tích/đi thẳng vào vấn đề house style.

**Always keep in English — do not translate:** issue, bug, flow (as in user flow / data flow /
workflow), API, database, cache, latency, throughput, deployment, rollback, pipeline, microservices,
load balancer, endpoint, framework, production, staging, queue, worker, thread, request, response,
commit, merge, release, patch, hotfix — and most proper nouns (product/service names, protocol names).
This list is illustrative, not exhaustive: the test is "would the target reader (the engineering team,
a technical lead) already say this word in English in a meeting?" — if yes, keep it in English even if
it's not on this list. When genuinely unsure whether a term counts as this kind of everyday jargon,
keep it in English rather than guess a Vietnamese equivalent that might read as unfamiliar.

**Translate:** the connective and argumentative language around those terms — "vì vậy" (therefore),
"do đó" (as a result), "tuy nhiên" (however), "ngược lại" (in contrast), "rủi ro chính là" (the main
risk is), "đánh đổi" (tradeoff), "chi phí" (cost) — this is where Vietnamese should carry the
reasoning, with the kept-English terms as the technical nouns embedded in it. For example: "Bug này
gây ra latency tăng đột biến trong flow thanh toán" — not "Lỗi này gây ra độ trễ tăng đột biến trong
luồng thanh toán."

**Section headings are a separate case.** The Standard Structure's Vietnamese headings ("Bối cảnh &
Vấn đề" for Context & Problem, etc.) are structural labels, not inline jargon — keep using the
Vietnamese headings from the Standard Structure table even though "issue" itself stays in English
inline. "Vấn đề" as a section name refers to the problem the whole document addresses; "issue" inline
refers to a specific tracked issue/ticket/observed instance (e.g. "issue này đã được ghi nhận trong
JIRA-1234") — they aren't interchangeable, and conflating them is one more reason not to translate
"issue" away.

**Common mistranslation traps:**
- "Solution" → don't render as "Giải pháp" when you mean a software product/tool; "giải pháp" specifically
  means the *approach/plan*, which matches this skill's usage.
- "Scalable" has no single clean Vietnamese word — prefer describing the concrete property
  ("có thể mở rộng để xử lý X yêu cầu/giây") over forcing a one-word translation.
- "Risk" (rủi ro) vs. "issue" (kept as "issue", not "vấn đề") — a risk is something that *might* happen
  with a probability; an issue is something already observed/true. Keep them in the sections they
  belong to, and keep "issue" in English per the rule above.

## Numbers and dates

Use the reader's expected format: dot or comma as thousands separator matches local convention
(e.g. "1.000.000" not "1,000,000" when writing for a Vietnamese audience, unless the org's internal
convention is otherwise — check existing docs). Dates as dd/mm/yyyy or "ngày X tháng Y năm Z", not
mm/dd/yyyy, to avoid ambiguity.

## Length and density

Vietnamese technical readers in a corporate context are often reading on a phone or skimming between
meetings — this argues for the same short-paragraph, table-over-prose bias called out in the main
skill file, applied slightly more aggressively than an equivalent English-language doc might use.
