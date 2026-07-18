# Common MCP Server

Kho cấu hình MCP để kết nối Claude Code với các hệ thống bên ngoài: database,
Grafana, Jira/Confluence. Mỗi thư mục trong `mcp/` là một MCP server độc
lập, không phụ thuộc lẫn nhau.

MCP (Model Context Protocol) là cơ chế cho phép Claude Code gọi ra ngoài
phạm vi code trong máy — query database, đọc dashboard, thao tác ticket —
thông qua các MCP server đóng vai trò cầu nối tới từng hệ thống cụ thể.

## Danh sách MCP server

| Thư mục | Chức năng |
|---|---|
| [`mcp/toolbox/`](./mcp/toolbox/README.md) | Query PostgreSQL, Redis, MongoDB (chỉ đọc) |
| [`mcp/grafana/`](./mcp/grafana/README.md) | Xem dashboard, alert, metric trên Grafana |
| [`mcp/selfhost-atlassian/`](./mcp/selfhost-atlassian/README.md) | Jira và Confluence bản tự host. Dùng Atlassian Cloud thì không cần cấu hình này — xem ghi chú trong README tương ứng |

## Quy trình setup chung

1. Cài công cụ runtime cần thiết cho MCP server đó (mỗi README nêu cụ thể).
2. `cp .env.example .env`, điền thông tin thật vào `.env`. File này không
   được commit lên git, nên điền giá trị thật vào là an toàn.
3. Đăng ký với Claude Code bằng lệnh `claude mcp add ...` — lệnh đầy đủ có
   sẵn trong README của từng server.
4. Chạy `claude mcp list`, xác nhận trạng thái `✔ Connected`.

Chi tiết từng bước, cách xử lý lỗi thường gặp nằm trong README riêng của
từng MCP server. Cũng có thể yêu cầu Claude Code tự thực hiện toàn bộ quy
trình — ví dụ "setup giúp tôi MCP Grafana" — Claude Code sẽ đọc README tương
ứng và làm theo.
