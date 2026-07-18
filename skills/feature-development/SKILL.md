---
name: feature-development
description: Quy trình phát triển 1 tính năng mới hoàn chỉnh — từ phân tích yêu cầu, đề xuất giải pháp, tới implement/test/fix lặp cho tới khi đạt chất lượng, rồi báo cáo và lưu kiến thức. Hoàn toàn abstraction công nghệ — tự quét và dùng các skill kỹ thuật chi tiết khi cần. Dùng cho mọi loại project/stack.
argument-hint: [mô tả yêu cầu tính năng]
---

# Feature Development Workflow

Chạy trong 1 agent duy nhất, tuần tự. Skill này KHÔNG chứa kiến thức công nghệ cụ thể — mọi chi tiết kỹ thuật (ngôn ngữ, framework, DB, messaging...) đến từ các skill khác được quét động ở Bước 0.

Yêu cầu đầu vào: `$ARGUMENTS`

## Bước 0 — Quét & cache skill map (bắt buộc, làm 1 lần đầu mỗi feature)

Quét toàn bộ `.claude/skills/*/SKILL.md` (và `~/.claude/skills/` nếu có), đọc `name` + `description` của từng skill (bỏ qua chính skill này). Xây dựng 1 bảng ánh xạ tạm trong đầu: "ngữ cảnh nào → skill nào phù hợp" dựa trên `description`. Cache lại bảng này cho suốt phiên làm feature — KHÔNG quét lại mỗi lần cần dùng skill, chỉ quét lại nếu bạn nghi ngờ danh sách skill đã thay đổi (VD: user vừa nói đã thêm skill mới).

Mục đích: khi sau này có thêm skill kỹ thuật mới (VD: 1 skill cho ngôn ngữ khác), workflow này KHÔNG cần sửa gì — tự nhận diện qua `description` mà không cần bảng cứng ghi tên trước.

Đồng thời phát hiện bối cảnh project: đọc `CLAUDE.md`, memory/MCP nếu có, code/logic hiện có liên quan — nếu `workflow-router` đã đọc các file này ngay trước đó trong cùng session, dùng lại, không đọc lại. KHÔNG gọi tên công nghệ cụ thể trong phần diễn giải với user ở các bước sau trừ khi cần thiết để truyền đạt quyết định kỹ thuật.

## Bước 1 — Phân tích yêu cầu (vai trò Business Analyst, abstraction)

Diễn giải lại yêu cầu bằng lời (re-verify), liệt kê giả định + câu hỏi mơ hồ. Dừng hỏi user nếu có sai lệch — không tự suy đoán ý định.

## Bước 2 — Đề xuất giải pháp (abstraction, tham chiếu skill kỹ thuật khi liệt kê task)

1. Đọc kiến trúc/convention hiện có — đề xuất nhất quán, KHÔNG tạo kiến trúc lạ nếu không có lý do rõ ràng.
2. Nếu có nhiều hướng hợp lý, đưa nhiều đề xuất riêng biệt. Mỗi đề xuất PHẢI có đủ diagram Mermaid mô tả phương án đó — Flow diagram + Sequence diagram LUÔN bắt buộc (mô tả trực tiếp hành vi/luồng xử lý); Architecture diagram và Component diagram bắt buộc nếu phương án đổi ranh giới hệ thống/thêm-bớt service-module (bỏ qua nếu chỉ sửa nội bộ 1 module, không đổi cấu trúc lớn); ERD bắt buộc nếu phương án đổi data model/schema (bỏ qua nếu không đụng tới dữ liệu lưu trữ). Không vẽ diagram không áp dụng được cho phạm vi thay đổi. Ngoài diagram, mỗi đề xuất còn gồm: Tradeoff giữa các hướng; Acceptance Criteria (Given-When-Then) + Edge Case + Definition of Done theo phương án; danh sách task cần hoàn thành — với mỗi task, ghi chú skill kỹ thuật (từ bảng ánh xạ Bước 0) dự kiến sẽ tham khảo lúc thực thi, KHÔNG cần nêu chi tiết công nghệ ở đây.
3. Ghi toàn bộ nội dung Bước 2 (mọi đề xuất, đầy đủ diagram + tradeoff + AC/Edge Case/DoD + task list) ra file `docs/plans/<feature-slug>.md` — đây là bản lưu để tham chiếu lại, KHÔNG thay thế việc trình bày đầy đủ trực tiếp cho user ngay trong hội thoại.
4. Có thể gợi ý 1 đề xuất kèm lý do, KHÔNG tự chọn thay user.

