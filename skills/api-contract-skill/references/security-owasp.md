# Security — OWASP API Security Top 10 (áp dụng cho REST/GraphQL/RPC)

## Authentication & Authorization
- Khai báo scheme xác thực/phân quyền RÕ RÀNG theo từng endpoint/method — không để mặc
  định "cần auth" một cách mơ hồ, ghi rõ ai (role/scope nào) được gọi endpoint nào.
- Phân biệt rõ 2 lỗi: **401** (chưa xác thực — không biết bạn là ai) vs **403** (đã xác
  thực nhưng không đủ quyền) — trả nhầm loại khiến client debug sai hướng.
- Broken Object Level Authorization (BOLA) — lỗi API phổ biến nhất theo OWASP: luôn kiểm
  tra user hiện tại có quyền truy cập ĐÚNG object đang request (VD `/orders/{id}` phải
  kiểm tra order đó thuộc về user gọi, không chỉ kiểm tra "đã login").

## Input Validation
- Validate chặt: type, format, min/max, pattern — hoặc field constraint tương ứng trong
  `.proto`/GraphQL schema. Không tin dữ liệu từ client dù đã có validate phía UI.
- Giới hạn kích thước payload request (tránh DoS qua body quá lớn).

## Response
- Tránh **over-fetching/mass assignment**: response chỉ trả field cần thiết, không trả
  nguyên object nội bộ (VD field `password_hash`, `internal_notes` lọt ra ngoài do dùng
  serializer mặc định thay vì DTO tường minh).
- `Idempotency-Key` cho endpoint không idempotent tự nhiên (VD tạo đơn hàng qua `POST`)
  nếu nghiệp vụ cần tránh double-submit.

## Rate Limiting
- Ghi chú rate-limit nếu endpoint có nguy cơ bị lạm dụng (login, search, tạo resource
  hàng loạt) — REST rate-limit theo request count là đủ; **GraphQL cần rate-limit theo
  query complexity**, không chỉ request count, vì 1 query GraphQL có thể tốn tài nguyên
  gấp nhiều lần 1 request REST đơn giản.

## Bí mật & Cấu hình
- KHÔNG hardcode secret/API key trong contract/spec file (VD ví dụ trong OpenAPI không
  dùng key thật).
- Với `.proto`/GraphQL schema: không expose field/message nội bộ không cần thiết ra
  public API chỉ vì "tiện dùng lại type có sẵn" — tạo type/message riêng cho public
  contract nếu khác với model nội bộ.

## Checklist nhanh trước khi chốt contract
- [ ] Mọi endpoint/method có khai báo auth scheme rõ ràng.
- [ ] Có phân biệt 401 vs 403 đúng ngữ cảnh.
- [ ] Object-level authorization được nhắc tới cho endpoint truy cập theo ID.
- [ ] Response không lộ field nhạy cảm/nội bộ.
- [ ] Endpoint có nguy cơ lạm dụng đã ghi chú cần rate-limit.
