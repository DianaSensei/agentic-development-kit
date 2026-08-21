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

## Terminology: when to keep English terms

Vietnamese technical writing commonly keeps certain English terms untranslated rather than forcing an
awkward Vietnamese equivalent — translating them can make a document read as less credible to a
technical audience, not more.

**Keep in English:** API, database, cache, latency, throughput, deployment, rollback, pipeline,
microservices, load balancer, endpoint, framework, production, staging — and most proper nouns
(product/service names, protocol names).

**Translate:** the connective and argumentative language — "vì vậy" (therefore), "do đó" (as a
result), "tuy nhiên" (however), "ngược lại" (in contrast), "rủi ro chính là" (the main risk is),
"đánh đổi" (tradeoff), "chi phí" (cost) — this is where Vietnamese should carry the reasoning, with
English terms as the technical nouns embedded in it.

**Common mistranslation traps:**
- "Solution" → don't render as "Giải pháp" when you mean a software product/tool; "giải pháp" specifically
  means the *approach/plan*, which matches this skill's usage.
- "Scalable" has no single clean Vietnamese word — prefer describing the concrete property
  ("có thể mở rộng để xử lý X yêu cầu/giây") over forcing a one-word translation.
- "Risk" (rủi ro) vs. "issue" (vấn đề) — proposals often blur these; a risk is something that *might*
  happen with a probability, an issue is something already true. Keep them in the sections they belong to.

## Numbers and dates

Use the reader's expected format: dot or comma as thousands separator matches local convention
(e.g. "1.000.000" not "1,000,000" when writing for a Vietnamese audience, unless the org's internal
convention is otherwise — check existing docs). Dates as dd/mm/yyyy or "ngày X tháng Y năm Z", not
mm/dd/yyyy, to avoid ambiguity.

## Length and density

Vietnamese technical readers in a corporate context are often reading on a phone or skimming between
meetings — this argues for the same short-paragraph, table-over-prose bias called out in the main
skill file, applied slightly more aggressively than an equivalent English-language doc might use.