**CHECKPOINT (bắt buộc)**: trình bày đầy đủ đề xuất (đã ghi ở `docs/plans/<feature-slug>.md`), chờ user xác nhận requirement/solution. KHÔNG sang Bước 3 khi chưa có xác nhận rõ ràng.

Ngay sau khi user chọn xong ở CHECKPOINT: cập nhật lại `docs/plans/<feature-slug>.md` — đưa phương án đã chọn lên đầu, đánh dấu rõ ràng (VD: `## ✅ Phương án đã chọn: <tên>`); các phương án KHÔNG được chọn đẩy xuống dưới, mỗi phương án bọc trong `<details><summary>Phương án không chọn: <tên></summary> ... </details>` để mặc định thu gọn (collapsed) khi xem trên renderer hỗ trợ (GitHub, VS Code preview...).

## Bước 3 — Implement + Test (loop tới khi đạt chất lượng)

### 3.1 Implement

Trước khi viết BẤT KỲ dòng code nào cho 1 phần việc thuộc phạm vi 1 skill kỹ thuật đã ánh xạ ở Bước 0 (VD: phần liên quan Java/Spring → `java-spring-skill`, phần liên quan DB → `database-skill`) — BẮT BUỘC gọi `Read` để đọc TOÀN VĂN file `SKILL.md` tương ứng NGAY LÚC ĐÓ, không dựa vào tên/mô tả 1 dòng đã cache ở Bước 0 để suy luận nội dung. Việc cache ở Bước 0 CHỈ để biết skill nào tồn tại và tên chính xác của nó — KHÔNG thay thế việc đọc nội dung thật khi thực sự áp dụng.

**Quan trọng — không dùng lại cache từ yêu cầu TRƯỚC trong cùng session**: nếu đây là 1 yêu cầu MỚI của user (khác yêu cầu đã xử lý trước đó trong cùng hội thoại), PHẢI `Read` lại từ đầu, KỂ CẢ nếu bạn "nhớ" đã đọc skill này ở lượt trước — nội dung file có thể đã thay đổi giữa 2 lượt (user có thể vừa sửa skill). Chỉ được coi là "đã đọc đủ" trong phạm vi CÙNG 1 yêu cầu/task đang xử lý liên tục, không kéo dài qua nhiều yêu cầu khác nhau.

Nếu 1 task liên quan tới NHIỀU skill (VD: vừa Java/Spring vừa Database), đọc TOÀN BỘ các skill liên quan trước khi bắt đầu viết code cho task đó — không đọc từng phần rồi code xen kẽ tùy tiện.

Sau khi đọc, làm task theo đúng convention/kiến thức trong file đó, KHÔNG tự bịa cách làm dựa trên kiến thức nền chung nếu skill tương ứng đã có hướng dẫn cụ thể khác.

### 3.2 Test

Viết và chạy test đầy đủ theo skill kỹ thuật tương ứng (unit/integration/functional/tùy loại project). Đối chiếu kết quả với:

- Từng Acceptance Criteria đã chốt ở Bước 2.
- Từng Edge Case đã liệt kê.
- Definition of Done.
- **Ngưỡng chất lượng**: test phải pass, không có lỗi nghiêm trọng còn mở, coverage đủ cho các AC quan trọng (không chấp nhận "test cho có" mà bỏ sót AC).

