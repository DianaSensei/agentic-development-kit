# So sánh giao thức — REST vs GraphQL vs RPC vs Message

Chọn đúng giao thức cho ĐÚNG loại giao tiếp — sai lựa chọn ở đây khó sửa sau vì nhiều
client/consumer sẽ phụ thuộc vào nó.

## REST (OpenAPI)
- Phù hợp: public API, API hướng browser trực tiếp, cần cache HTTP tự nhiên (GET
  cacheable), client đa dạng không kiểm soát được (mobile, third-party).
- Ưu điểm: dễ debug (curl/browser), tooling phổ biến, HTTP semantic quen thuộc.
- Nhược điểm: over-fetching/under-fetching (client phải gọi nhiều endpoint hoặc nhận dư
  field), versioning phải quản lý thủ công qua URL/header.

## GraphQL
- Phù hợp: client cần linh hoạt chọn field trả về (mobile muốn ít field hơn web), nhiều
  loại client với nhu cầu dữ liệu khác nhau cho CÙNG 1 domain, tránh over-fetching.
- Ưu điểm: 1 endpoint, schema tự mô tả (self-documenting), versioning qua deprecation
  field thay vì URL.
- Nhược điểm: cache HTTP không tự nhiên như REST (cần cache tầng ứng dụng/persisted
  query), rủi ro N+1 ở tầng resolver nếu không cẩn thận, phức tạp hơn để bảo mật đúng
  (rate-limit theo query complexity, không phải theo request count).

## RPC (gRPC/Protobuf)
- Phù hợp: giao tiếp service-to-service NỘI BỘ cần hiệu năng cao, streaming (server/
  client/bidirectional), type-safe qua codegen giữa các service cùng hệ sinh thái.
- Ưu điểm: nhanh hơn REST (binary + HTTP/2 multiplexing), hợp đồng chặt chẽ qua `.proto`.
- Nhược điểm: KHÔNG phù hợp cho public API hướng browser trực tiếp (cần proxy như
  grpc-web), khó debug bằng tay hơn REST (cần tool riêng như `grpcurl`).

## Message (Kafka/RabbitMQ/Pub-Sub)
- Phù hợp: giao tiếp BẤT ĐỒNG BỘ — không cần response ngay, cần decouple producer/
  consumer, cần khả năng retry/replay, 1-nhiều consumer cùng quan tâm 1 sự kiện.
- Không phù hợp: cần response ngay trong cùng request (dùng REST/RPC), luồng nghiệp vụ
  yêu cầu tính nhất quán mạnh ngay lập tức (dùng transaction đồng bộ).
- Xem `references/message-contract.md` để chọn đúng broker (Kafka vs RabbitMQ vs Pub/Sub)
  — quyết định đó nằm ở skill kỹ thuật broker tương ứng, không phải skill này.

## Quy tắc quyết định nhanh
1. Cần response ngay + public/browser-facing → **REST**.
2. Cần response ngay + client cần linh hoạt field/nhiều loại client khác nhau → **GraphQL**.
3. Cần response ngay + nội bộ service-to-service + hiệu năng cao → **RPC**.
4. KHÔNG cần response ngay, cần decouple/replay/nhiều consumer → **Message**.

Nếu 1 nhu cầu có thể hợp lý theo nhiều hướng — tự chọn theo quy tắc trên và nêu lý do
ngắn gọn trong báo cáo, không cần hỏi trừ khi đây là quyết định ảnh hưởng nhiều service
đang chạy production (đổi giao thức giao tiếp giữa các service đã tồn tại).
