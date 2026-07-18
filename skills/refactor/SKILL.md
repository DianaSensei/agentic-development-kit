---
name: refactor
description: Quy trình refactor code — cải thiện cấu trúc/hiệu năng/khả năng bảo trì mà KHÔNG được đổi hành vi bên ngoài (API response, side-effect, output phải giữ nguyên 100%). Dùng khi yêu cầu là dọn dẹp/tái cấu trúc/cải thiện chất lượng code, không phải thêm tính năng mới hay sửa hành vi sai. Hoàn toàn abstraction công nghệ — tự quét và dùng các skill kỹ thuật chi tiết khi cần.
argument-hint: "[mô tả phần code cần refactor + lý do]"
---

# Refactor Workflow

Chạy trong 1 agent duy nhất, tuần tự. Nguyên tắc TỐI THƯỢNG xuyên suốt: **hành vi bên ngoài của hệ thống (API response, side-effect, dữ liệu ghi ra, log, event phát ra...) PHẢI giữ nguyên 100% trước và sau refactor**. Nếu tại bất kỳ điểm nào phát hiện không thể refactor mà giữ nguyên hành vi — DỪNG LẠI, báo user, KHÔNG tự ý coi đây là "refactor kèm sửa nhỏ".

## Bước 0 — Quét & cache skill map + Discover bối cảnh
Giống `feature-development`/`bug-fix`: quét `.claude/skills/*/SKILL.md` (bỏ qua skill này), đọc `CLAUDE.md`, memory/MCP nếu có, code/logic hiện có ở khu vực cần refactor — nếu `workflow-router` đã đọc các file này ngay trước đó trong cùng session, dùng lại, không đọc lại.

## Bước 1 — Xác định rõ pain point (KHÔNG chấp nhận mô tả mơ hồ)
Yêu cầu refactor phải cụ thể hóa được TẠI SAO cần refactor — không chấp nhận lý do chung chung như "code xấu". Làm rõ 1 trong các loại pain point:
- Code duplicate (DRY violation) ở đâu, lặp lại bao nhiêu chỗ.
- Coupling quá chặt, khó test độc lập (phải mock quá nhiều dependency không liên quan).
- Hiệu năng kém do cấu trúc (không phải do thiếu index/cache — cái đó là việc của skill kỹ thuật tương ứng, refactor ở đây là về cấu trúc code).
- Khó mở rộng do vi phạm nguyên tắc thiết kế (God class, vi phạm Single Responsibility...).
- Naming/structure không nhất quán với convention hiện tại của project.

Nếu user mô tả mơ hồ ("dọn code này cho sạch"), hỏi lại cụ thể pain point nào đang nhắm tới trước khi tiếp tục — refactor không có mục tiêu rõ ràng dễ lan man, đổi quá nhiều thứ không cần thiết.

## Bước 2 — Kiểm tra "lưới an toàn" TRƯỚC khi refactor (bắt buộc, không bỏ qua)
Refactor an toàn đòi hỏi có test bao phủ ĐỦ hành vi hiện tại trước khi động vào code.
1. Kiểm tra test hiện có cho khu vực cần refactor — có bao phủ đủ các nhánh hành vi quan trọng không (không chỉ happy path).
2. Nếu THIẾU bao phủ: viết **characterization test** trước — test ghi lại ĐÚNG hành vi hiện tại (dù hành vi đó tối ưu hay không, dù có bug tiềm ẩn hay không — KHÔNG sửa bug trong bước này, chỉ ghi lại "hiện tại nó đang chạy thế này"). Nếu phát hiện bug thật sự trong lúc viết characterization test, DỪNG LẠI, báo user: đây không còn là refactor thuần túy nữa, cần chuyển sang `bug-fix` trước, quay lại refactor sau khi bug đã fix.
3. KHÔNG bắt đầu Bước 3 nếu chưa có lưới an toàn đủ tin cậy.

