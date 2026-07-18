# Atlassian MCP — Jira + Confluence tự host

Cấu hình cho [mcp-atlassian](https://github.com/sooperset/mcp-atlassian),
chạy local qua `uvx`. Sau khi kết nối, có thể yêu cầu Claude Code: "tìm
ticket đang giao cho tôi", "tóm tắt trang Confluence X" mà không cần mở
giao diện Jira/Confluence.

Cấu hình này chỉ áp dụng cho Jira/Confluence bản tự host (Server hoặc Data
Center — địa chỉ không thuộc dạng `*.atlassian.net`).

## Dùng Atlassian Cloud

Không dùng cấu hình trong thư mục này. Atlassian cung cấp MCP server chính
thức (Rovo) cho Cloud, không cần cài đặt hay quản lý token:

```bash
claude mcp add atlassian-cloud --transport http https://mcp.atlassian.com/v1/mcp
```

Nếu `claude mcp list` hiển thị `! Needs authentication`, chạy `/mcp` trong
Claude Code, chọn server này và chọn Authenticate để đăng nhập qua trình
duyệt.

---

## Cài đặt

Cách cài và chạy chính thức nằm ở
[README của sooperset/mcp-atlassian](https://github.com/sooperset/mcp-atlassian#quick-start)
— tham khảo trang đó nếu gợi ý dưới đây không còn đúng. Repo này mặc định
dùng cách chạy qua `uv`/`uvx` vì đơn giản nhất, không yêu cầu Docker:

```bash
brew install uv
uvx --version
```

Nếu không dùng macOS hoặc không có Homebrew, xem hướng dẫn cài đặt `uv` tại
[docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/).
`uvx mcp-atlassian` (dùng ở bước đăng ký bên dưới) luôn lấy bản phát hành
mới nhất, không cần chỉ định version.

## Tạo Personal Access Token

Đường dẫn thao tác trên giao diện Jira/Confluence có thể thay đổi theo
phiên bản — tham khảo
[tài liệu xác thực chính thức của mcp-atlassian](https://mcp-atlassian.soomiles.com/docs/authentication)
nếu các bước dưới đây không khớp.

Thực hiện riêng cho từng sản phẩm — Jira và Confluence dùng token khác
nhau dù chung một hệ thống: đăng nhập → avatar góc trên bên phải →
**Profile** → **Personal Access Tokens** → **Create token**. Sao chép token
ngay sau khi tạo.

Nếu chỉ dùng một trong hai sản phẩm, bỏ qua bước tạo token cho sản phẩm còn
lại.

## Cấu hình `.env`

```bash
cp .env.example .env
```

| Biến | Bắt buộc | Ghi chú |
|---|---|---|
| `JIRA_URL` | Nếu dùng Jira | ví dụ `https://jira.congty.com` |
| `JIRA_PERSONAL_TOKEN` | Nếu dùng Jira | token vừa tạo |
| `CONFLUENCE_URL` | Nếu dùng Confluence | địa chỉ Confluence |
| `CONFLUENCE_PERSONAL_TOKEN` | Nếu dùng Confluence | token vừa tạo |
| `READ_ONLY_MODE` | Không, mặc định `true` | `true` vô hiệu hoá mọi tool ghi/sửa/xoá — xem phần cuối tài liệu |
| `JIRA_PROJECTS_FILTER` / `CONFLUENCE_SPACES_FILTER` | Không | giới hạn phạm vi project/space, phân tách bằng dấu phẩy |

Sản phẩm nào không dùng có thể để trống, server sẽ tự bỏ qua.

## Đăng ký với Claude Code

Xác định đường dẫn tuyệt đối tới thư mục này (`pwd` trong thư mục này), sau
đó:

```bash
claude mcp add selfhost-atlassian --scope user -- uvx mcp-atlassian --env-file /đường-dẫn/mcp/selfhost-atlassian/.env
```

Khác với Grafana/Toolbox, server này đọc trực tiếp file `.env` qua
`--env-file` — không cần truyền token vào lệnh, chỉ cần đường dẫn chính
xác tới file.

Xác nhận:

```bash
claude mcp list
```

Trạng thái `✔ Connected` cạnh `selfhost-atlassian` là hoàn tất. Nếu lỗi,
kiểm tra URL có truy cập được và token chưa hết hạn hoặc bị thu hồi.

## Kiểm tra sau khi kết nối

- "Tìm ticket Jira đang giao cho tôi"
- "Tóm tắt trang Confluence tên X"
- "Có bug nào được tạo trong tuần này không?"

Với `READ_ONLY_MODE=true`, các yêu cầu tạo mới ticket hoặc trang sẽ bị từ
chối — xem phần bên dưới.

---

## Cấu hình nâng cao

**Đăng ký qua file config thay vì lệnh CLI** — vì `--env-file` chỉ cần một
đường dẫn thay vì giá trị trực tiếp, cách này an toàn ở mọi phạm vi, kể cả
khi chia sẻ qua git:

```json
{
  "mcpServers": {
    "selfhost-atlassian": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "mcp-atlassian",
        "--env-file", "${CLAUDE_PROJECT_DIR}/mcp/selfhost-atlassian/.env"
      ]
    }
  }
}
```

Phạm vi cá nhân: dán vào `~/.claude.json`, thay `${CLAUDE_PROJECT_DIR}`
bằng đường dẫn tuyệt đối (biến này chỉ có giá trị trong phiên làm việc gắn
với một project cụ thể). Chia sẻ với team: dán vào `.mcp.json` ở gốc
project và commit vào git, giữ nguyên `${CLAUDE_PROJECT_DIR}` — mỗi thành
viên vẫn cần tự tạo file `.env` trên máy họ.

`.mcp.json` chỉ được đọc lại khi mở phiên làm việc mới.

## Vì sao mặc định read-only

`READ_ONLY_MODE=true` vô hiệu hoá mọi tool tạo/sửa/xoá ở phía server, không
chỉ là một dòng mô tả yêu cầu Claude tránh thao tác ghi. Ngay cả khi có yêu
cầu tạo ticket, server sẽ từ chối trực tiếp, bất kể quyền hạn thực tế của
token.

Chỉ tắt read-only khi thực sự cần Claude Code tạo hoặc chỉnh sửa nội dung.
Có thể kết hợp thêm `JIRA_PROJECTS_FILTER` / `CONFLUENCE_SPACES_FILTER` để
giới hạn phạm vi truy cập, vì Personal Access Token của Atlassian thường kế
thừa toàn bộ quyền của tài khoản tạo ra nó, không tự giới hạn theo
project/space.
