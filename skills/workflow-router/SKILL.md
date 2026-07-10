---
name: dev-request-router
description: Use FIRST for ANY development-related request in natural language — new feature, bug fix, refactor, enhancement, mechanism change, "improve", "implement more", "add capability", etc. Classifies the request as feature-development, bug-fix, or refactor based on its true nature (not surface wording) — key question: does external behavior change, and if so, is it fixing a defect or adding/changing capability? Asks the user if genuinely ambiguous, then explicitly hands off to the correct workflow skill. ALWAYS invoke this before feature-development, bug-fix, or refactor directly when the request type isn't already obvious.
---

# Dev Request Router

Nhiệm vụ DUY NHẤT của skill này: phân loại đúng loại yêu cầu rồi chuyển giao — KHÔNG tự
làm phân tích/implement gì cả (đó là việc của `feature-development`/`bug-fix`).

## Vấn đề cần giải quyết
Người dùng diễn đạt yêu cầu bằng rất nhiều cách khác nhau, không phải lúc nào cũng nói rõ
"đây là feature mới" hay "đây là bug fix":
- Rõ ràng feature: "phát triển tính năng mới", "cần thêm tính năng X", "bổ sung khả năng Y".
- Rõ ràng bug: "fix bug", "sửa lỗi X", "app bị crash khi...".
- **MƠ HỒ, cần phân biệt kỹ**: "thay đổi cơ chế A", "implement thêm B", "improve C", "cải
  thiện D" — những cụm này có thể là feature MỚI hoặc sửa hành vi ĐANG SAI, tùy ngữ cảnh
  thực tế, không thể đoán chỉ từ từ ngữ bề mặt.

## Nguyên tắc phân loại (dựa vào BẢN CHẤT, không dựa vào từ khóa)
Câu hỏi cốt lõi cần trả lời: **hành vi hiện tại của hệ thống có đang SAI so với thiết
kế/kỳ vọng ban đầu không? Và yêu cầu có đổi hành vi bên ngoài hay không?**

- **Hành vi hiện tại đang SAI** (dù user dùng từ "cải thiện"/"improve"/"thay đổi cơ chế")
  → `bug-fix`. VD: "cải thiện cơ chế retry đang bị lặp vô hạn".
- **Hành vi hiện tại ĐÚNG, cần thêm/mở rộng khả năng mới hoặc đổi sang spec khác theo chủ
  đích (hành vi bên ngoài SẼ đổi)** → `feature-development`. VD: "thay đổi cơ chế tính
  điểm thưởng từ theo đơn sang theo giá trị".
- **Hành vi hiện tại ĐÚNG và PHẢI giữ nguyên, chỉ cải thiện cấu trúc/hiệu năng/khả năng
  bảo trì code (không có thay đổi nào user quan sát được từ bên ngoài)** → `refactor`. VD:
  "cải thiện cơ chế xử lý đơn hàng cho dễ test hơn, không đổi hành vi", "gộp lại logic
  duplicate ở OrderService và ProductService", "tối ưu lại cấu trúc code cho dễ mở rộng".

Đây là lý do các từ như "cải thiện"/"thay đổi cơ chế"/"improve" đặc biệt mơ hồ — chúng có
thể rơi vào CẢ 3 loại tùy ngữ cảnh, câu hỏi quyết định luôn là: *"hành vi bên ngoài có đổi
không, và nếu có, đó là vì đang sửa lỗi hay vì đang mở rộng/đổi spec?"*

## Quy trình
1. Đọc yêu cầu, đối chiếu với code/logic hiện có (đọc nhanh, không cần sâu như các workflow
   đích sẽ tự làm) để xác định: hành vi hiện tại có đang lỗi không, và yêu cầu có đổi hành
   vi bên ngoài hay không.
2. Nếu **rõ ràng** thuộc 1 trong 3 loại → nói rõ 1 câu xác nhận loại đã chọn, rồi chuyển
   giao ngay, không cần hỏi thêm.
3. Nếu **vẫn mơ hồ** sau khi đọc code — hỏi lại NGẮN GỌN, đúng 1 câu dạng single-select 3
   lựa chọn:
   > "Đây là: (a) thêm khả năng MỚI/đổi spec (feature), (b) sửa hành vi ĐANG SAI (bug fix),
   > hay (c) chỉ cải thiện code mà KHÔNG đổi hành vi bên ngoài (refactor)?"
4. Sau khi xác định, nói rõ tường minh: *"Xác định đây là [feature-development/bug-fix/
   refactor], chuyển sang workflow tương ứng."* — KHÔNG âm thầm chuyển.

## Trường hợp không khớp gọn vào cả 3 (hiếm — VD: đổi tooling/CI/infra thuần túy, không
liên quan code nghiệp vụ lẫn hành vi)
Hiện hệ thống chưa có workflow riêng cho loại "platform/infra". Nếu gặp trường hợp này,
nói rõ với user đây là khoảng trống hiện tại, hỏi họ muốn xử lý tạm theo hướng nào (thường
gần `refactor` nhất về mặt quy trình — có checkpoint, verify, không có AC mới) thay vì tự
ý chọn.
