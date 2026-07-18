# Agents

Bộ Claude Code subagent (`.claude/agents/*.md`, gọi qua Task tool) tạo thành 1 pipeline nhiều tầng cho
việc phát triển tính năng: Tier 1 làm rõ yêu cầu + lên phương án, Tier 2 triển khai chuyên biệt theo
từng mảng kỹ thuật. Mỗi agent nhận input/trả output theo JSON contract cố định, để agent sau dùng thẳng
không cần suy đoán lại.

> **Khác với `skills/`**: thư mục này là 1 hệ thống multi-agent riêng (nhiều Task subagent tách biệt,
> nói chuyện với nhau qua JSON), độc lập với `skills/` (thư viện skill dùng trong 1 agent duy nhất qua
> Skill tool). Hai thư mục hiện KHÔNG tham chiếu lẫn nhau.

## Pipeline

```
business-analyst  →  solution-architect  →  Tier-2 specialist(s), theo task_breakdown
   (Tier 1)              (Tier 1)              (song song hoặc tuần tự, tùy dependency)
```

| Bước | Agent | Vai trò |
|------|-------|---------|
| 1 | [`business-analyst`](./business-analyst.md) | Đọc hiện trạng, làm rõ yêu cầu, đánh giá tính khả thi. Hoàn toàn agnostic — không biết/không cần biết stack. Output: draft AC/Edge Case/DoD + impact assessment sơ bộ. |
| 2 | [`solution-architect`](./solution-architect.md) | Nhận output của Bước 1, xác định stack (`CLAUDE.md` → memory/MCP → bằng chứng code), đưa 1+ proposal đầy đủ diagram/tradeoff/AC-DoD đã chốt + `task_breakdown` gán việc cho đúng Tier-2 agent. KHÔNG viết code, KHÔNG chốt schema/công nghệ lưu trữ cụ thể. |
| 3 | Tier-2 specialist(s) | Mỗi agent trong `task_breakdown` triển khai đúng phần việc được gán, có thể chạy song song nếu không phụ thuộc nhau (`can_run_parallel_with`). |

`solution-architect` **không dùng danh sách tên agent cố định** — nó tự đọc `agents/*.md` (Bước 0.5
trong file của nó) để biết Tier-2 agent nào đang thực sự tồn tại và mô tả làm gì, rồi mới gán việc.
Nghĩa là thêm 1 Tier-2 agent mới vào thư mục này không cần sửa `solution-architect.md`.

## Tier-2 Specialists Hiện Có

| Agent | Chuyên trách | Gọi sau |
|-------|--------------|---------|
| [`api-spec-designer`](./api-spec-designer.md) | Contract API — REST (OpenAPI) đồng bộ + message contract (Kafka/RabbitMQ/Pub-Sub, kiểu AsyncAPI) bất đồng bộ. Chỉ ra contract, không implement server/broker. | `solution-architect` |
| [`data-storage-architect`](./data-storage-architect.md) | Thiết kế data storage cho MỌI công nghệ (Oracle/PostgreSQL/MySQL/Redis/MongoDB/Elasticsearch/SQLite local). Tự phát hiện công nghệ đang dùng, luôn trình bày tradeoff, không tự quyết. | `solution-architect` |
| [`java-ecosystem-engineer`](./java-ecosystem-engineer.md) | Implement + tự test business/functional flow Java Spring Boot (MVC/WebFlux, Spring Data, Security, Kafka, RabbitMQ, resilience). | `data-storage-architect` + `api-spec-designer` (nếu áp dụng) |
| [`tauri-react-engineer`](./tauri-react-engineer.md) | Implement + tự test Tauri (Rust command) + React (UI) cho desktop app cross-platform. | `data-storage-architect` (nếu cần persisted data) + `api-spec-designer` (nếu áp dụng) |

Mỗi agent implement (Tier 2) đều tự viết VÀ tự chạy test cho phần mình làm trước khi báo hoàn thành,
không để lại việc verify cho bước sau.

## Quy ước chung

- **JSON output có cấu trúc** — mỗi agent trả 1 JSON object theo schema cố định trong file của nó, để
  agent/bước sau dùng thẳng, không phải parse lại văn bản tự do.
- **`checkpoint`** — hầu hết output có field `checkpoint` (`required`, `type`, `summary`) đánh dấu rõ
  khi nào cần dừng lại chờ user xác nhận (VD: chọn 1 trong nhiều proposal của `solution-architect`)
  trước khi đi tiếp.
- **`context_sources_used` / `provenance`** — agent luôn ghi rõ thông tin lấy từ đâu (CLAUDE.md, memory/
  MCP, hay đọc code) để bước sau biết độ tin cậy, không coi mọi input như đã được xác nhận chắc chắn.
- **Tier 1 không phụ thuộc stack, Tier 2 thì có** — `business-analyst` cố tình được thiết kế hoàn toàn
  agnostic (dùng được cho mọi loại project); từ `solution-architect` trở đi mới cần xác định stack cụ
  thể để route đúng specialist.
- **Mỗi proposal của `solution-architect` phải tự đủ (self-contained)** — vì agent này chỉ chạy 1 lần
  trong luồng bình thường, sau khi user chọn 1 proposal thì lead-agent dùng thẳng AC/Edge Case/DoD/
  task_breakdown của đúng proposal đó, không gọi lại `solution-architect` để hỏi thêm.
