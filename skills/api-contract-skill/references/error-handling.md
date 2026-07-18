# Error Handling — RFC 7807 (Problem Details)

## Nguyên tắc chung
Dùng chung 1 schema lỗi cho TOÀN BỘ API — không để mỗi endpoint tự bịa format riêng
(1 endpoint trả `{error: "..."}`, endpoint khác trả `{message: "...", code: ...}` là dấu
hiệu thiếu chuẩn hóa).

## RFC 7807 — chuẩn khuyến nghị nếu project chưa có convention riêng
Mọi response lỗi trả `Content-Type: application/problem+json` với các field:

| Field | Ý nghĩa | Bắt buộc |
|-------|---------|----------|
| `type` | URI ổn định định danh loại lỗi (KHÔNG phải chuỗi chung chung như `"error"`) | Có |
| `title` | Tóm tắt ngắn gọn, cố định cho loại lỗi này | Có |
| `status` | HTTP status code, trùng với status thật của response | Có |
| `detail` | Mô tả CHI TIẾT, actionable, riêng cho lần lỗi này (không phải template tĩnh) | Nên có |
| `instance` | URI của request cụ thể gây lỗi (dùng để trace) | Nên có |
| `errors[]` | Mở rộng riêng cho validation lỗi theo từng field | Khi cần |

### Ví dụ
```json
{
  "type": "https://api.example.com/errors/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "The 'email' field must be a valid email address.",
  "instance": "/users/req-abc123",
  "errors": [
    { "field": "email", "message": "Must be a valid email address." }
  ]
}
```

## Quy tắc áp dụng
- `type` phải là URI ổn định, đã tài liệu hóa — không đổi giá trị này giữa các lần trả về
  cùng loại lỗi (client có thể so sánh `type` để xử lý theo điều kiện).
- `detail` phải actionable — nói rõ CÁI GÌ sai và (nếu có thể) CÁCH sửa, không chỉ nói
  "Invalid input".
- KHÔNG lộ thông tin nhạy cảm trong `detail` (stack trace, câu SQL, đường dẫn file nội
  bộ) — đây là lỗi bảo mật phổ biến.
- Status code trong body PHẢI khớp status code HTTP thật — không trả `200 OK` kèm body
  báo lỗi (gây khó khăn cho client dựa vào HTTP status để xử lý).

## Khi project đã có convention error riêng
KHÔNG áp đặt RFC 7807 nếu project đã có 1 chuẩn error nhất quán khác đang dùng — giữ
nguyên convention hiện có, chỉ đảm bảo endpoint MỚI tuân theo đúng convention đó thay vì
tự bịa format khác.

## Request ID — luôn kèm để debug được
Mọi response lỗi (đặc biệt `5xx`) nên có 1 ID định danh riêng cho request đó (VD field
`request_id`/`instance`, hoặc header `X-Request-ID`) — nếu không có, user/support không
có cách nào tra lại đúng log của lần lỗi cụ thể đó trong hệ thống. Không thêm hạ tầng
tracing mới chỉ vì việc này nếu project chưa có — tận dụng correlation ID sẵn có nếu đã
có cơ chế logging/tracing.

## Retryable vs Non-retryable — giúp client biết có nên tự retry không
Khai báo rõ (qua status code chuẩn, không cần field riêng) lỗi nào client NÊN tự động
retry và lỗi nào KHÔNG:
- **Nên retry** (thường là lỗi tạm thời): `408` Request Timeout, `429` Too Many Requests
  (kèm header `Retry-After`), `502`/`503`/`504` (lỗi hạ tầng tạm thời).
- **KHÔNG nên retry** (lỗi do request sai, retry cũng fail y hệt): `400`, `401`, `403`,
  `404`, `409`, `422`.
- Với `429`/`503`, LUÔN trả kèm header `Retry-After` (giây hoặc HTTP-date) để client biết
  chờ bao lâu trước khi thử lại — không để client tự đoán/retry ngay lập tức gây thêm tải.
