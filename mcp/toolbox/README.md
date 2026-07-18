# Database MCP (PostgreSQL, Redis, MongoDB)

Cấu hình cho [MCP Toolbox](https://github.com/googleapis/mcp-toolbox) của
Google — một binary chạy trên máy, đứng giữa Claude Code và database. Sau
khi kết nối, có thể yêu cầu Claude Code trực tiếp: "liệt kê bảng trong
database primary", "lấy giá trị key user:123 trong Redis", thay vì tự mở
client của từng database.

Cấu hình sẵn hai nguồn PostgreSQL (`primary`, `analytics`), một Redis, một
MongoDB. Không bắt buộc dùng đủ cả bốn — nguồn nào không có thông tin kết
nối thì bỏ qua, không ảnh hưởng các nguồn còn lại.

Lưu ý quan trọng: phần PostgreSQL trong cấu hình này chỉ đọc dữ liệu, không
có tool nào ghi/xoá/sửa bảng. Lý do và cách đảm bảo điều này được nói ở cuối
tài liệu.

## Cài binary

Cách cài đặt chính thức, cập nhật theo phiên bản mới nhất, nằm ở
[trang giới thiệu MCP Toolbox](https://mcp-toolbox.dev/documentation/introduction/#installing-the-server)
và [trang Releases trên GitHub](https://github.com/googleapis/mcp-toolbox/releases)
— tham khảo hai trang này nếu gợi ý dưới đây không còn đúng.

Trên macOS, cách nhanh nhất là qua Homebrew (tự lấy bản mới nhất, không cần
tự tải theo version):

```bash
brew install mcp-toolbox
```

Lệnh này cài binary tên `toolbox`. Chạy `toolbox --version` để xác nhận.
Không dùng Homebrew hoặc dùng Linux/Windows thì tải binary trực tiếp từ
trang Releases ở trên, chọn đúng bản ứng với hệ điều hành.

Ngoài ra cần thông tin kết nối database, xin từ người quản trị hệ thống.
Riêng PostgreSQL, yêu cầu tài khoản có quyền chỉ đọc (read-only), không
dùng tài khoản admin.

## Cấu hình `.env`

```bash
cp .env.example .env
```

| Biến | Áp dụng cho | Ghi chú |
|---|---|---|
| `POSTGRES_PRIMARY_*` | PostgreSQL #1 | host/port/database/user/password — user phải là tài khoản read-only |
| `POSTGRES_ANALYTICS_*` | PostgreSQL #2 | tương tự, nếu có nguồn thứ hai |
| `REDIS_ADDRESS` | Redis | dạng `host:port` |
| `REDIS_USERNAME` / `REDIS_PASSWORD` | Redis | để trống nếu không dùng xác thực |
| `REDIS_DATABASE` | Redis | số thứ tự database, mặc định `0` |
| `MONGODB_URI` | MongoDB | connection string đầy đủ |
| `MONGODB_DATABASE` / `MONGODB_COLLECTION` | MongoDB | database/collection mặc định |

Nguồn nào không dùng có thể giữ nguyên giá trị mẫu.

## Chạy thử

Trong thư mục này (dùng `toolbox` nếu cài qua Homebrew, hoặc `./toolbox` nếu
tải binary trực tiếp vào thư mục này):

```bash
set -a && source .env && set +a
toolbox --config tools.yaml
```

Thấy dòng `Server ready to serve!` là khởi động thành công. Giữ nguyên
process này chạy, không đóng terminal.

Nếu gặp lỗi, nguyên nhân thường nằm ở giá trị sai trong `.env` — message
lỗi thường chỉ rõ trường nào không hợp lệ.

## Đăng ký với Claude Code

Mở một terminal khác (không tắt process toolbox đang chạy):

```bash
claude mcp add toolbox --scope user --transport http http://127.0.0.1:5000/mcp
```

Xác nhận:

```bash
claude mcp list
```

Trạng thái `✔ Connected` cạnh `toolbox` là hoàn tất. Nếu thấy
`✘ Failed to connect`, kiểm tra lại process toolbox ở bước trước có còn
chạy hay không.

## Kiểm tra sau khi kết nối

Thử một vài yêu cầu với Claude Code:
- "Liệt kê các bảng trong database primary"
- "Query 10 dòng đầu bảng users trong database analytics"
- "Lấy giá trị key session:abc123 trong Redis"
- "Tìm document có status=active trong MongoDB"

Nêu rõ nguồn dữ liệu (primary/analytics/Redis/MongoDB) trong yêu cầu, Claude
Code sẽ tự chọn đúng tool tương ứng.

---

## Cấu hình nâng cao

**Chạy dưới dạng stdio thay vì giữ process HTTP** — Claude Code sẽ tự khởi
động toolbox khi cần, không phải giữ terminal chạy liên tục:

```bash
claude mcp add toolbox --scope user -- toolbox --stdio --config /đường-dẫn-tuyệt-đối/tools.yaml
```

Cách này yêu cầu các biến trong `.env` phải được nạp vào môi trường trước
khi Claude Code khởi động process — phức tạp hơn HTTP, nên chỉ dùng khi có
lý do cụ thể.

**Giới hạn phạm vi kết nối, ví dụ chỉ mở Redis** — thêm tên toolset vào
cuối URL:

```bash
claude mcp add redis-only --scope user --transport http http://127.0.0.1:5000/mcp/redis-toolset
```

Các toolset có sẵn: `postgres-primary-toolset`, `postgres-analytics-toolset`,
`redis-toolset`, `mongodb-toolset`, `all` (mặc định).

**Đăng ký qua file config thay vì lệnh CLI** — `claude mcp add` về bản chất
chỉ ghi vào một file cấu hình, có thể chỉnh trực tiếp. Phạm vi cá nhân, sửa
`~/.claude.json`:

```json
{
  "mcpServers": {
    "toolbox": { "type": "http", "url": "http://127.0.0.1:5000/mcp" }
  }
}
```

Chia sẻ với team, tạo `.mcp.json` ở gốc project và commit vào git (mỗi
thành viên vẫn tự chạy toolbox trên máy họ):

```json
{
  "mcpServers": {
    "toolbox": {
      "type": "stdio",
      "command": "toolbox",
      "args": ["--stdio", "--config", "${CLAUDE_PROJECT_DIR}/mcp/toolbox/tools.yaml"]
    }
  }
}
```

Claude Code chỉ đọc lại `.mcp.json` khi mở phiên làm việc mới.

**Thêm datasource PostgreSQL thứ ba** — sao chép một khối `kind: source`
trong `tools.yaml` (ví dụ `postgres-analytics-source`), đổi tên, trỏ sang
bộ biến môi trường mới (ví dụ `POSTGRES_REPORTING_*`), bổ sung các biến đó
vào `.env` và `.env.example`. Sao chép luôn hai tool `*_query_data` và
`*_list_tables` đi kèm, thêm vào một toolset.

## Vì sao PostgreSQL chỉ đọc

Toolbox không kiểm tra nội dung câu SQL trước khi thực thi — câu lệnh nào
đưa vào cũng được chạy nguyên văn, miễn tài khoản kết nối có quyền thực
hiện. `tools.yaml` chủ động không định nghĩa tool ghi/xoá/sửa nào, nhưng đó
chỉ là một lớp bảo vệ ở mức cấu hình, không phải giới hạn kỹ thuật cứng.

Lớp bảo vệ thực sự nằm ở tài khoản PostgreSQL khai báo trong `.env`. Tài
khoản này cần chỉ có quyền SELECT — không có INSERT/UPDATE/DELETE, không sở
hữu bảng, không có quyền DDL. Khi đó, dù có yêu cầu thực thi câu lệnh ghi,
PostgreSQL sẽ từ chối bằng lỗi permission denied, độc lập với nội dung
`tools.yaml`.

Repo này không tạo hay chỉnh sửa quyền của tài khoản đó — cần xin tài khoản
read-only từ người quản trị database, tương tự quy trình cấp quyền cho bất
kỳ công cụ báo cáo chỉ-đọc nào khác.
