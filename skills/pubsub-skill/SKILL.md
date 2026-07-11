---
name: pubsub-skill
description: Kiến thức chuyên sâu Google Cloud Pub/Sub — topic/subscription, push vs pull, ack deadline, ordering key, dead-letter topic, exactly-once delivery. Dùng khi feature cần giao tiếp bất đồng bộ qua Google Pub/Sub.
---

# Google Cloud Pub/Sub

## Discover
Xác nhận project đã dùng Pub/Sub qua dependency (`spring-cloud-gcp-starter-pubsub` hoặc
client library GCP), đọc topic/subscription config hiện có, đọc `api-contract-skill` nếu
đã có message contract chốt trước.

## Khi nào phù hợp
Phù hợp nếu hạ tầng đã ở GCP — không phải quản lý broker (fully managed), tự scale theo tải,
tích hợp tốt với Cloud Run/Functions/Dataflow. Nếu multi-cloud/on-prem, hoặc cần routing
phức tạp như RabbitMQ, cân nhắc kỹ trước khi khóa vào Pub/Sub (vendor lock-in GCP).

## Issue thường gặp trong thực tế
- **Ordering key vẫn có thể nghẽn**: Pub/Sub xử lý tuần tự trong cùng 1 ordering key (tương
  tự tinh thần partition Kafka nhưng đơn vị khác) — nếu 1 key quá "hot" (nhận traffic vượt
  trội), throughput của key đó vẫn bị giới hạn dù các key khác vẫn chạy song song bình thường.
- **Quota theo project GCP**: publish/subscribe throughput, số subscription/topic đều có
  quota mặc định — cần kiểm tra quota trước khi thiết kế traffic lớn, không chỉ tin vào
  "serverless nên tự scale vô hạn".
- **Duplicate vẫn xảy ra dù bật exactly-once**: nếu subscriber crash SAU khi xử lý xong
  side-effect nhưng TRƯỚC khi ack, Pub/Sub sẽ redeliver — exactly-once của Pub/Sub đảm bảo
  không duplicate ở tầng nhận message, không đảm bảo side-effect chỉ chạy đúng 1 lần; vẫn
  cần idempotent thực sự nếu side-effect quan trọng (giao dịch tài chính).

## Topic & Subscription
- 1 topic có thể có nhiều subscription độc lập (mỗi subscription nhận đủ mọi message —
  khác Kafka consumer group cùng chia nhau message trong 1 group).
- Naming nhất quán convention hiện có.

## Push vs Pull
- **Pull**: subscriber tự chủ động lấy message (phù hợp khi cần kiểm soát tốc độ xử lý,
  batch xử lý) — dùng phổ biến cho backend service.
- **Push**: Pub/Sub tự gọi HTTP endpoint của bạn — phù hợp serverless (Cloud Run/Functions),
  cần endpoint public/authenticated đúng cách (OIDC token verify).
- Với subscription MỚI, tự chọn push hoặc pull theo hạ tầng deploy hiện có (serverless →
  push, backend service tự quản lý tốc độ xử lý → pull) và nêu lý do. Chỉ hỏi lại khi đổi
  mô hình của 1 subscription ĐANG CHẠY (ảnh hưởng cấu hình deploy/endpoint đang phục vụ
  traffic thật).

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
Với topic/subscription MỚI, tự chọn push/pull và có bật ordering/exactly-once hay không
theo yêu cầu đã mô tả (đối chiếu `api-contract-skill` nếu đã chốt), nêu lý do trong báo
cáo. Chỉ trình bày tradeoff và chờ user khi thay đổi ảnh hưởng subscription ĐANG CHẠY
production hoặc yêu cầu không đủ rõ để suy luận (VD: không rõ có cần đảm bảo thứ tự).
