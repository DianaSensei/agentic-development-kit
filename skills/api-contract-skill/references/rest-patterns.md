# REST Patterns

## Resource & URI
- Resource-oriented URL, danh từ số nhiều: `/users`, `/users/{id}/orders` — KHÔNG nhét
  verb vào URI (`/getUser/{id}` sai, `/users/{id}` đúng — verb đã nằm trong HTTP method).
- Nested resource tối đa 2 cấp (`/users/{id}/orders`) — sâu hơn nên dùng query param lọc
  thay vì lồng thêm (`/orders?user_id=...`) để tránh URI quá phức tạp.
- HTTP method đúng ngữ nghĩa: `GET` (đọc, idempotent, safe), `POST` (tạo mới/action không
  idempotent), `PUT` (thay thế toàn bộ, idempotent), `PATCH` (sửa 1 phần), `DELETE` (xóa,
  idempotent).
- Status code đúng ngữ cảnh: `200` OK, `201` Created (kèm header `Location`), `204` No
  Content (xóa thành công không trả body), `400` Bad Request (input sai), `401`
  Unauthorized (chưa auth), `403` Forbidden (đã auth nhưng không đủ quyền), `404` Not
  Found, `409` Conflict (xung đột state), `422` Unprocessable Entity (validate business
  rule fail), `429` Too Many Requests.

## Pagination
- **Cursor-based** (khuyến nghị cho dataset lớn/phân trang sâu): trả `next_cursor` +
  `has_more`, client không cần biết offset — tránh vấn đề "trang bị lệch" khi dữ liệu
  thay đổi giữa các lần gọi.
- **Offset-based** (`?page=2&limit=20`): đơn giản, dễ hiểu, chấp nhận được cho dataset
  nhỏ/UI có "nhảy tới trang N" — nhưng chậm dần với offset lớn và có thể lệch dữ liệu.
- Luôn có giới hạn `limit` tối đa (VD `maximum: 100`) để tránh client xin nguyên bảng.

## Filtering & Sorting
- Query param nhất quán: `?status=active&sort=-created_at` (dấu `-` = giảm dần).
- Validate giá trị filter/sort field — không cho sort theo field bất kỳ (rủi ro lộ field
  nội bộ hoặc N+1 nếu sort theo field không có index).

## Versioning
- Chọn 1 chiến lược nhất quán: URL path (`/v1/users`) rõ ràng/dễ debug nhất, khuyến nghị
  mặc định trừ khi project đã theo header versioning (`Accept:
  application/vnd.api+json;version=1` — sạch hơn về mặt REST thuần túy nhưng khó test/
  debug bằng tay hơn URL path).
- Chỉ dùng major version (`v1`, `v2`) — không version hóa từng field lẻ tẻ (`v1.1`, `v1.2`
  gây rối, khó biết khi nào thực sự breaking).
- **Deprecation phải có cơ chế báo hiệu rõ ràng, không chỉ nói bằng lời**: trả header
  `Deprecation: true` + `Sunset: <ngày tắt, RFC 8594>` + `Link: <url-version-mới>;
  rel="successor-version"` trên mọi response của version sắp bị tắt. Sau ngày sunset, trả
  `410 Gone` kèm message hướng dẫn migrate — không tắt đột ngột không báo trước.
- Thời hạn hỗ trợ song song 2 version tối thiểu vài tháng (tùy mức độ ảnh hưởng consumer
  thực tế) — không tự ý rút ngắn nếu chưa xác nhận consumer đã migrate xong.
- Field-level thay đổi nhỏ (thêm field optional) KHÔNG cần bump version — chỉ bump khi
  breaking (đổi type, xóa field, đổi ngữ nghĩa).

## Caching (conditional requests)
- `Cache-Control` cho response cacheable (`public, max-age=3600` cho dữ liệu ít đổi,
  `private, no-cache` cho dữ liệu riêng user, `no-store` cho dữ liệu nhạy cảm không nên
  cache).
- `ETag` cho response cần validate cache chính xác: client gửi lại `If-None-Match: <etag>`
  ở lần sau, server trả `304 Not Modified` (không body) nếu chưa đổi — tiết kiệm băng
  thông cho resource lớn/ít đổi.
- `If-Match` cho ghi có điều kiện (tránh lost update khi 2 client cùng sửa 1 resource):
  client gửi kèm ETag đã biết, server trả `412 Precondition Failed` nếu resource đã đổi
  từ lúc đó — dùng khi nghiệp vụ cần optimistic concurrency ở tầng HTTP thay vì chỉ ở DB.

## HATEOAS (áp dụng chọn lọc, không bắt buộc)
- Trả link điều hướng liên quan trong response (`_links: { self, next, related }`) nếu
  client cần discover API động — hầu hết REST API nội bộ/CRUD đơn giản KHÔNG cần mức độ
  này, chỉ áp dụng khi có yêu cầu rõ ràng về khả năng tự khám phá API.

## Idempotency
- `PUT`/`DELETE` phải idempotent tự nhiên theo spec HTTP.
- `POST` không idempotent tự nhiên — nếu nghiệp vụ cần (VD tạo đơn hàng, thanh toán),
  dùng header `Idempotency-Key` do client gửi, server dedup theo key đó trong 1 khoảng
  thời gian hợp lý.
