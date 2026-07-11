---
name: redis-skill
description: Kiến thức chuyên sâu Redis cho nhiều use-case — caching, distributed lock, queue, ranking/leaderboard. Dùng khi feature cần cache, khóa phân tán, hàng đợi nhẹ, hoặc bảng xếp hạng.
---

# Redis — Đa dụng theo Use-case

## Discover
Xác nhận project đã dùng Redis qua dependency (`spring-boot-starter-data-redis`,
`lettuce`/`jedis`), đọc cấu hình cluster/standalone hiện có, TTL convention đang dùng.

## Khi nào phù hợp / KHÔNG phù hợp
Phù hợp: cache, session, distributed lock ngắn hạn, queue nhẹ chấp nhận mất mát tối thiểu,
leaderboard/counter tốc độ cao. **KHÔNG phù hợp** làm nguồn dữ liệu chính (source of truth)
cho dữ liệu quan trọng cần durability mạnh — kể cả bật AOF/RDB, Redis vẫn "best-effort":
RDB mất dữ liệu giữa 2 lần snapshot, AOF (`appendfsync everysec`, mặc định) có thể mất tới
~1s dữ liệu nếu crash. Nếu nghiệp vụ không chấp nhận mất dữ liệu này, dữ liệu đó phải nằm ở
RDBMS (`database-skill`), Redis chỉ nên là cache/tăng tốc phía trên.

## Issue thường gặp trong thực tế
- **Big key**: hash/set/sorted set quá lớn (hàng trăm nghìn field/member) làm block event
  loop đơn luồng của Redis khi thao tác trên nó (VD: `KEYS *`, `DEL` trên key lớn) — dùng
  `SCAN` thay `KEYS`, `UNLINK` thay `DEL` (xóa bất đồng bộ, không block).
- **Hot key**: 1 key bị truy cập cực nhiều (viral) dồn tải vào đúng 1 node dù cluster có
  nhiều node (do key chỉ thuộc 1 slot) — cân nhắc cache tầng ứng dụng phía trước hoặc tách
  nhỏ key nếu gặp tình huống này.
- **Eviction policy sai**: khi đạt `maxmemory`, policy (`allkeys-lru`/`volatile-ttl`/...)
  quyết định key nào bị xóa trước — chọn `allkeys-lru` mà có key quan trọng KHÔNG đặt TTL
  sẽ khiến key đó có thể bị evict ngoài ý muốn; chọn `volatile-*` nếu cần bảo vệ key không
  TTL khỏi bị evict.
- **Pub/Sub (kênh `PUBLISH`/`SUBSCRIBE`, khác Streams)**: KHÔNG có persistence — subscriber
  offline lúc publish sẽ mất message vĩnh viễn, không phù hợp nếu cần đảm bảo nhận đủ (dùng
  Streams nếu cần durability + replay).

## 1. Caching
- **Key naming**: nhất quán convention hiện có (VD: `<domain>:<entity>:<id>`).
- **TTL**: luôn đặt TTL rõ ràng cho cache — không cache vô thời hạn trừ khi có lý do rõ
  ràng và cơ chế invalidation chủ động đi kèm.
- **Invalidation strategy**: write-through (cập nhật cache ngay khi ghi DB), write-behind,
  hoặc cache-aside (invalidate khi ghi, load lại khi đọc miss) — tự chọn theo mức độ chấp
  nhận stale data của nghiệp vụ (mặc định cache-aside nếu không có tín hiệu khác, đơn giản
  và an toàn nhất), nêu ngắn gọn lý do đã chọn. Chỉ hỏi lại nếu cache này phục vụ dữ liệu
  nhạy cảm mà stale data có thể gây hậu quả nghiệp vụ nghiêm trọng (giá/tồn kho/số dư).
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
Nếu yêu cầu đã đủ rõ mục đích (VD: "cache kết quả API X", "khóa để tránh xử lý trùng
đơn hàng") — tự suy ra use-case tương ứng (cache/lock/queue/ranking) và chọn cấu trúc dữ
liệu Redis phù hợp mà không cần hỏi lại. Chỉ hỏi lại khi mô tả quá mơ hồ để suy luận đúng
use-case (VD: "lưu tạm dữ liệu này vào Redis" không rõ có cần TTL, có cần đọc lại theo
thứ tự, hay chỉ cần tồn tại tạm thời).
