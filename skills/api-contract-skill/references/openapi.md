# OpenAPI 3.x/3.1

OpenAPI là artifact THẬT của contract REST — không phải tài liệu tham khảo phụ, đây chính
là file phải ghi ra (xem mục Output trong SKILL.md chính).

## Cấu trúc tối thiểu hợp lệ

```yaml
openapi: "3.1.0"
info:
  title: My API
  version: "1.0.0"
servers:
  - url: https://api.example.com/v1
    description: Production
paths:
  /users/{id}:
    get:
      summary: Get a user
      operationId: getUser
      tags: [Users]
      parameters:
        - name: id
          in: path
          required: true
          schema: { type: string, format: uuid }
      responses:
        "200":
          description: User found
          content:
            application/json:
              schema: { $ref: "#/components/schemas/User" }
        "404": { $ref: "#/components/responses/NotFound" }
components:
  schemas:
    User:
      type: object
      required: [id, email]
      properties:
        id:    { type: string, format: uuid, readOnly: true }
        email: { type: string, format: email }
  responses:
    NotFound:
      description: Resource not found
      content:
        application/problem+json:
          schema: { $ref: "#/components/schemas/Problem" }
  securitySchemes:
    BearerAuth: { type: http, scheme: bearer, bearerFormat: JWT }
security:
  - BearerAuth: []
```

## Quy tắc khi viết spec
- `operationId` duy nhất, dùng để codegen client/server — đặt tên rõ nghĩa
  (`listUsers`, `getUser`, `createUser`), không để trống (nhiều tool codegen cần field
  này).
- Field readonly (`id`, `created_at`) đánh dấu `readOnly: true` — tránh client gửi lên khi
  tạo/sửa resource.
- Dùng `$ref` để tái sử dụng schema chung (`Problem`, `Pagination`) — không copy-paste
  định nghĩa response lỗi vào từng endpoint.
- Khai báo `securitySchemes` + `security` tường minh — không để mặc định "endpoint nào
  cũng cần auth" mà không ghi rõ trong spec.

## Validate & Mock (nếu project đã có tooling)
- Lint spec trước khi báo hoàn thành nếu có tool sẵn: `npx @redocly/cli lint
  <file>.openapi.yaml` — không tự thêm dependency mới cho việc này nếu project chưa có,
  chỉ ghi chú nên có trong báo cáo.
- Mock server để verify contract trước khi bên tiêu thụ code theo: `npx
  @stoplight/prism-cli mock <file>.openapi.yaml` — hữu ích khi frontend/consumer cần bắt
  đầu code song song trước khi backend implement xong.

## OpenAPI 3.0 vs 3.1
- 3.1 tương thích JSON Schema đầy đủ hơn (hỗ trợ `type` là mảng, `const`, composition
  linh hoạt hơn) — ưu tiên 3.1 cho spec MỚI nếu tooling project hỗ trợ.
- Nếu project đã có spec 3.0 lớn, không tự ý nâng lên 3.1 giữa chừng chỉ vì lý thuyết
  "mới hơn" — việc nâng version spec ảnh hưởng toàn bộ tooling codegen đang dùng, cần bàn
  riêng nếu có lý do cụ thể (VD cần feature JSON Schema mà 3.0 không hỗ trợ).
