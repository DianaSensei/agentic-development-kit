---
name: kafka-skill
description: Kiến thức chuyên sâu Apache Kafka — thiết kế topic/partition, consumer group, delivery semantics, idempotency, schema evolution, dead-letter, monitoring lag. Dùng khi feature cần giao tiếp bất đồng bộ qua Kafka.
---

# Apache Kafka

## Discover
Xác nhận project đã dùng Kafka qua dependency (`spring-kafka`, client library tương ứng),
đọc topic/config hiện có, đọc `api-contract-skill` nếu đã có message contract được chốt
trước (schema, tên topic, delivery semantic yêu cầu) — dùng đúng theo đó, không tự đổi.

## Thiết kế Topic & Partition
- Naming nhất quán convention hiện có (VD: `<domain>.<entity>.<event-past-tense>`).
- Partition key: chọn key đảm bảo message liên quan cùng 1 entity vào cùng partition (giữ
  thứ tự xử lý đúng theo entity đó) — KHÔNG chọn key ngẫu nhiên nếu thứ tự quan trọng.
- Số partition: cân nhắc throughput cần và số consumer instance dự kiến (partition là đơn
  vị song song hóa tối đa) — trình bày tradeoff nếu đây là quyết định ảnh hưởng lớn (khó
  giảm partition sau khi đã tăng).

## Consumer Group & Rebalancing
- Consumer group name rõ ràng theo service tiêu thụ, không dùng chung group cho nhiều
  service không liên quan (gây cạnh tranh message sai ý).
- Cân nhắc `max.poll.records`/`session.timeout.ms` nếu xử lý message chậm gây rebalance
  liên tục — không tự đổi config production mà không đo trước.

## Delivery Semantics & Idempotency
- At-least-once (phổ biến nhất): consumer PHẢI idempotent (dùng dedup key/kiểm tra đã xử
  lý chưa trước khi thực hiện side-effect).
- Exactly-once: dùng Kafka transactions (`transactional.id`, `isolation.level=read_committed`)
  nếu cần — chi phí phức tạp hơn, chỉ dùng khi thực sự cần thiết, nêu tradeoff.
- Producer: `acks=all` + `enable.idempotence=true` nếu cần đảm bảo không mất/trùng message
  ở phía producer.

## Schema Evolution
- Backward-compatible bắt buộc: chỉ thêm field optional, không đổi kiểu/xóa field đang
  dùng (nếu dùng Schema Registry + Avro/Protobuf, tuân thủ compatibility mode đã cấu hình).
- Version hóa event nếu breaking change không tránh được — không âm thầm đổi shape event
  cũ.

## Dead-letter & Error Handling
- Định nghĩa rõ dead-letter topic khi message xử lý lỗi (không retry vô hạn tại chỗ).
- `SeekToCurrentErrorHandler`/`DefaultErrorHandler` (Spring Kafka) với retry có giới hạn
  trước khi đẩy sang DLT.

## Monitoring cần lưu ý (ghi chú, không tự implement dashboard)
Consumer lag là chỉ số quan trọng nhất — ghi chú trong output nếu feature có khả năng gây
lag cao (xử lý chậm hơn tốc độ produce), để user cân nhắc scale consumer.

## Test
Testcontainers Kafka cho integration test — test đúng delivery semantic đã implement, test
idempotency khi consume trùng message, test dead-letter khi xử lý lỗi. Unit test business
logic thuần túy xem `java-spring-skill`.

## Ranh giới
Không tự quyết định partition count/delivery semantic nếu đây là lần đầu thiết kế — trình
bày tradeoff, chờ user hoặc đối chiếu `api-contract-skill` đã chốt trước.
