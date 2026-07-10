---
name: feature-development
description: Quy trình phát triển 1 tính năng mới hoàn chỉnh — từ phân tích yêu cầu, đề xuất giải pháp, tới implement/test/fix lặp cho tới khi đạt chất lượng, rồi báo cáo và lưu kiến thức. Hoàn toàn abstraction công nghệ — tự quét và dùng các skill kỹ thuật chi tiết khi cần. Dùng cho mọi loại project/stack.
argument-hint: [mô tả yêu cầu tính năng]
---

# Feature Development Workflow

Chạy trong 1 agent duy nhất, tuần tự. Skill này KHÔNG chứa kiến thức công nghệ cụ thể —
mọi chi tiết kỹ thuật (ngôn ngữ, framework, DB, messaging...) đến từ các skill khác được
quét động ở Bước 0.

Yêu cầu đầu vào: `$ARGUMENTS`

## Bước 0 — Quét & cache skill map (bắt buộc, làm 1 lần đầu mỗi feature)
Quét toàn bộ `.claude/skills/*/SKILL.md` (và `~/.claude/skills/` nếu có), đọc `name` +
`description` của từng skill (bỏ qua chính skill này). Xây dựng 1 bảng ánh xạ tạm trong
đầu: "ngữ cảnh nào → skill nào phù hợp" dựa trên `description`. Cache lại bảng này cho
suốt phiên làm feature — KHÔNG quét lại mỗi lần cần dùng skill, chỉ quét lại nếu bạn nghi
ngờ danh sách skill đã thay đổi (VD: user vừa nói đã thêm skill mới).

Mục đích: khi sau này có thêm skill kỹ thuật mới (VD: 1 skill cho ngôn ngữ khác), workflow
này KHÔNG cần sửa gì — tự nhận diện qua `description` mà không cần bảng cứng ghi tên trước.

Đồng thời phát hiện bối cảnh project: đọc `CLAUDE.md`, memory/MCP nếu có, code/logic hiện
có liên quan — nhưng KHÔNG gọi tên công nghệ cụ thể trong phần diễn giải với user ở các
bước sau trừ khi cần thiết để truyền đạt quyết định kỹ thuật.

## Bước 1 — Phân tích yêu cầu (vai trò Business Analyst, abstraction)
Diễn giải lại yêu cầu bằng lời (re-verify), liệt kê giả định + câu hỏi mơ hồ. Dừng hỏi
user nếu có sai lệch — không tự suy đoán ý định.

## Bước 2 — Đề xuất giải pháp (abstraction, tham chiếu skill kỹ thuật khi liệt kê task)
1. Đọc kiến trúc/convention hiện có — đề xuất nhất quán, KHÔNG tạo kiến trúc lạ nếu không
   có lý do rõ ràng.
2. Nếu có nhiều hướng hợp lý, đưa nhiều đề xuất riêng biệt, mỗi đề xuất gồm:
   - Sequence diagram + flow diagram (Mermaid).
   - Tradeoff giữa các hướng.
   - Acceptance Criteria (Given-When-Then) + Edge Case + Definition of Done theo phương án.
   - Danh sách task cần hoàn thành — với mỗi task, ghi chú skill kỹ thuật (từ bảng ánh xạ
     Bước 0) dự kiến sẽ tham khảo lúc thực thi, KHÔNG cần nêu chi tiết công nghệ ở đây.
3. Có thể gợi ý 1 đề xuất kèm lý do, KHÔNG tự chọn thay user.

**CHECKPOINT (bắt buộc)**: trình bày đầy đủ đề xuất, chờ user xác nhận requirement/
solution. KHÔNG sang Bước 3 khi chưa có xác nhận rõ ràng.

## Bước 3 — Implement + Test (loop tới khi đạt chất lượng)

### 3.1 Implement
Làm từng task đã liệt kê. Với mỗi task, tham khảo đúng skill kỹ thuật đã ánh xạ ở Bước 0
(dựa theo bối cảnh phát hiện — ngôn ngữ/framework/DB/UI liên quan) để đảm bảo đúng thực
hành chuyên sâu, KHÔNG tự bịa cách làm nếu skill tương ứng đã tồn tại.

