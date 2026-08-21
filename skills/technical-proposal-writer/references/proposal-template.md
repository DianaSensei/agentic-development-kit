# Proposal Template

Copy-paste starting point. Each section has a Vietnamese and English heading and a one-line prompt
for what must actually be in it — the prompt is not filler text to leave in the final document, replace
it. Drop a section only when it's genuinely not applicable to this proposal, not because it's hard to
fill in (a dropped Risks or Alternatives section is usually a sign the proposal needs more thinking,
not less writing).

---

## Vietnamese

```markdown
# [Tên đề xuất]

**Người đề xuất:** [tên] · **Ngày:** [ngày] · **Trạng thái:** [Bản nháp / Chờ duyệt / Đã duyệt]
**Người cần phê duyệt:** [tên/vai trò]

## Tóm tắt
[2–3 câu: vấn đề là gì, giải pháp đề xuất là gì, và quyết định cụ thể đang xin phê duyệt là gì —
người đọc bận rộn nên đọc xong phần này là hiểu được việc chính.]

## Bối cảnh & Vấn đề
[Điều gì đang xảy ra khiến tài liệu này cần tồn tại ngay bây giờ — số liệu/sự cố/chi phí cụ thể nếu có.
Nếu có từ 2 vấn đề trở lên, liệt kê riêng từng vấn đề kèm mã ngắn để tham chiếu lại ở phần Giải pháp:]
- **P1 —** [tên ngắn vấn đề 1]: [mô tả + bằng chứng]
- **P2 —** [tên ngắn vấn đề 2]: [mô tả + bằng chứng]

## Mục tiêu
- [Mục tiêu cụ thể, đo lường được nếu có thể]

## Ngoài phạm vi
- [Những gì đề xuất này KHÔNG giải quyết, để tránh hiểu lầm về scope]

## Giải pháp đề xuất
[Mô tả giải pháp ở mức độ chi tiết phù hợp với người đọc — đẩy chi tiết triển khai sâu ra phụ lục
hoặc design doc liên kết nếu người đọc là lãnh đạo không chuyên sâu kỹ thuật. Nếu Bối cảnh có nhiều
vấn đề, mỗi thành phần giải pháp phải nêu rõ nó giải quyết vấn đề nào — chỉ cần mapping table dưới đây
khi có từ 3 vấn đề/giải pháp trở lên, còn ít hơn thì ghi trực tiếp trong câu ("Giải pháp A giải quyết P1").]

*(Chỉ thêm khi có nhiều vấn đề/giải pháp — xóa nếu không cần)*
| Vấn đề | Giải pháp tương ứng |
|---|---|
| P1 — [tên ngắn] | [tên ngắn thành phần giải pháp] |
| P2 — [tên ngắn] | [tên ngắn thành phần giải pháp] |

## Phương án thay thế đã xem xét
| Phương án | Ưu điểm | Nhược điểm | Vì sao không chọn |
|---|---|---|---|
| [A] | | | |
| [B] | | | |

## Rủi ro & Biện pháp giảm thiểu
| Rủi ro | Khả năng xảy ra | Tác động | Biện pháp giảm thiểu |
|---|---|---|---|
| | | | |

## Kế hoạch triển khai
1. [Giai đoạn 1 — điều kiện bắt đầu/kết thúc]
2. [Giai đoạn 2]

## Lộ trình & Nguồn lực
- **Thời gian dự kiến:** [X tuần/tháng]
- **Nhân sự cần:** [vai trò, số lượng]
- **Phụ thuộc bên ngoài:** [đội khác, hệ thống khác, phê duyệt khác]

## Tiêu chí đo lường thành công
- [Chỉ số cụ thể + ngưỡng đạt được]

## Câu hỏi mở
- [Điểm chưa chốt, cần input từ người đọc]
```

---

## English

```markdown
# [Proposal Title]

**Author:** [name] · **Date:** [date] · **Status:** [Draft / In Review / Approved]
**Approver(s):** [name/role]

## Summary
[2–3 sentences: what the problem is, what's being proposed, and the specific decision being asked
for — a busy reader should get the whole ask from this section alone.]

## Context & Problem
[What's happening that makes this document necessary now — concrete numbers/incidents/cost if any.
If there are 2+ distinct problems, list them separately with a short ID to reference back to in
Proposed Solution:]
- **P1 —** [short problem name]: [description + evidence]
- **P2 —** [short problem name]: [description + evidence]

## Goals
- [Specific, measurable where possible]

## Non-Goals
- [What this proposal explicitly does not solve, to prevent scope confusion]

## Proposed Solution
[Describe at the depth the reader needs — push deep implementation detail to an appendix or linked
design doc if the reader is non-technical leadership. If Context listed multiple problems, each
solution component must state which problem it resolves — inline ("Component A resolves P1") is enough
for 1–2 problems; use the mapping table below once there are 3+.]

*(Only include when there are multiple problems/solution components — delete otherwise)*
| Problem | Corresponding Solution |
|---|---|
| P1 — [short name] | [short solution component name] |
| P2 — [short name] | [short solution component name] |

## Alternatives Considered
| Option | Pros | Cons | Why not chosen |
|---|---|---|---|
| [A] | | | |
| [B] | | | |

## Risks & Mitigations
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| | | | |

## Implementation Plan
1. [Phase 1 — entry/exit condition]
2. [Phase 2]

## Timeline & Resources
- **Estimated timeline:** [X weeks/months]
- **Staffing needed:** [role, count]
- **External dependencies:** [other team, other system, other approval]

## Success Metrics
- [Specific metric + target threshold]

## Open Questions
- [Unresolved point, needs reader input]
```
