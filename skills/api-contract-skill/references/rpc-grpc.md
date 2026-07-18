# RPC (gRPC/Protobuf)

## Khi nào dùng
- Giao tiếp service-to-service NỘI BỘ cần hiệu năng cao, hoặc cần streaming (server-side,
  client-side, hoặc bidirectional streaming).
- KHÔNG phù hợp cho public API hướng browser trực tiếp — browser không gọi gRPC thuần
  được, cần proxy như `grpc-web` nếu bắt buộc phải expose ra browser.

## Thiết kế `.proto`
- **Field number KHÔNG được đổi/tái sử dụng sau khi đã publish** — đây là breaking change
  nghiêm trọng nhất trong Protobuf vì wire format dựa vào field number, không phải tên.
  Chỉ thêm field mới với số field mới; đánh dấu `reserved N;` cho field number đã xóa để
  tránh ai đó vô tình dùng lại số đó sau này.
- Field mới PHẢI optional (hoặc có default value hợp lý) để không phá vỡ client cũ chưa
  update — nguyên tắc backward-compatible giống REST/GraphQL.
- Đặt tên message/field theo convention `snake_case` cho field (chuẩn Protobuf), message
  name `PascalCase`.

## Service Definition
```protobuf
service OrderService {
  rpc GetOrder(GetOrderRequest) returns (Order);
  rpc StreamOrderUpdates(StreamRequest) returns (stream OrderUpdate); // server streaming
}
```
- Method name là verb rõ ràng (`GetOrder`, `CreateOrder`) — khác REST, RPC method tên có
  verb là bình thường vì đây không phải resource-oriented.

## Versioning
- Đóng gói version vào package name (`package com.example.order.v1;`) nếu cần breaking
  change — tạo package `v2` mới thay vì cố nhồi backward-compat vào cùng 1 message khi
  thay đổi quá lớn để giữ đúng nghĩa "1 version = 1 contract cố định".

## Deadline & Timeout
- Luôn set deadline phía client cho mọi RPC call — tránh chờ vô hạn khi service downstream
  chậm/treo. Không dựa vào timeout mặc định của thư viện (thường quá dài hoặc không có).
- Deadline nên truyền xuyên suốt chuỗi gọi (deadline propagation) nếu A gọi B gọi C — C
  không nên có deadline dài hơn thời gian còn lại của deadline gốc từ A.

## Error Handling
- Dùng status code chuẩn của gRPC (`INVALID_ARGUMENT`, `NOT_FOUND`, `PERMISSION_DENIED`,
  `DEADLINE_EXCEEDED`...) thay vì tự định nghĩa error code riêng — client/tooling gRPC đã
  hiểu sẵn các status này.
- Dùng `google.rpc.ErrorDetails` (hoặc tương đương) để mang thông tin lỗi có cấu trúc khi
  cần chi tiết hơn status code đơn thuần.
