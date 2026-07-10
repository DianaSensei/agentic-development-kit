---
name: pubsub-skill
description: Kiến thức chuyên sâu Google Cloud Pub/Sub — topic/subscription, push vs pull, ack deadline, ordering key, dead-letter topic, exactly-once delivery. Dùng khi feature cần giao tiếp bất đồng bộ qua Google Pub/Sub.
---

# Google Cloud Pub/Sub

## Discover
Xác nhận project đã dùng Pub/Sub qua dependency (`spring-cloud-gcp-starter-pubsub` hoặc
client library GCP), đọc topic/subscription config hiện có, đọc `api-contract-skill` nếu
đã có message contract chốt trước.

## Topic & Subscription
- 1 topic có thể có nhiều subscription độc lập (mỗi subscription nhận đủ mọi message —
  khác Kafka consumer group cùng chia nhau message trong 1 group).
- Naming nhất quán convention hiện có.

## Push vs Pull
- **Pull**: subscriber tự chủ động lấy message (phù hợp khi cần kiểm soát tốc độ xử lý,
  batch xử lý) — dùng phổ biến cho backend service.
- **Push**: Pub/Sub tự gọi HTTP endpoint của bạn — phù hợp serverless (Cloud Run/Functions),
  cần endpoint public/authenticated đúng cách (OIDC token verify).
- Chọn theo hạ tầng hiện có, không tự đổi mô hình nếu ảnh hưởng lớn tới deploy.

## Ack Deadline & Retry
- Ack deadline mặc định ngắn (thường 10s) — nếu xử lý lâu hơn, PHẢI extend deadline
  (`modifyAckDeadline`) hoặc cấu hình deadline dài hơn, nếu không message sẽ bị redeliver
  dù đang xử lý dở (gây trùng xử lý nếu không idempotent).
- Retry policy: cấu hình exponential backoff thay vì để mặc định redeliver ngay lập tức
  khi nack.

## Ordering Key
Nếu cần đảm bảo thứ tự xử lý theo entity — dùng `ordering key` (yêu cầu bật ordering trên
subscription), tương tự vai trò partition key của Kafka nhưng cơ chế khác (Pub/Sub đảm bảo
thứ tự trong cùng ordering key, không phải theo partition vật lý).

## Dead-letter Topic
Cấu hình dead-letter topic + `maxDeliveryAttempts` — sau số lần nack nhất định, message
tự động chuyển sang dead-letter topic thay vì retry vô hạn.

## Exactly-once Delivery
Pub/Sub hỗ trợ exactly-once delivery ở mức subscription (cấu hình riêng) — nhưng vẫn cần
consumer idempotent cho các trường hợp edge case (duplicate do publisher retry) trừ khi
đã dùng thêm cơ chế dedup phía publisher.

## Idempotency
Mặc định coi là at-least-once trừ khi đã bật exactly-once — consumer luôn nên có dedup
key/kiểm tra đã xử lý trước khi side-effect, an toàn nhất quán bất kể cấu hình.

## Test
Dùng Pub/Sub emulator (GCP cung cấp) cho integration test local — test ack/nack behavior,
test dead-letter khi vượt maxDeliveryAttempts, test idempotency khi nhận trùng.

## Ranh giới
Không tự chọn push/pull hay bật ordering/exactly-once nếu ảnh hưởng lớn tới hạ tầng —
trình bày tradeoff, đối chiếu `api-contract-skill` đã chốt.
