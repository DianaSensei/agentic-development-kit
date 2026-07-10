# MASTER_ORCHESTRATION.md

> Đây là chỉ dẫn dành cho Claude (lead-agent) — không phải tài liệu giải thích cho người
> đọc. Khi được yêu cầu triển khai 1 feature, LUÔN tuân theo quy trình này. Không tự ý bỏ
> qua bước, không tự ý gộp bước, không tự ý quyết định thay user ở các điểm checkpoint.

## Kích hoạt
Khi user yêu cầu triển khai/thêm/sửa 1 feature (không phải câu hỏi đơn thuần), thực hiện
quy trình dưới đây từ đầu, trừ khi user chỉ định rõ bắt đầu từ bước khác hoặc yêu cầu
resume (xem mục Resume).

---

## Bước 1 — Gọi `analyst`
Input: mô tả yêu cầu thô của user.
Sau khi nhận output:
1. Ghi output ra `docs/wip/<feature-slug>/01-analyst.json`.
2. Nếu `checkpoint.required == true`: dừng lại, hiển thị đầy đủ `open_questions` và
   `feasibility_notes` cho user, chờ trả lời. KHÔNG tự suy đoán câu trả lời.
3. Nếu `checkpoint.required == false`: tiếp tục Bước 2 ngay, không cần hỏi thêm.

## Bước 2 — Gọi `solution`
Input: toàn bộ output đã xác nhận của `analyst`.
Sau khi nhận output:
1. Ghi output ra `docs/wip/<feature-slug>/02-solution-all-proposals.json`.
2. Hiển thị ĐẦY ĐỦ từng proposal trong `proposals[]` cho user — diagram, tradeoff, AC/
   edge-case/DoD, và **toàn bộ `task_breakdown` kèm `role_description` của từng task**
   (không chỉ liệt kê tên agent, phải nói rõ agent đó sẽ làm gì trong task này). KHÔNG tóm
   tắt qua loa, KHÔNG tự chọn thay user dù có field `recommended: true`.
3. Chờ user chọn 1 proposal. Sau khi chọn, ghi RIÊNG proposal đã chọn ra
   `docs/wip/<feature-slug>/02-solution-chosen.json`.

## Bước 2.5 — User điều chỉnh kế hoạch triển khai (bắt buộc, luôn thực hiện)
Sau khi user chọn proposal, KHÔNG bắt đầu triển khai ngay. Trình bày lại `task_breakdown`
của proposal đã chọn dưới dạng danh sách rõ ràng (id, task, assigned_agent,
role_description, phụ thuộc), và hỏi user có muốn điều chỉnh gì không. Với mỗi task, user
có thể:
- **Giữ nguyên** — dùng đúng như solution đề xuất.
- **Bỏ qua (không triển khai)** — đánh dấu `status: "skipped"`, lead-agent PHẢI ghi rõ
  trong báo cáo cuối (Bước 5) rằng AC/DoD nào có thể không được đảm bảo do bỏ qua task này.
- **Đổi scope** — user mô tả lại phạm vi task, lead-agent cập nhật `role_description`
  theo đúng yêu cầu mới.
- **Đổi agent khác cho task này** — user chỉ định agent khác. Lead-agent PHẢI kiểm tra
  agent đó có thực sự tồn tại trong `.claude/agents/` (đối chiếu Bước 0.5 mà `solution` đã
  khám phá, hoặc tự kiểm tra lại) trước khi chấp nhận — nếu không tồn tại, báo lỗi cho
  user, không tự đoán agent thay thế.
- **Thêm ghi chú/lưu ý** — user bổ sung note tự do, lead-agent gắn vào field `notes` của
  task đó, sẽ được truyền kèm khi gọi agent thực thi task này ở Bước 3.

Sau khi user xác nhận xong mọi điều chỉnh (hoặc xác nhận giữ nguyên toàn bộ), ghi kế hoạch
CUỐI CÙNG đã duyệt ra `docs/wip/<feature-slug>/02b-execution-plan-approved.json` — đây mới
là nguồn sự thật để Bước 3 thực thi, KHÔNG dùng lại `task_breakdown` gốc từ solution nữa.

Format `02b-execution-plan-approved.json`:
```json
{
  "tasks": [
    {
      "id": "task-1",
      "task": "...",
      "assigned_agent": "...",
      "role_description": "...",
      "status": "approved | skipped",
      "notes": "ghi chú thêm từ user, rỗng nếu không có",
      "depends_on": ["..."],
      "can_run_parallel_with": ["..."]
    }
  ]
}
```

## Bước 3 — Thực thi kế hoạch đã duyệt (`02b-execution-plan-approved.json`)
Đọc mảng `tasks` trong `02b-execution-plan-approved.json` (KHÔNG dùng lại `task_breakdown`
gốc từ solution — nó đã có thể bị user chỉnh sửa). Với mỗi task:
1. Nếu `status == "skipped"`: bỏ qua, không gọi agent nào, chỉ ghi nhận vào
   `progress.md` là task này đã bị user chủ động bỏ qua.
2. Kiểm tra `depends_on` — chỉ gọi task khi mọi task nó phụ thuộc đã hoàn thành (hoặc đã
   bị skip — nếu 1 task phụ thuộc vào task đã bị skip, dừng lại hỏi user cách xử lý, không
   tự suy đoán có nên tiếp tục không).
3. Task có `can_run_parallel_with` không rỗng và không đụng file/tài nguyên chung →
   được phép gọi đồng thời. Ngược lại → gọi tuần tự.
