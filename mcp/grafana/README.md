# Grafana MCP

Cấu hình cho [server chính thức của Grafana](https://github.com/grafana/mcp-grafana),
chạy local qua `uvx`, không yêu cầu Docker hay server riêng. Sau khi kết
nối, có thể yêu cầu Claude Code: "liệt kê dashboard hiện có", "alert nào
đang active", "CPU của service X trong một giờ qua" mà không cần mở giao
diện Grafana.

## Cài đặt

Cách cài và chạy chính thức nằm ở
[README của grafana/mcp-grafana](https://github.com/grafana/mcp-grafana#quick-start)
— tham khảo trang đó nếu gợi ý dưới đây không còn đúng. Repo này mặc định
dùng cách chạy qua `uv`/`uvx` vì đơn giản nhất, không yêu cầu Docker:

```bash
brew install uv
uvx --version
```

Nếu không dùng macOS hoặc không có Homebrew, xem hướng dẫn cài đặt `uv` tại
[docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/).
`uvx mcp-grafana` (dùng ở bước đăng ký bên dưới) luôn lấy bản phát hành mới
nhất, không cần chỉ định version.

## Tạo Service Account token

Đường dẫn thao tác trên giao diện Grafana có thể thay đổi theo phiên bản —
tham khảo
[tài liệu chính thức về Service Accounts](https://grafana.com/docs/grafana/latest/administration/service-accounts/)
nếu các bước dưới đây không khớp với giao diện bạn đang thấy.

Vào Grafana → **Administration** → **Service accounts** → **Add service
account**, đặt tên bất kỳ (ví dụ `mcp-claude-code`). Chọn role **Viewer**
nếu chỉ cần đọc dữ liệu — mức quyền an toàn hơn. Chọn Editor/Admin nếu cần
Claude Code tạo hoặc chỉnh sửa dashboard.

Vào service account vừa tạo, chọn **Add service account token**, và sao
chép token ngay lúc đó — token chỉ hiển thị một lần.

## Cấu hình `.env`

```bash
cp .env.example .env
```

| Biến | Bắt buộc | Ghi chú |
|---|---|---|
| `GRAFANA_URL` | Có | `http://localhost:3000` (tự host) hoặc `https://<instance>.grafana.net` (Cloud) |
| `GRAFANA_SERVICE_ACCOUNT_TOKEN` | Có | token vừa tạo |
| `GRAFANA_ORG_ID` | Chỉ với instance nhiều org | ID số của org |

## Đăng ký với Claude Code

```bash
set -a && source .env && set +a
claude mcp add grafana --scope user \
  --env GRAFANA_URL="$GRAFANA_URL" \
  --env GRAFANA_SERVICE_ACCOUNT_TOKEN="$GRAFANA_SERVICE_ACCOUNT_TOKEN" \
  -- uvx mcp-grafana
```

Hai dòng đầu nạp giá trị từ `.env` vào shell, dòng cuối đăng ký server và
lấy token trực tiếp từ đó — không cần nhập thủ công. `--scope user` áp dụng
cho mọi project trên máy hiện tại; nếu dùng nhiều máy, cần lặp lại các bước
này trên từng máy vì `.env` không tự đồng bộ.

Xác nhận:

```bash
claude mcp list
```

Trạng thái `✔ Connected` cạnh `grafana` là hoàn tất. Nếu thấy
`✘ Failed to connect`, kiểm tra `GRAFANA_URL` có truy cập được và token
chưa bị thu hồi.

## Kiểm tra sau khi kết nối

- "Liệt kê dashboard trên Grafana"
- "Alert nào đang active?"
- "CPU của service checkout trong một giờ qua?"

---

## Cấu hình nâng cao

**Đăng ký qua file config thay vì lệnh CLI** — phạm vi cá nhân, sửa
`~/.claude.json`. File này không lên git nên có thể ghi token thật trực
tiếp:

```json
{
  "mcpServers": {
    "grafana": {
      "type": "stdio",
      "command": "uvx",
      "args": ["mcp-grafana"],
      "env": {
        "GRAFANA_URL": "http://localhost:3000",
        "GRAFANA_SERVICE_ACCOUNT_TOKEN": "<token từ .env>"
      }
    }
  }
}
```

Chia sẻ với team, tạo `.mcp.json` ở gốc project và commit vào git. Không
được ghi token thật vào file này — dùng cú pháp `${TÊN_BIẾN}`, mỗi thành
viên tự khai báo giá trị trên máy họ:

```json
{
  "mcpServers": {
    "grafana": {
      "type": "stdio",
      "command": "uvx",
      "args": ["mcp-grafana"],
      "env": {
        "GRAFANA_URL": "${GRAFANA_URL}",
        "GRAFANA_SERVICE_ACCOUNT_TOKEN": "${GRAFANA_SERVICE_ACCOUNT_TOKEN}"
      }
    }
  }
}
```

Ghi rõ trong README/CLAUDE.md của project rằng mỗi thành viên cần chạy
`set -a && source mcp/grafana/.env && set +a` trước khi mở Claude Code.
`.mcp.json` chỉ được đọc lại khi mở phiên làm việc mới.

**Phương thức chạy khác** — Docker, hoặc chạy như HTTP server dùng chung cho
nhiều người dùng, xem [README gốc](https://github.com/grafana/mcp-grafana#usage).
Cách `uvx` ở trên là đơn giản nhất cho một người dùng, nên được dùng làm mặc
định ở đây.

**Giới hạn chỉ đọc** — Grafana MCP không có công tắc read-only riêng trong
cấu hình; quyền truy cập phụ thuộc hoàn toàn vào role của Service Account.
Để đảm bảo Claude Code không thể chỉnh sửa dashboard hay ghi annotation,
tạo Service Account với role Viewer, không cấp Editor/Admin trừ khi thực sự
cần các tool có khả năng ghi.