### 3.2 Test
Viết và chạy test đầy đủ theo skill kỹ thuật tương ứng (unit/integration/functional/tùy
loại project). Đối chiếu kết quả với:
- Từng Acceptance Criteria đã chốt ở Bước 2.
- Từng Edge Case đã liệt kê.
- Definition of Done.
- **Ngưỡng chất lượng**: test phải pass, không có lỗi nghiêm trọng còn mở, coverage đủ
  cho các AC quan trọng (không chấp nhận "test cho có" mà bỏ sót AC).

### 3.3 Nếu CHƯA đạt ngưỡng — vào loop fix
Với MỖI issue/lỗi phát hiện (test fail, review tự phát hiện vấn đề):
1. Chẩn đoán nguyên nhân, sửa, chạy lại test liên quan.
2. Tính đây là **lần thử #1** cho issue này.
3. Nếu vẫn fail: thử lại, tăng biến đếm cho issue đó (#2, #3...).
4. **Tối đa 5 lần thử cho MỖI issue riêng biệt.** Nếu tới lần thứ 5 vẫn chưa giải quyết
   được — DỪNG LẠI, KHÔNG thử tiếp, raise vấn đề này cho user: mô tả issue, đã thử gì ở
   mỗi lần, tại sao chưa giải quyết được, đề xuất hướng cần user quyết định (đổi cách
   tiếp cận, chấp nhận giới hạn, hay cần thêm thông tin).
5. Issue MỚI phát sinh (khác issue đang xử lý) được tính là 1 bộ đếm riêng, có 5 lần thử
   riêng — không cộng dồn số lần thử của issue khác vào nhau.
6. Sau khi 1 issue được giải quyết, chạy lại TOÀN BỘ test liên quan (không chỉ test của
   issue đó) để đảm bảo không phá vỡ chỗ khác, rồi quay lại 3.2.

Lặp lại 3.1 → 3.2 → 3.3 cho tới khi đạt đủ ngưỡng chất lượng + AC + DoD, HOẶC có issue
phải raise cho user (thì dừng workflow tại đó, không tự ý coi như xong).

## Bước 4 — Báo cáo kết quả cuối (bắt buộc)
- AC/DoD nào đạt / chưa đạt.
- Risk/issue phát sinh trong suốt quá trình (kể cả đã fix) — bao gồm cả issue đã raise
  cho user nếu có.
- Danh sách file đã thay đổi.
- Số lần lặp fix đã dùng cho từng issue (để user thấy độ khó thực tế).

**CHECKPOINT**: chờ user xác nhận đã review đầy đủ báo cáo trước khi sang Bước 5.

## Bước 5 — Lưu kiến thức & note kinh nghiệm (chỉ sau checkpoint trên)
1. Memory/MCP (nếu có kết nối): ghi quyết định quan trọng, kết quả cuối.
2. File quyết định: `docs/decisions/<feature-slug>.md` — phương án đã chọn, lý do, diagram
   cuối, AC/DoD cuối, risk còn tồn đọng.
3. **Experience log (bắt buộc, tích lũy lâu dài, KHÔNG ghi đè)**: append vào
   `docs/knowledge/experience-log.md` — với mỗi issue đã gặp trong Bước 3.3 (dù đã fix
   hay chưa fix được), ghi theo format:
   ```markdown
   ## [<ngày>] <feature-slug> — <mô tả issue ngắn gọn>
   - Nguyên nhân: ...
   - Số lần thử: X/5
   - Kết quả: Đã fix | Chưa fix (raised cho user)
   - Cách fix (nếu có) / Hướng đã thử mà KHÔNG hiệu quả (để lần sau không lặp lại)
   ```
   Mục đích: lần sau gặp issue tương tự (cùng project hoặc project khác), đọc file này
   trước để tránh thử lại đúng những hướng đã biết là không hiệu quả.
