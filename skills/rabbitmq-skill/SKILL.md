---
name: rabbitmq-skill
description: Kiến thức chuyên sâu RabbitMQ — exchange type, routing, queue durability, dead-letter exchange, prefetch, quorum queue, priority queue. Dùng khi feature cần giao tiếp bất đồng bộ qua RabbitMQ.
---

# RabbitMQ

## Discover
Xác nhận project đã dùng RabbitMQ qua dependency (`spring-boot-starter-amqp`), đọc
exchange/queue config hiện có, đọc `api-contract-skill` nếu đã có message contract chốt
trước — dùng đúng theo đó.

## Exchange Type
- **Direct**: routing 1-1 rõ ràng theo routing key chính xác.
- **Topic**: routing theo pattern (`order.*.created`) — dùng khi nhiều consumer quan tâm
  các phần khác nhau của cùng loại event.
- **Fanout**: broadcast tới mọi queue bind vào exchange, không quan tâm routing key.
- **Headers**: routing theo header thay vì routing key — ít dùng, chỉ khi thực sự cần.

## Queue Durability & Reliability
- Queue/exchange `durable=true` cho dữ liệu quan trọng (sống sót qua restart broker).
- Message `persistent` nếu cần đảm bảo không mất khi broker crash.
- Cân nhắc **quorum queue** (thay vì classic mirrored queue) cho high-availability hiện đại
  — trình bày tradeoff nếu đổi loại queue ảnh hưởng downtime.

## Ack Strategy & Prefetch
- Manual ack nếu cần đảm bảo xử lý xong mới ack (an toàn hơn nhưng cần xử lý reject/requeue
  đúng khi lỗi).
- `prefetch count` hợp lý theo tốc độ xử lý consumer — quá cao gây 1 consumer ôm hết message
  trong khi consumer khác rảnh, quá thấp giảm throughput.

## Dead-letter Exchange (DLX)
- Cấu hình DLX + `x-dead-letter-routing-key` rõ ràng cho message bị reject/hết TTL/hết
  retry — không để message lỗi bị mất âm thầm.
- Retry có giới hạn trước khi đẩy sang DLX (tránh loop vô hạn giữa queue chính và DLX).

## Priority Queue (nếu nghiệp vụ cần xử lý ưu tiên)
`x-max-priority` khi khai báo queue — chỉ dùng khi thực sự có yêu cầu ưu tiên xử lý rõ
ràng, không thêm phức tạp không cần thiết nếu FIFO đã đủ.

## Idempotency
Consumer PHẢI idempotent nếu dùng at-least-once (mặc định phổ biến với manual ack + reject
requeue) — dùng dedup key/kiểm tra đã xử lý trước khi side-effect.

## Test
Testcontainers RabbitMQ cho integration test — test đúng ack/requeue behavior, test DLX
khi message lỗi, test idempotency khi nhận trùng.

## Ranh giới
Không tự quyết định exchange type/queue type nếu ảnh hưởng lớn tới kiến trúc hiện có —
trình bày tradeoff, đối chiếu `api-contract-skill` đã chốt.
