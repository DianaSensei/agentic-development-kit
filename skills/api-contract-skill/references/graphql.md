# GraphQL

## Schema-first
- Định nghĩa type, query, mutation TRƯỚC khi viết resolver — schema chính là contract.
  Naming: PascalCase cho type (`User`, `OrderInput`), camelCase cho field/argument.
- Phân tách rõ `Query` (đọc), `Mutation` (ghi), `Subscription` (real-time nếu cần) —
  không nhét action ghi dữ liệu vào Query.

## Input & Validation
- Dùng input type riêng cho mutation (`CreateUserInput`) thay vì liệt kê argument rời
  rạc — dễ mở rộng sau này (thêm field vào input type không breaking).
- Ràng buộc qua custom scalar (VD `Email`, `PositiveInt`) khi có thể, để schema tự
  validate thay vì dồn hết logic vào resolver.

## N+1 (lưu ý, không phải phạm vi thiết kế contract)
- Resolver lồng nhau (VD `User.orders` gọi lại DB cho từng user trong danh sách) dễ gây
  N+1 query — đây là vấn đề TRIỂN KHAI (dùng Dataloader/batching để giải quyết), không
  phải quyết định ở tầng thiết kế contract. Chỉ cần ghi chú trong bàn giao cho người
  triển khai nếu schema có khả năng gây N+1 rõ ràng (field trả về list lồng nhau nhiều
  cấp).

## Versioning
- KHÔNG version hóa qua URL như REST (GraphQL thường chỉ có 1 endpoint `/graphql`).
- Thêm field/type mới thay vì đổi field cũ. Đánh dấu field cũ `@deprecated(reason: "...")`
  trước khi xóa hẳn, cho consumer thời gian migrate.
- Breaking change thật sự (đổi type field, đổi ngữ nghĩa argument) cần thông báo trước và
  có lộ trình — tương tự REST, không âm thầm đổi.

## Error Handling
- GraphQL luôn trả HTTP 200 kể cả khi có lỗi nghiệp vụ — lỗi nằm trong field `errors[]`
  của response, không dựa vào HTTP status code như REST.
- Dùng `extensions` trong error object để mang thông tin có cấu trúc (error code, field
  liên quan) thay vì chỉ có `message` dạng text tự do — giúp client xử lý lỗi có điều
  kiện thay vì so sánh chuỗi.

## Bảo mật đặc thù GraphQL
- Giới hạn độ sâu query (`query depth limit`) và độ phức tạp (`query complexity`) — 1
  query GraphQL có thể lồng sâu tùy ý, khác REST (mỗi request chỉ tốn 1 lần gọi cố
  định), nên rate-limit theo request count KHÔNG đủ, cần giới hạn theo complexity.
- Tắt `introspection` ở môi trường production nếu API không public, tránh lộ toàn bộ
  schema nội bộ cho người ngoài dò.
