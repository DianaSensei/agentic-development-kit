---
name: ui-ux-design-skill
description: Kiến thức chuyên sâu UI/UX design — nguyên tắc usability, accessibility, consistency, responsive/cross-platform cho desktop app. Dùng khi feature có thành phần giao diện cần thiết kế trước khi implement, phối hợp với tauri-react-skill.
---

# UI/UX Design

## Discover
Đọc design system hiện có (nếu có): design token (màu, spacing, typography), component
library đang dùng, style guide trong `CLAUDE.md` hoặc file convention riêng. Giữ nhất
quán, không tự tạo pattern UI mới nếu đã có chuẩn.

## Usability Heuristics (Nielsen, áp dụng thực tế)
- **Visibility of system status**: luôn cho user biết đang xảy ra gì (loading, progress,
  đã lưu chưa) — không để UI im lặng khi đang xử lý.
- **Error prevention & recovery**: validate trước khi submit khi có thể, thông báo lỗi rõ
  ràng kèm cách khắc phục, không chỉ báo "Error" chung chung.
- **Consistency**: cùng 1 hành động phải có cùng 1 cách thực hiện xuyên suốt app (không
  nơi này dùng nút, nơi khác dùng gesture cho cùng chức năng).
- **User control**: luôn có đường lùi (Cancel/Undo) cho hành động không thể hoàn tác ngay
  lập tức nếu khả thi.

## Accessibility (a11y)
- Contrast màu đủ (WCAG AA tối thiểu: 4.5:1 cho text thường).
- Hỗ trợ điều hướng bàn phím đầy đủ (Tab/Enter/Esc) — quan trọng với desktop app hơn cả
  mobile vì user quen dùng bàn phím.
- Label rõ ràng cho input/button (không chỉ icon không có text/aria-label).
- Size touch/click target đủ lớn (tối thiểu ~44x44px) dù là desktop, vì màn hình cảm ứng
  (tablet chạy Windows) vẫn có thể dùng app.

## Responsive & Cross-platform (đặc thù desktop app)
- Test layout ở nhiều kích thước cửa sổ (user có thể resize tùy ý, khác hẳn mobile app cố
  định) — tránh layout vỡ khi cửa sổ nhỏ lại.
- Tôn trọng convention UI riêng từng OS khi hợp lý (menu bar macOS ở trên cùng màn hình vs
  trong window ở Windows/Linux) — nhưng vẫn giữ nhất quán trải nghiệm cốt lõi.
- Dark mode/light mode: nếu hỗ trợ, đảm bảo mọi màu sắc dùng token thay vì hardcode, tránh
  sót 1 vài chỗ không đổi theo theme.

## Information Architecture
Trước khi thiết kế màn hình cụ thể, xác định rõ: user cần thấy thông tin gì đầu tiên (độ
ưu tiên hiển thị), luồng thao tác chính (bao nhiêu bước để hoàn thành tác vụ chính, càng
ít càng tốt nhưng không hy sinh rõ ràng).

## Khi có nhiều hướng thiết kế hợp lý
Với màn hình/luồng nhỏ, phạm vi rõ (thêm 1 form, 1 danh sách, 1 dialog...) — tự chọn
phương án tốt nhất theo usability heuristics ở trên (ưu tiên quen thuộc/nhất quán với
pattern hiện có của app hơn là sáng tạo mới), nêu ngắn gọn lý do đã chọn thay vì hỏi trước.
Chỉ trình bày 2-3 phương án kèm tradeoff (đơn giản hơn vs linh hoạt hơn, quen thuộc vs mới
lạ) và để user chọn khi đây là luồng/màn hình LỚN, ảnh hưởng nhiều phần khác của app hoặc
đổi mental model người dùng đã quen — quyết định khó đảo ngược sau khi user đã quen dùng.

## Ranh giới
Skill này thiết kế Ý TƯỞNG/layout/luồng UX — việc implement code cụ thể (component React,
command Tauri) thuộc về `tauri-react-skill`. Nếu cần mockup trực quan, có thể tạo bằng HTML/
React artifact tạm để user hình dung trước khi code thật.
