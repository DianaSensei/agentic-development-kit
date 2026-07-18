# Message Contract (Kafka/RabbitMQ/Pub-Sub) — chuẩn AsyncAPI

Skill này quyết định PHẦN HỢP ĐỒNG của giao tiếp bất đồng bộ. Chi tiết hạ tầng broker cụ
thể (partition, consumer group, ack mode, exchange type) thuộc về `kafka-skill`/
`rabbitmq-skill`/`pubsub-skill` khi triển khai — không quyết định ở đây.

**AsyncAPI là chuẩn bắt buộc cho message contract** — đóng vai trò tương đương OpenAPI
cho REST. Với project mới hoặc chưa có convention nào cho message contract, luôn dùng
AsyncAPI, không tự bịa format JSON rời rạc hay tài liệu mô tả tự do. Nếu project đã có
sẵn 1 convention khác đang dùng nhất quán (VD Avro schema qua Schema Registry), giữ
nguyên convention đó thay vì áp đặt AsyncAPI lên trên.

## Event Schema — viết bằng AsyncAPI 3.x
- Định nghĩa `channels` (topic/queue), `messages` (payload schema), `operations`
  (send/receive) theo đúng cấu trúc AsyncAPI 3.x — xem skeleton mẫu bên dưới.
- Payload bên trong mỗi message mô tả bằng JSON Schema — đây không phải 2 lựa chọn tách
  biệt, AsyncAPI dùng JSON Schema làm ngôn ngữ mô tả payload của chính nó.
- Naming topic/queue/exchange nhất quán convention hiện có (VD Kafka:
  `<domain>.<entity>.<event-past-tense>`, VD `order.payment.completed`).

## AsyncAPI 3.x — cấu trúc tối thiểu

```yaml
asyncapi: "3.0.0"
info:
  title: Order Events
  version: "1.0.0"
channels:
  order.payment.completed:
    address: order.payment.completed
    messages:
      PaymentCompleted:
        $ref: "#/components/messages/PaymentCompleted"
operations:
  publishPaymentCompleted:
    action: send
    channel:
      $ref: "#/channels/order.payment.completed"
    messages:
      - $ref: "#/channels/order.payment.completed/messages/PaymentCompleted"
components:
  messages:
    PaymentCompleted:
      payload:
        type: object
        required: [order_id, amount, event_version]
        properties:
          order_id:      { type: string, format: uuid }
          amount:        { type: number }
          event_version: { type: integer, default: 1 }
```

## Schema Versioning & Compatibility
- Chiến lược evolution BẮT BUỘC backward-compatible: chỉ thêm field optional, không đổi
  kiểu field cũ, không xóa field đang dùng — đây là ràng buộc cứng để tránh phá vỡ
  consumer đang chạy phiên bản cũ (consumer không được deploy đồng bộ với producer trong
  hệ bất đồng bộ).
- Nếu dùng Schema Registry (Avro/Protobuf), tuân thủ compatibility mode đã cấu hình
  (BACKWARD/FORWARD/FULL) — không tự đổi mode nếu chưa hiểu rõ tác động.
- Breaking change không tránh được → version hóa event (VD field `event_version` trong
  payload, hoặc topic mới) — không âm thầm đổi shape event cũ.

## Delivery Semantic — đây là YÊU CẦU/hợp đồng, không phải cấu hình kỹ thuật
- Xác định nghiệp vụ cần **at-least-once** (phổ biến, chấp nhận trùng, consumer phải
  idempotent) hay **exactly-once** (phức tạp hơn, chỉ dùng khi thực sự cần thiết — VD
  giao dịch tài chính không chấp nhận double-processing).
- Ghi rõ delivery semantic yêu cầu vào contract — cơ chế triển khai cụ thể (Kafka
  transaction, RabbitMQ manual ack, Pub/Sub exactly-once subscription) do skill kỹ thuật
  broker tương ứng quyết định, miễn tuân thủ đúng yêu cầu này.

## Consumer Contract (Dead-letter)
- Mô tả rõ consumer nên xử lý gì khi nhận message lỗi/không parse được: có tồn tại
  dead-letter topic/queue không, ai chịu trách nhiệm xử lý message ở đó — không đi sâu
  cấu hình broker cụ thể (retry count, backoff) ở tầng contract này.

## Chọn Broker (tham khảo nhanh, quyết định chi tiết ở skill kỹ thuật tương ứng)
- **Kafka**: throughput cao, cần replay lịch sử, nhiều consumer group độc lập.
- **RabbitMQ**: routing linh hoạt, task queue kinh điển, quy mô vừa phải.
- **Google Pub/Sub**: hạ tầng đã ở GCP, không muốn tự quản lý broker.
- Nếu project đã dùng 1 broker cụ thể, luôn thiết kế contract tương thích với broker đó
  — không đề xuất đổi broker chỉ vì lý thuyết "phù hợp hơn" nếu không có yêu cầu rõ ràng.
