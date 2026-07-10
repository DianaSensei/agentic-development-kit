---
name: bug-fix
description: Quy trình xử lý báo cáo lỗi hoàn chỉnh — thu thập triệu chứng, cố gắng reproduce, chờ user xác nhận trước khi sửa, implement/fix lặp tới khi đạt chất lượng, rồi báo cáo, lưu kiến thức và tạo postmortem. Hoàn toàn abstraction công nghệ — tự quét và dùng các skill kỹ thuật chi tiết khi cần. Dùng cho mọi loại project/stack.
argument-hint: [mô tả lỗi/triệu chứng]
---

# Bug Fix Workflow

Chạy trong 1 agent duy nhất, tuần tự. Skill này KHÔNG chứa kiến thức công nghệ cụ thể —
chi tiết kỹ thuật đến từ các skill khác được quét động ở Bước 0.

Yêu cầu đầu vào: `$ARGUMENTS`

## Bước 0 — Quét & cache skill map (bắt buộc, làm 1 lần đầu mỗi bug)
Quét toàn bộ `.claude/skills/*/SKILL.md` (và `~/.claude/skills/` nếu có), đọc `name` +
`description` (bỏ qua chính skill này), xây dựng ánh xạ "ngữ cảnh → skill phù hợp", cache
cho suốt phiên xử lý bug này. Không cần sửa file này khi có skill kỹ thuật mới — tự nhận
diện qua `description`.

Đồng thời đọc `CLAUDE.md`, memory/MCP nếu có, code/logic hiện có liên quan tới khu vực
nghi ngờ có bug.

## Bước 1 — Thu thập triệu chứng
Ghi nhận đầy đủ những gì user biết/quan sát được: hành vi mong đợi vs thực tế, điều kiện
xảy ra (khi nào, dữ liệu nào, môi trường nào), tần suất (luôn xảy ra hay ngẫu nhiên), có
thông báo lỗi/log nào không. Nếu thiếu thông tin quan trọng để chẩn đoán, hỏi lại NGAY,
không cố đoán mò trước khi có đủ dữ kiện tối thiểu.

## Bước 2 — Cố gắng chứng minh/reproduce
1. Phối hợp triệu chứng từ user với context/knowledge project (code hiện có, luồng xử lý,
   log nếu có) để dựng lại kịch bản có khả năng gây ra lỗi.
2. Nếu reproduce được: ghi rõ CÁC BƯỚC chính xác để tái hiện lỗi + nguyên nhân gốc (root
   cause) mà bạn xác định được dựa trên bằng chứng cụ thể (không đoán mò).
3. Nếu KHÔNG reproduce được: nói THẲNG là chưa reproduce được, KHÔNG giả vờ đã hiểu rõ
   nguyên nhân. Trình bày các giả thuyết có khả năng (kèm mức độ tin cậy: cao/trung bình/
   thấp) và đề xuất cần thêm thông tin gì từ user (log cụ thể hơn, bước thao tác chi tiết
   hơn) để tăng khả năng reproduce.

## Bước 3 — Báo cáo cho user review/approve (CHECKPOINT bắt buộc)
Trình bày: đã reproduce được hay chưa, root cause (nếu có, kèm độ tin cậy), hướng sửa dự
kiến (kèm skill kỹ thuật dự kiến tham khảo — abstraction, không cần nêu chi tiết công
nghệ), edge case liên quan cần đảm bảo không lặp lại, DoD (thế nào là coi như đã fix xong).

**CHECKPOINT**: chờ user xác nhận/approve hướng sửa trước khi thực thi. KHÔNG tự ý sửa
code khi chưa có xác nhận — kể cả khi bạn rất tự tin về root cause.

## Bước 4 — Implement + Retest (loop tới khi đạt chất lượng)

### 4.1 Implement fix
Sửa đúng root cause đã được duyệt ở Bước 3 (không sửa theo triệu chứng bề mặt). Tham khảo
skill kỹ thuật phù hợp (theo ánh xạ Bước 0) cho phần thực hiện cụ thể.

### 4.2 Retest
Viết test case tái hiện đúng bug này (đảm bảo không tái diễn), chạy lại TOÀN BỘ test liên
quan (không chỉ test mới) để chắc chắn không phá vỡ chỗ khác.

### 4.3 Nếu CHƯA đạt (bug vẫn còn, hoặc phát sinh lỗi mới) — vào loop fix
Với MỖI issue/test-case chưa pass (bug gốc chưa hết, hoặc lỗi mới phát sinh do fix):
1. Chẩn đoán, sửa, retest — tính là lần thử #1 cho issue/test-case đó.
2. Vẫn fail: thử lại, tăng biến đếm (#2, #3...).
3. **Tối đa 5 lần thử cho MỖI issue/test-case riêng biệt.** Tới lần thứ 5 vẫn chưa xong —
   DỪNG LẠI, raise cho user: mô tả issue, đã thử gì mỗi lần, vì sao chưa giải quyết được,
   đề xuất hướng cần user quyết định.
4. Issue/test-case MỚI phát sinh có bộ đếm riêng, không cộng dồn với issue khác.

Lặp lại 4.1 → 4.2 → 4.3 tới khi bug gốc đã fix, test pass đầy đủ, không phát sinh lỗi mới,
HOẶC có issue phải raise cho user (dừng tại đó).

## Bước 5 — Báo cáo kết quả cuối (bắt buộc)
- Bug gốc đã fix chưa, DoD đạt chưa.
- Risk/issue phát sinh trong quá trình (kể cả đã fix, kể cả đã raise).
- Danh sách file đã thay đổi.
- Số lần lặp fix đã dùng cho từng issue/test-case.

**CHECKPOINT**: chờ user xác nhận đã review đầy đủ trước khi sang Bước 6.

## Bước 6 — Lưu kiến thức, note kinh nghiệm & tạo Postmortem (chỉ sau checkpoint trên)
1. Memory/MCP (nếu có kết nối): ghi root cause, cách fix, kết quả cuối.
2. **Experience log (tích lũy, KHÔNG ghi đè)**: append vào
   `docs/knowledge/experience-log.md` theo đúng format như ở feature-development (ngày,
   mô tả issue, nguyên nhân, số lần thử, kết quả, cách fix hoặc hướng KHÔNG hiệu quả).
3. **Postmortem (bắt buộc riêng cho bug-fix)**: tạo `docs/postmortems/<bug-slug>.md` gồm:
   ```markdown
   # Postmortem: <tên bug>
   ## Triệu chứng ban đầu
   ## Root cause
   ## Impact (phạm vi ảnh hưởng, mức độ nghiêm trọng)
   ## Cách phát hiện/reproduce
   ## Cách fix
   ## Test đã bổ sung để tránh tái diễn
   ## Bài học / Đề xuất phòng ngừa (nếu có pattern chung có thể áp dụng nơi khác)
   ```
   Nếu KHÔNG reproduce/fix được (đã raise cho user và dừng ở đó), vẫn tạo postmortem với
   phần "Chưa giải quyết được" ghi rõ giả thuyết đã thử, lý do dừng, đề xuất bước tiếp
   theo — để lần sau (ai đó khác hoặc chính bạn) không phải bắt đầu lại từ đầu.