## Bước 3 — Đề xuất phương án refactor
1. Đọc convention/kiến trúc hiện có, đề xuất theo pattern refactor phù hợp (extract method/class, introduce interface, replace conditional with polymorphism, strangler fig cho refactor lớn theo từng phần...).
2. Nếu có nhiều hướng hợp lý, đưa nhiều đề xuất kèm tradeoff (mức độ thay đổi, rủi ro, thời gian), giống `feature-development` Bước 2 — nhưng KHÔNG cần AC/Edge Case theo nghĩa thêm hành vi mới, thay bằng: "Behavior Preservation Checklist" (danh sách hành vi cụ thể PHẢI giữ nguyên, đối chiếu từ characterization test ở Bước 2).
3. Xác định phạm vi: refactor 1 lần (nếu nhỏ) hay chia nhiều bước nhỏ tăng dần (nếu lớn) — ưu tiên chia nhỏ để mỗi bước dễ verify, dễ rollback nếu có vấn đề.

**CHECKPOINT (bắt buộc)**: trình bày phương án, chờ user xác nhận trước khi thực thi.

## Bước 4 — Thực thi (từng bước nhỏ, verify liên tục)
1. Refactor theo TỪNG bước nhỏ đã chia ở Bước 3 — KHÔNG làm 1 lần lớn rồi mới test cuối cùng (rủi ro cao, khó xác định điểm gây lỗi nếu có).
2. Sau MỖI bước nhỏ: chạy lại toàn bộ test liên quan (bao gồm characterization test) — PHẢI pass 100% trước khi sang bước nhỏ tiếp theo.
3. Nếu 1 bước làm vỡ test: sửa lại trong phạm vi hợp lý, tối đa **3 lần thử** cho bước đó (ít hơn 5 lần của `feature-development`/`bug-fix` vì bản chất refactor nên rủi ro thấp, sửa nhiều lần không thành công là dấu hiệu hướng refactor không ổn). Nếu vẫn fail sau 3 lần: **ROLLBACK bước đó** (revert lại trạng thái trước bước nhỏ này, dùng git nếu có), báo cáo user, không tiếp tục refactor dở dang trên trạng thái lỗi.
4. Tham khảo skill kỹ thuật phù hợp (đọc TOÀN VĂN `SKILL.md` liên quan NGAY LÚC áp dụng, không dùng cache từ yêu cầu trước trong session — cùng nguyên tắc như `feature-development`) cho cách viết code chuẩn theo stack.

## Bước 5 — Xác nhận hành vi không đổi (bắt buộc, khác biệt cốt lõi so với 2 workflow kia)
1. Chạy lại TOÀN BỘ test suite liên quan (không chỉ test của khu vực vừa refactor) — đảm bảo không phá vỡ phần khác của hệ thống.
2. Đối chiếu lại "Behavior Preservation Checklist" ở Bước 3 — xác nhận từng mục vẫn đúng.
3. Nếu có thể, so sánh output cụ thể trước/sau (VD: chạy cùng input, so sánh response) để có bằng chứng cụ thể ngoài việc "test pass" — test có thể sót case.

## Bước 6 — Báo cáo kết quả cuối (bắt buộc)
- Pain point ban đầu đã giải quyết như thế nào (đối chiếu Bước 1).
- Xác nhận rõ ràng: hành vi bên ngoài có thay đổi gì không (phải là "Không" — nếu có, đây là vấn đề nghiêm trọng cần nêu bật, không chôn trong chi tiết).
- Danh sách file đã thay đổi, số bước nhỏ đã thực hiện, có bước nào phải rollback không.
- Risk còn tồn đọng (nếu có).
- Đã chạy `code-review-skill` (nếu có) trước khi báo cáo.

Không cần checkpoint chờ xác nhận riêng ở đây — báo cáo xong làm luôn Bước 7 (ghi log là thao tác phụ, ít rủi ro, sửa lại được nếu user phản hồi khác).

## Bước 7 — Lưu kiến thức (làm ngay sau Bước 6)
1. Memory/MCP (nếu có kết nối): ghi lại pattern refactor đã áp dụng, lý do.
2. `docs/decisions/<refactor-slug>.md`: pain point, phương án đã chọn, behavior preservation checklist, kết quả.
3. **Experience log** (tích lũy, append): `docs/knowledge/experience-log.md` — ghi lại pattern refactor nào hiệu quả/không hiệu quả cho loại pain point tương ứng, để lần sau tham khảo khi gặp pain point tương tự.
