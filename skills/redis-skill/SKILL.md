---
name: redis-skill
description: Kiến thức chuyên sâu Redis cho nhiều use-case — caching, distributed lock, queue, ranking/leaderboard. Dùng khi feature cần cache, khóa phân tán, hàng đợi nhẹ, hoặc bảng xếp hạng.
---

# Redis — Đa dụng theo Use-case

## Discover
Xác nhận project đã dùng Redis qua dependency (`spring-boot-starter-data-redis`,
`lettuce`/`jedis`), đọc cấu hình cluster/standalone hiện có, TTL convention đang dùng.

## 1. Caching
- **Key naming**: nhất quán convention hiện có (VD: `<domain>:<entity>:<id>`).
- **TTL**: luôn đặt TTL rõ ràng cho cache — không cache vô thời hạn trừ khi có lý do rõ
  ràng và cơ chế invalidation chủ động đi kèm.
- **Invalidation strategy**: write-through (cập nhật cache ngay khi ghi DB), write-behind,
  hoặc cache-aside (invalidate khi ghi, load lại khi đọc miss) — chọn theo mức độ chấp
  nhận stale data của nghiệp vụ, trình bày tradeoff nếu ảnh hưởng lớn.
- **Cache stampede**: cân nhắc lock hoặc jitter TTL khi nhiều request cùng miss cache 1 lúc
  (tránh tất cả cùng đánh vào DB).

## 2. Distributed Lock
- Dùng `SET key value NX PX <ttl>` (hoặc thư viện Redisson) — LUÔN đặt TTL cho lock để
  tránh deadlock vĩnh viễn nếu process giữ lock crash.
- Cân nhắc thuật toán **Redlock** nếu cần lock tin cậy qua nhiều Redis instance độc lập
  (không chỉ 1 instance/cluster đơn) — chỉ dùng khi thực sự cần độ tin cậy cao, có tranh
  cãi kỹ thuật về Redlock nên cân nhắc kỹ trước khi áp dụng cho nghiệp vụ tài chính quan
  trọng.
- Giải phóng lock đúng chủ sở hữu (dùng token/value ngẫu nhiên, kiểm tra trước khi xóa —
  tránh giải phóng nhầm lock của process khác).

## 3. Queue nhẹ
- **List** (`LPUSH`/`BRPOP`) cho queue đơn giản FIFO, không cần độ tin cậy cao.
- **Redis Streams** (`XADD`/`XREADGROUP`) nếu cần consumer group, ack, replay — gần với
  Kafka hơn nhưng nhẹ hơn, phù hợp khi không muốn thêm hạ tầng Kafka/RabbitMQ mới. Nếu
  nghiệp vụ cần độ tin cậy/durability cao hơn Streams cung cấp, cân nhắc `kafka-skill`/
  `rabbitmq-skill` thay vì cố ép Redis làm queue chính.

## 4. Ranking / Leaderboard
- **Sorted Set** (`ZADD`/`ZRANGE`/`ZRANK`) — cấu trúc chuẩn cho bảng xếp hạng, tra cứu
  rank O(log N).
- Cân nhắc cập nhật điểm bằng `ZINCRBY` thay vì đọc-sửa-ghi thủ công (tránh race condition).

## Cluster & High Availability (ghi chú, không tự đổi hạ tầng)
Nếu project đã dùng Redis Cluster, lưu ý 1 số lệnh không hỗ trợ multi-key qua nhiều slot
khác nhau (dùng hash tag `{...}` nếu cần đảm bảo key liên quan cùng 1 slot).

## Test
Testcontainers Redis cho integration test — test TTL/invalidation đúng, test lock không
bị giữ vượt TTL, test sorted set trả đúng thứ hạng.

## Ranh giới
Không tự chọn use-case (cache vs lock vs queue vs ranking) thay user nếu yêu cầu không rõ
— hỏi lại mục đích cụ thể trước khi thiết kế key/cấu trúc dữ liệu Redis tương ứng.