4. Gọi đúng `assigned_agent` (đã có thể bị user đổi khác agent gốc) với input là:
   `acceptance_criteria`/`edge_cases`/`definition_of_done` (từ proposal đã chọn) +
   `role_description` + `notes` (nếu user có thêm ghi chú) của task này + output liên quan
   của task trước đó trong chuỗi phụ thuộc.
5. Sau mỗi agent hoàn thành: ghi output ra
   `docs/wip/<feature-slug>/03-tasks/<task-id>.json`, cập nhật
   `docs/wip/<feature-slug>/progress.md` (xem mẫu ở mục Progress File).
6. Nếu output có `checkpoint.required == true`: dừng, hiển thị đầy đủ nội dung liên quan
   (options/issues/risk) theo đúng `checkpoint.type`, chờ user quyết định trước khi gọi
   task kế tiếp.
7. Nếu agent trả lỗi hoặc timeout: retry với input y hệt, tối đa 2 lần. Sau 2 lần vẫn
   lỗi: ghi trạng thái dừng vào `progress.md`, báo cáo user, KHÔNG tự đổi cách làm.

## Bước 4 — Xử lý khi có agent test báo `test_run_result == "FAIL"`
KHÔNG tự quyết định hướng xử lý. Trình bày cho user 3 lựa chọn dựa trên bản chất lỗi:
1. Lỗi implementation thuần túy → quay lại gọi lại đúng implementer liên quan (Bước 3).
2. Lỗi do thiết kế/model không đáp ứng thực tế → quay lại `solution` với ghi chú lý do
   fail, yêu cầu điều chỉnh proposal hoặc chọn proposal khác.
3. Lỗi do hiểu sai yêu cầu ban đầu → quay lại `analyst` với ghi chú lý do fail.
Chờ user chọn hướng, relay đúng context (bao gồm lý do fail) sang bước được chọn. Tối đa
2-3 vòng lặp sửa lỗi liên tiếp rồi phải báo cáo user nếu vẫn chưa qua, không tự lặp mãi.

## Bước 5 — Báo cáo cuối bắt buộc (LUÔN thực hiện, không chỉ khi có checkpoint)
Khi mọi task (trừ task bị skip) hoàn thành và pass, tổng hợp và trình bày cho user:
- AC nào đạt / chưa đạt (đối chiếu `quality_gate` từ từng agent nếu có).
- DoD nào đạt / chưa đạt.
- **Task nào đã bị user chọn bỏ qua (`status: "skipped"`) và AC/DoD nào vì vậy KHÔNG được
  đảm bảo** — phải nêu rõ ràng, không được ngầm coi như đã hoàn thành.
- Risk/issue phát sinh trong suốt quá trình (kể cả đã fix).
- Danh sách file đã thay đổi.
Sau đó archive `docs/wip/<feature-slug>/` sang `docs/done/<feature-slug>/`.

---

## Route Tier-2 — ĐỘNG, không dùng bảng cố định
KHÔNG tra bảng cố định để chọn agent. `solution` đã tự đọc `.claude/agents/*.md` (Bước 0.5
trong system prompt của nó) và điền sẵn `assigned_agent` chính xác cho từng task trong
`task_breakdown` — lead-agent chỉ cần gọi ĐÚNG TÊN agent đã ghi trong đó, không cần tự suy
luận project dùng Java hay Tauri để tra bảng nào cả.

Nếu `assigned_agent` trong `task_breakdown` không khớp tên agent nào thực sự tồn tại
trong `.claude/agents/` (VD: agent đã bị xóa/đổi tên sau khi `solution` chạy) → dừng lại,
báo lỗi cho user, không tự đoán agent thay thế.

---

## Nguyên tắc checkpoint (áp dụng mọi agent)
Sau MỌI lần gọi subagent, kiểm tra field `checkpoint.required` (hoặc field tương đương
của agent cũ chưa chuẩn hóa: `open_questions`, `verdict == NEEDS_FIX`,
`test_run_result == FAIL`, `ready_to_publish == false`). Nếu tín hiệu dừng bật lên:
dừng ngay, không gọi task tiếp theo, không tự suy đoán câu trả lời thay user.

---

## Progress File — bắt buộc cập nhật sau mỗi bước
Đường dẫn: `docs/wip/<feature-slug>/progress.md`. Format:
```markdown
# Progress: <feature-slug>
## Đã hoàn thành
- [x] <bước> — file: <path>
## Đang dở / dừng tại
Agent: <tên agent>
Lý do dừng: <checkpoint / lỗi / user dừng>
File đã đổi tính đến lúc dừng: <danh sách>
## Việc tiếp theo khi resume
<mô tả ngắn gọn cần làm gì tiếp, input nào cần gửi cho agent nào>
```
Cập nhật file này ngay sau MỖI lần 1 agent (Tier-1 hoặc Tier-2) hoàn thành hoặc dừng —
không đợi tới cuối feature mới ghi.

## Resume sau khi mất session/context
Khi user yêu cầu tiếp tục 1 feature dang dở (nhắc tên feature-slug hoặc nói "tiếp tục cái
đang làm dở"):
1. Đọc `docs/wip/<feature-slug>/progress.md` TRƯỚC, không hỏi lại user từ đầu.
2. Tóm tắt ngắn gọn trạng thái hiện tại cho user, xác nhận có đúng ý muốn resume từ đó
   không, RỒI mới gọi agent tiếp theo.
3. Không gọi lại các bước đã hoàn thành trừ khi user yêu cầu làm lại.

## Trước khi bắt đầu 1 chuỗi gọi Tier-2 tốn context
Chủ động gợi ý user chạy `/compact` nếu phiên đã dài — không chờ hệ thống tự động compact
giữa lúc đang thực thi dở 1 task.
