---
name: data-storage-skill
description: Kiến thức chuyên sâu thiết kế lưu trữ local/offline CHỈ CHO app desktop Tauri+React — SQLite (tauri-plugin-sql), key-value (tauri-plugin-store), file thô (tauri-plugin-fs). KHÔNG dùng cho database server-side (Oracle/Postgres/MySQL/Mongo — xem database-skill; Redis — xem redis-skill; Elasticsearch — xem elasticsearch-skill). Dùng khi feature Tauri cần lưu dữ liệu offline trên máy user.
---

# Data/Storage — Local & Offline (Tauri Desktop)

## Phạm vi (đọc kỹ trước khi dùng)
Skill này CHỈ áp dụng cho lưu trữ **local trên máy user**, không có server/DB trung tâm. Nếu project có backend Java kết nối Oracle/Postgres/MySQL/Mongo → dùng `database-skill`. Nếu dùng Redis/Elasticsearch → dùng `redis-skill`/`elasticsearch-skill` tương ứng.

## GIAI ĐOẠN 0 — Discover (bắt buộc)
Xác định cơ chế lưu trữ đang dùng theo bằng chứng cụ thể trong `Cargo.toml`/`package.json`: `tauri-plugin-sql`, `tauri-plugin-store`, `tauri-plugin-fs`. KHÔNG suy đoán nếu chưa thấy bằng chứng. Nếu project mới chưa có gì, liệt kê lựa chọn kèm tradeoff (xem bên dưới).

## GIAI ĐOẠN 1 — Đánh giá thay đổi
Phân loại: **ADD** (mới), **MODIFY** (đổi cấu trúc hiện có), **REMOVE/DEPRECATE**, **NONE**.

## GIAI ĐOẠN 2 — Chọn cơ chế lưu trữ (khi chưa bị ràng buộc bởi cái đã có)
- **`tauri-plugin-store`**: key-value JSON đơn giản — phù hợp settings/preference, dữ liệu nhỏ không cần query phức tạp (VD: theme, ngôn ngữ, vị trí cửa sổ).
- **`tauri-plugin-sql`** (SQLite): phù hợp khi cần query có điều kiện, quan hệ giữa nhiều loại dữ liệu, hoặc dataset lớn hơn cần index để truy xuất nhanh.
- **`tauri-plugin-fs`**: file thô (JSON/CSV/binary tự định dạng) — phù hợp khi dữ liệu là file người dùng thao tác trực tiếp (export/import), hoặc blob lớn không nên nhét vào SQLite.

Với **ADD** (dữ liệu mới, chưa tồn tại trên máy user nào) — tự chọn cơ chế lưu trữ phù hợp nhất theo 5 trục: dung lượng, tốc độ truy xuất, quyền/bảo mật (file permission trên từng OS), rủi ro, khả năng mở rộng sau này; nêu ngắn gọn lý do đã chọn trong báo cáo thay vì hỏi trước. Với **MODIFY/REMOVE** cơ chế đang lưu dữ liệu thật của user hiện có — luôn trình bày **options** kèm tradeoff theo 5 trục trên và chờ user quyết định, vì sai lựa chọn ở đây có thể làm mất dữ liệu đã lưu trên máy user (không có DBA/rollback tập trung như server).

## GIAI ĐOẠN 3 — Schema & Migration
- SQLite: ERD Mermaid **đầy đủ** (không phải diff), đánh dấu phần mới/thay đổi.
- Key-value/file: JSON Schema mô tả đầy đủ cấu trúc.
- Migration: ưu tiên backward-compatible (app có thể đang chạy version cũ trên máy user khác nhau) — migration PHẢI tự chạy lúc app khởi động, có rollback plan hoặc chí ít không phá hỏng dữ liệu cũ nếu migration fail giữa chừng.

## Issue thường gặp trong thực tế
- **SQLite single-writer lock**: SQLite chỉ cho phép 1 writer tại 1 thời điểm — nhiều command Tauri ghi đồng thời (VD: 2 sự kiện UI trigger ghi cùng lúc) dễ gặp lỗi "database is locked" nếu không bật WAL mode (`PRAGMA journal_mode=WAL` — cho phép đọc song song lúc ghi) hoặc không serialize các thao tác ghi ở tầng ứng dụng.

## Lưu ý đặc thù desktop/offline (khác hẳn DB server-side)
- Không có DBA canh chừng — migration lỗi có thể khiến app user không mở được nữa, xử lý migration failure phải có fallback (backup file cũ trước khi migrate, hoặc catch lỗi và cho phép app chạy tiếp với dữ liệu rỗng thay vì crash).
- Dung lượng giới hạn bởi đĩa máy user, không phải server — tránh thiết kế phình to không cần thiết (VD: lưu ảnh/file lớn trực tiếp trong SQLite blob nếu `tauri-plugin-fs` phù hợp hơn).
- Không có network để "backup lên cloud" mặc định — nếu nghiệp vụ cần backup/sync, đó là quyết định kiến trúc lớn (thêm hạ tầng network/cloud mới cho 1 app vốn offline-first), luôn cần bàn riêng và chờ user duyệt trước khi thêm.

## Việc KHÔNG làm
Không viết code Rust/React thực thi (xem `tauri-react-skill`). Không tự đổi cơ chế lưu trữ ĐANG dùng để giữ dữ liệu thật của user trừ khi user yêu cầu rõ hoặc không còn lựa chọn khả thi (nêu rõ lý do) — nhưng với nhu cầu lưu trữ MỚI trong phạm vi task, tự chọn cơ chế phù hợp nhất mà không cần hỏi.
