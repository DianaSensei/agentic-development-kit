---
name: tauri-react-skill
description: Kiến thức chuyên sâu implement code Tauri (Rust backend) + React (frontend) cho desktop app — IPC command/invoke, capabilities/permissions, plugin chuẩn (dialog/fs/store/sql), xử lý đa OS (`#[cfg(target_os)]`), state loading/error/empty ở React. Phối hợp với `data-storage-skill` (thiết kế lưu trữ) và `ui-ux-design-skill` (thiết kế UX) — skill này CHỈ lo phần code thực thi. Dùng khi implement/sửa code trong app Tauri+React.
---

# Tauri + React — Implementation

## Discover
Đọc `src-tauri/Cargo.toml` + `src-tauri/tauri.conf.json` (version Tauri, plugin đã cài), `package.json` (React version, state management đang dùng — Context/Redux/Zustand/React Query). Đọc `capabilities/*.json` hiện có. KHÔNG giả định version/plugin nếu chưa thấy bằng chứng — API Tauri v1 và v2 khác nhau đáng kể (đặc biệt permission/capabilities model).

## IPC: Command & Invoke
- Command Rust (`#[tauri::command]`) nên trả `Result<T, E>` rõ ràng thay vì panic — panic trong command làm crash toàn bộ tiến trình backend, không chỉ fail request đó.
- Validate input ở phía Rust dù React đã validate — không tin dữ liệu từ frontend (frontend có thể bị bypass qua devtools/webview).
- Đặt tên command nhất quán convention hiện có (`snake_case` phía Rust, gọi qua `invoke('command_name', {...})` phía React).
- Thao tác dài (I/O lớn, xử lý nặng): tránh block main thread của Rust — dùng `async fn` command hoặc `tauri::async_runtime::spawn` cho việc nặng, để UI không bị treo.
- Cần gửi tiến trình liên tục (progress, log realtime) → dùng event (`emit`/`listen`) thay vì poll bằng invoke lặp lại.

## Capabilities & Permissions (Tauri v2 — least-privilege)
- Khai báo permission CHỈ đúng scope cần dùng trong `capabilities/*.json` (VD: `fs:allow- read-file` với `path` scope cụ thể, không cấp quyền full filesystem nếu chỉ cần đọc 1 thư mục cấu hình).
- Không bật `"dangerousRemoteDomainIpcAccess"` hoặc mở CSP quá rộng nếu không thực sự cần.
- Mỗi plugin thêm vào phải đi kèm khai báo permission tương ứng trong capabilities — thiếu khai báo sẽ khiến command bị chặn ở runtime dù code Rust đúng (lỗi dễ nhầm là "bug logic" trong khi thực chất là thiếu permission).

## Plugin chuẩn
- **Dialog** (`tauri-plugin-dialog`): dùng cho open/save file picker, confirm dialog native — không tự dựng modal HTML giả lập file picker OS.
- **FS** (`tauri-plugin-fs`): thao tác file thô, luôn qua scope đã khai báo trong capabilities, không dùng path tuyệt đối build tay từ input user chưa validate (path traversal risk — chuẩn hóa/kiểm tra path nằm trong base dir cho phép).
- **Store** (`tauri-plugin-store`): key-value JSON, xem chi tiết chọn lựa ở `data-storage- skill` — skill này chỉ lo code gọi đúng API (`load`, `get`, `set`, `save`).
- **SQL** (`tauri-plugin-sql`): connection string/migration setup, dùng đúng API async của plugin (`Database.load`, `execute`, `select`) — schema/migration design xem `data- storage-skill`.
- Plugin chuẩn cần thiết trực tiếp cho task (dialog/fs/store/sql ở trên) thì tự thêm bình thường, khai báo permission tối thiểu tương ứng, chỉ nêu trong báo cáo là đã thêm. Không tự thêm plugin NGOÀI phạm vi task đang làm — mỗi plugin thêm quyền truy cập hệ thống, tăng bề mặt tấn công, nên việc thêm phải gắn với nhu cầu cụ thể chứ không phải "tiện thì thêm".

