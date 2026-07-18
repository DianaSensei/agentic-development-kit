# Agentic Development Kit

Bộ cấu hình Claude Code cho phát triển phần mềm có hỗ trợ AI: 1 thư viện skill dùng trong 1 agent duy
nhất, 1 pipeline multi-agent theo tầng, và cấu hình MCP để Claude Code kết nối ra ngoài phạm vi code
(database, dashboard, ticket tracker). Dùng cho bất kỳ project/stack nào — phần lõi (workflow, quy
trình) không phụ thuộc công nghệ cụ thể, chi tiết công nghệ nằm ở các module riêng.

## Cấu trúc thư mục

| Thư mục | Là gì | Xem thêm |
|---|---|---|
| [`skills/`](./skills/README.md) | Thư viện 28 Claude Code Skill — workflow (feature/bug-fix/refactor), kiến thức kỹ thuật theo ngôn ngữ/hạ tầng, chất lượng/bảo mật, tích hợp MCP. Claude Code tự nhận diện skill phù hợp qua `description`, không cần gọi tay (trừ vài skill đánh dấu manual-only). | [`skills/README.md`](./skills/README.md) |
| [`agents/`](./agents/README.md) | Pipeline Task subagent nhiều tầng (Tier 1 làm rõ yêu cầu + lên phương án, Tier 2 triển khai chuyên biệt), nói chuyện với nhau qua JSON contract cố định. | [`agents/README.md`](./agents/README.md) |
| [`mcp/`](./mcp/README.md) | Cấu hình MCP server để Claude Code kết nối hệ thống ngoài: database (PostgreSQL/Redis/MongoDB, chỉ đọc), Grafana, Jira/Confluence tự host. | [`mcp/README.md`](./mcp/README.md) |

## `skills/` và `agents/` khác nhau thế nào?

Hai hệ thống này **độc lập, hiện chưa tham chiếu lẫn nhau** — cả hai đều nhắm tới việc phát triển tính
năng có cấu trúc, nhưng theo 2 mô hình khác nhau:

- **`skills/`** — 1 agent (phiên Claude Code hiện tại) tự đọc skill phù hợp và làm toàn bộ việc trong
  cùng 1 phiên, tuần tự. Bắt đầu từ `workflow-router` (skill), phân loại yêu cầu rồi chuyển cho
  `feature-development`/`bug-fix`/`refactor`, các skill này tự đọc thêm skill kỹ thuật (`java-spring-
  skill`, `database-skill`...) khi cần.
- **`agents/`** — nhiều Task subagent tách biệt, mỗi agent 1 vai trò cố định (`business-analyst` →
  `solution-architect` → Tier-2 specialist), input/output là JSON có schema rõ ràng, cho phép chạy song
  song nhiều Tier-2 agent không phụ thuộc nhau.

Dùng cái nào tùy tình huống — `skills/` phù hợp khi muốn 1 luồng liền mạch, dễ theo dõi trong 1 phiên;
`agents/` phù hợp khi muốn tách rõ trách nhiệm từng vai trò và có thể chạy song song nhiều phần việc độc
lập.

## Bắt đầu nhanh

1. **Skill**: không cần setup gì thêm — mở Claude Code trong repo này, mô tả yêu cầu, `workflow-router`
   sẽ tự nhận diện và điều phối. Xem danh sách đầy đủ tại [`skills/README.md`](./skills/README.md).
2. **Agent**: gọi trực tiếp qua Task tool, bắt đầu từ `business-analyst` cho yêu cầu mới. Xem
   [`agents/README.md`](./agents/README.md) để biết thứ tự và schema input/output từng agent.
3. **MCP**: nếu cần Claude Code truy cập database/Grafana/Jira-Confluence, làm theo
   [`mcp/README.md`](./mcp/README.md) — hoặc yêu cầu thẳng "setup giúp tôi MCP Grafana", Claude Code sẽ
   tự đọc README tương ứng và làm theo (hoặc dùng skill `mcp-setup` cho MCP server khác không có sẵn ở
   đây).

## Quy ước chung

- Phần điều phối/workflow (trong cả `skills/` và `agents/`) được thiết kế để không phụ thuộc ngôn ngữ/
  framework cụ thể — mọi chi tiết công nghệ nằm ở các module chuyên biệt (skill kỹ thuật hoặc Tier-2
  agent), tự nhận diện qua bằng chứng thật (dependency, cấu hình, code hiện có), không giả định trước.
- Thay đổi ảnh hưởng hành vi bên ngoài (feature mới, sửa lỗi) luôn có checkpoint chờ user xác nhận
  trước khi thực thi; refactor thuần cấu trúc bắt buộc giữ nguyên 100% hành vi quan sát được.
- File bí mật/credential không commit vào repo — xem từng `README.md` trong `mcp/*/` về cách dùng
  `.env` (không track bởi git).