### 3.3 Nếu CHƯA đạt ngưỡng — vào loop fix

Với MỖI issue/lỗi phát hiện (test fail, review tự phát hiện vấn đề):

1. Chẩn đoán nguyên nhân, sửa, chạy lại test liên quan.
2. Tính đây là **lần thử #1** cho issue này.
3. Nếu vẫn fail: thử lại, tăng biến đếm cho issue đó (#2, #3...).
4. **Tối đa 5 lần thử cho MỖI issue riêng biệt.** Nếu tới lần thứ 5 vẫn chưa giải quyết được — DỪNG LẠI, KHÔNG thử tiếp, raise vấn đề này cho user: mô tả issue, đã thử gì ở mỗi lần, tại sao chưa giải quyết được, đề xuất hướng cần user quyết định (đổi cách tiếp cận, chấp nhận giới hạn, hay cần thêm thông tin).
5. Issue MỚI phát sinh (khác issue đang xử lý) được tính là 1 bộ đếm riêng, có 5 lần thử riêng — không cộng dồn số lần thử của issue khác vào nhau.
6. Sau khi 1 issue được giải quyết, chạy lại TOÀN BỘ test liên quan (không chỉ test của issue đó) để đảm bảo không phá vỡ chỗ khác, rồi quay lại 3.2.

Lặp lại 3.1 → 3.2 → 3.3 cho tới khi đạt đủ ngưỡng chất lượng + AC + DoD, HOẶC có issue phải raise cho user (thì dừng workflow tại đó, không tự ý coi như xong).

## Bước 4 — Báo cáo kết quả cuối (bắt buộc)

- AC/DoD nào đạt / chưa đạt.
- Risk/issue phát sinh trong suốt quá trình (kể cả đã fix) — bao gồm cả issue đã raise cho user nếu có.
- Danh sách file đã thay đổi.
- Số lần lặp fix đã dùng cho từng issue (để user thấy độ khó thực tế).

Không cần checkpoint chờ xác nhận riêng ở đây — báo cáo xong làm luôn Bước 5 (ghi log là thao tác phụ, ít rủi ro, sửa lại được nếu user phản hồi khác sau khi đọc báo cáo).

## Bước 5 — Lưu kiến thức & note kinh nghiệm (làm ngay sau Bước 4, không chờ checkpoint)

1. Memory/MCP (nếu có kết nối): ghi quyết định quan trọng, kết quả cuối.
2. File changelog: `docs/changelog/<feature-slug>.md` — kế thừa từ `docs/plans/<feature-slug>.md` (phương án đã chọn + diagram tương ứng, cập nhật lại nếu diagram/thiết kế có đổi trong lúc implement), cộng thêm: lý do chọn phương án, AC/DoD cuối (đạt/chưa đạt), risk còn tồn đọng, danh sách file đã thay đổi. Đây là bản ghi những gì THỰC SỰ đã build cho feature này (khác `docs/plans/` — nơi chỉ ghi các phương án lúc đề xuất), không đặt trong `docs/decisions/` vì sau khi hoàn thành nó không còn là 1 quyết định thuần túy mà là nhật ký thay đổi thực tế của feature.
3. **Experience log (bắt buộc, tích lũy lâu dài, KHÔNG ghi đè)**: append vào `docs/knowledge/experience-log.md` — với mỗi issue đã gặp trong Bước 3.3 (dù đã fix hay chưa fix được), ghi theo format:

   ```markdown
   ## [<ngày>] <feature-slug> — <mô tả issue ngắn gọn>

   - Nguyên nhân: ...
   - Số lần thử: X/5
   - Kết quả: Đã fix | Chưa fix (raised cho user)
   - Cách fix (nếu có) / Hướng đã thử mà KHÔNG hiệu quả (để lần sau không lặp lại)
   ```

Mục đích: lần sau gặp issue tương tự (cùng project hoặc project khác), đọc file này trước để tránh thử lại đúng những hướng đã biết là không hiệu quả.