## Đa OS (`#[cfg(target_os)]`)
- Nếu có logic khác nhau giữa macOS/Windows/Linux (path mặc định, menu bar, tray icon, keyboard shortcut convention), dùng `#[cfg(target_os = "macos")]`/`"windows"`/`"linux"` tường minh — PHẢI xử lý ĐỦ CẢ 3 OS mà app target, không chỉ code cho OS đang dev rồi bỏ quên 2 OS còn lại (lỗi phổ biến: chỉ test trên máy dev, ship lỗi trên OS khác).
- Đường dẫn file hệ thống (app data dir, config dir): dùng API của Tauri (`app_handle.path().app_data_dir()`...) thay vì hardcode path kiểu Unix/Windows, để tự đúng theo từng OS.

## React — State cho thao tác gọi Tauri
- Mọi lời gọi `invoke` xuyên tiến trình PHẢI có đủ 3 trạng thái ở UI: loading, error, và success/empty (không data) — không để UI "đứng im" không phản hồi trong lúc chờ Rust xử lý, và không nuốt lỗi im lặng khi `invoke` reject.
- Cleanup listener (`listen`/`once`) đúng lúc unmount component (gọi hàm unlisten trả về từ `listen`) — tránh listener rò rỉ, nhận event trùng khi component mount lại nhiều lần.
- Tránh gọi `invoke` lặp lại không cần thiết trong render loop (dùng `useEffect` với dependency đúng, hoặc React Query/SWR nếu project đã dùng để cache kết quả).

## Issue thường gặp trong thực tế
- **WebView khác nhau theo OS**: Windows dùng WebView2 (Chromium), macOS dùng WKWebView (Safari engine), Linux dùng WebKitGTK — CSS/JS feature support khác nhau giữa 3 engine này (đặc biệt CSS mới, một số Web API). Test trên devtools của 1 OS KHÔNG đảm bảo đúng trên OS khác — đây là lý do phải test đủ 3 OS trước khi báo hoàn thành nếu app target cả 3.
- **CSP quá chặt**: Content-Security-Policy trong `tauri.conf.json` chặn resource hợp lệ (inline style/script, font external) thường gây lỗi im lặng trong console browser (bị chặn, không phải lỗi logic React) — dễ nhầm là bug component khi thực chất là CSP.
- **Thiếu permission không phải lúc nào cũng lỗi rõ ràng**: 1 số plugin fail âm thầm hoặc trả lỗi chung chung khi thiếu capability, dễ nhầm là bug code Rust — luôn kiểm tra `capabilities/*.json` trước khi debug sâu vào logic command.

## Test
- Rust: unit test cho command logic thuần (tách business logic ra khỏi `#[tauri::command]` wrapper để test không cần khởi động runtime Tauri đầy đủ).
- React: test component với `invoke` đã mock (không gọi Tauri runtime thật trong unit test) — test cả 3 nhánh loading/error/success.
- Nếu cần test tích hợp thật (cả Rust + WebView), ghi rõ đây là test thủ công/manual QA nếu project chưa có hạ tầng E2E cho desktop (WebDriver/tauri-driver). KHÔNG tự dựng mới hạ tầng E2E (chi phí thiết lập lớn, ảnh hưởng toàn bộ quy trình test của project) — đề xuất kèm lý do, chờ user quyết định có đầu tư hạ tầng này không.

## Ranh giới
Không tự quyết định cơ chế lưu trữ (SQLite vs store vs fs) — đó là `data-storage-skill`. Không tự quyết định layout/luồng UX — đó là `ui-ux-design-skill`. Skill này chỉ lo phần code Rust command + capabilities + code React gọi/hiển thị kết quả đúng theo quyết định đã chốt ở 2 skill kia. Review cuối → `code-review-skill`.
