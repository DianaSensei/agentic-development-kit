---
name: api-contract-skill
description: Kiến thức chuyên sâu thiết kế contract API — REST (OpenAPI 3.x), RPC (gRPC/Protobuf), và message contract bất đồng bộ (Kafka/RabbitMQ/Pub-Sub, AsyncAPI). Bao gồm nguyên tắc thiết kế, bảo mật (OWASP API Security Top 10), naming/versioning. Dùng trước khi implement, để chốt hợp đồng giao tiếp.
---

# API & Message Contract Design (REST / RPC / Message)

## Discover

Đọc contract hiện có (OpenAPI/proto file/AsyncAPI nếu có), convention naming/versioning/
auth hiện tại. Xác định loại giao tiếp cần thiết kế: đồng bộ (REST hoặc RPC) hay bất đồng
bộ (message qua `kafka-skill`/`rabbitmq-skill`/`pubsub-skill`).

## REST (OpenAPI 3.x)

HTTP verb đúng ngữ nghĩa, resource-oriented URL, status code đúng ngữ cảnh. Pagination/
filtering/sorting nhất quán. Error schema chuẩn hóa dùng chung toàn API. Versioning theo
chiến lược đã có (URL path/header).

## RPC (gRPC/Protobuf)

- Dùng khi cần hiệu năng cao, giao tiếp service-to-service nội bộ, hoặc streaming (server/
  client/bidirectional streaming) — KHÔNG phù hợp cho public API hướng browser trực tiếp
  (cần proxy như grpc-web nếu vậy).
- Thiết kế `.proto`: field number KHÔNG được đổi/tái sử dụng sau khi đã publish (breaking
  change nghiêm trọng) — chỉ thêm field mới với số field mới, đánh dấu `reserved` cho field
  đã xóa.
- Versioning: đóng gói version vào package name (`com.example.orderv1`) nếu cần breaking
  change, không cố nhồi backward-compat vào cùng 1 message nếu thay đổi quá lớn.
- Deadline/timeout: luôn set deadline phía client, tránh chờ vô hạn khi service downstream
  chậm/treo.

## So sánh nhanh REST vs RPC (tự chọn theo ngữ cảnh, trừ khi ảnh hưởng lớn)

- REST: dễ debug (curl/browser), phù hợp public API, cache HTTP tự nhiên.
- RPC: nhanh hơn (binary + HTTP/2), type-safe qua codegen, phù hợp nội bộ nhiều service.
- Tự chọn phương án phù hợp nhất theo ngữ cảnh hiện có (public-facing → REST, nội bộ
  service-to-service hiệu năng cao → RPC), nêu ngắn gọn lý do đã chọn trong báo cáo. Chỉ
  dừng lại hỏi user nếu đây là quyết định ảnh hưởng NHIỀU service đang chạy production
  (đổi giao thức giao tiếp giữa các service đã tồn tại) — vì đó là thay đổi kiến trúc khó
  đảo ngược, không phải lựa chọn cục bộ cho 1 endpoint/service mới.

## Bảo mật (OWASP API Security Top 10 — áp dụng cả REST lẫn RPC)

Khai báo scheme xác thực/phân quyền rõ theo endpoint/method. Validate input chặt (type/
format/min-max/pattern, hoặc field constraint trong `.proto`). Tránh over-fetching trong
response. `Idempotency-Key` cho REST endpoint không idempotent tự nhiên nếu cần. Ghi chú
rate-limit nếu có nguy cơ lạm dụng.

## Message Contract (Kafka/RabbitMQ/Pub-Sub)

- Event schema (JSON Schema hoặc AsyncAPI), naming topic/queue nhất quán, chiến lược
  versioning backward-compatible (chỉ thêm field optional). Delivery semantic **yêu cầu**
  (at-least-once/exactly-once) — đây là hợp đồng, cơ chế cụ thể triển khai thuộc về
  `kafka-skill`/`rabbitmq-skill`/`pubsub-skill` tương ứng.
- Dead-letter contract: có tồn tại dead-letter topic/queue không, ai xử lý.

## Output BẮT BUỘC — phải ghi ra FILE THẬT, không chỉ áp dụng ngầm khi code

Đây là bước THIẾT KẾ CONTRACT, phải tạo ra 1 artifact cụ thể TRƯỚC khi bắt đầu code — không được coi đây chỉ là nguyên tắc ghi nhớ trong đầu rồi code thẳng vào Controller/Producer.

1. **REST**: nếu project đã có file OpenAPI (`openapi.yaml`/`.json`, hoặc dùng springdoc
   tự sinh từ annotation), cập nhật/bổ sung đúng path/schema liên quan vào đó. Nếu project
   CHƯA có file OpenAPI tập trung, tạo mới `docs/api/<feature-slug>.openapi.yaml` chứa
   fragment của endpoint đang thiết kế.
2. **Message contract (Kafka/RabbitMQ/Pub-Sub)**: LUÔN ghi ra
   `docs/api/<feature-slug>.asyncapi.yaml` (hoặc file tương đương) mô tả event schema,
   channel/topic name, delivery semantic yêu cầu — kể cả khi project không có convention
   AsyncAPI sẵn, đây là tài liệu SỐNG (living doc) để lần sau đối chiếu, không phải chỉ
   annotation trong ngoặc ở task list.
3. Sau khi ghi file, liệt kê rõ đường dẫn file đã tạo/cập nhật vào phần báo cáo — để lead-
   agent (hoặc `feature-development`/`bug-fix`) biết đây là 1 file thật đã thay đổi, đưa
   vào danh sách "File đã thay đổi" ở báo cáo cuối.

Nếu 1 task chỉ thêm 1 endpoint/event rất nhỏ và project chưa có convention tập trung file
contract — vẫn PHẢI tạo file nhỏ tương ứng, không bỏ qua bước này chỉ vì "đơn giản quá
không cần file riêng".

## Ranh giới

Skill này quyết định: shape dữ liệu, tên endpoint/method/topic, semantic yêu cầu,
versioning. KHÔNG quyết định: chi tiết hạ tầng broker (partition, consumer group, ack
mode) — thuộc skill kỹ thuật broker tương ứng. Nếu có nhiều cách thiết kế hợp lý cho 1
contract MỚI (chưa có consumer/producer nào phụ thuộc) — tự chọn phương án tốt nhất theo
tiêu chí rõ ràng (đơn giản, nhất quán convention hiện có, ít breaking change nhất) và nêu
lý do trong báo cáo. Chỉ hỏi lại user khi contract đã có bên tiêu thụ thực tế và thay đổi
sẽ breaking, hoặc khi yêu cầu gốc mơ hồ tới mức không thể suy luận đúng ý định nghiệp vụ.
