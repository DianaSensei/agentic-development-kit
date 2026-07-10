---
name: java-spring-skill
description: Kiến thức chuyên sâu Java + Spring ecosystem (Spring Boot > 2.4, Java > 8) — Spring MVC/WebFlux, Spring Data, Spring Security, Resilience4j — kèm unit test (JUnit5, Mockito). KHÔNG bao gồm Kafka/RabbitMQ (xem kafka-skill/rabbitmq-skill riêng) hay thiết kế DB (xem database-skill). Dùng khi implement business logic Java thuần.
---

# Java + Spring Ecosystem + Unit Test

## Discover trước khi code
Đọc `pom.xml`/`build.gradle`: version Java/Spring Boot chính xác, reactive (WebFlux) hay
servlet (MVC), có Resilience4j/Spring Security không, framework test đang dùng (JUnit4 vs
5, có Mockito/AssertJ chưa). Đọc `CLAUDE.md`/convention. KHÔNG giả định nếu chưa thấy
bằng chứng.

## Kiến trúc & layering
Giữ đúng layer convention hiện có (Controller → Service → Repository, hoặc hexagonal nếu
project đã dùng). Không tự đổi kiến trúc layering giữa chừng.

## An toàn (safe)
- Transaction boundary rõ ràng (`@Transactional` đúng scope, tránh transactional method
  gọi lẫn nhau trong cùng class gây mất hiệu lực proxy).
- Idempotency ở nơi có thể gọi trùng (retry từ client, timeout rồi gọi lại).
- Thread-safety cho bean singleton có state (tránh mutable state không đồng bộ hóa).
- Validate input ở boundary (Bean Validation `@Valid`), không tin dữ liệu đầu vào.

## Hiệu năng (performance)
- Tránh N+1 (dùng `@EntityGraph`/`JOIN FETCH` nếu dùng JPA — chi tiết index/DB xem
  `database-skill`).
- Batch xử lý khi khối lượng lớn, tránh load toàn bộ dataset vào memory.
- Connection pool tuning (HikariCP) nếu cần, không tự đổi config mà không đo trước.

## Khả năng scale
- Ưu tiên stateless service để scale ngang.
- Resilience4j: circuit breaker/retry/bulkhead/rate-limiter cho lời gọi phụ thuộc dịch vụ
  khác — chỉ dùng nếu project đã có sẵn pattern này, không tự thêm dependency mới mà
  không báo.
- Cân nhắc reactive (WebFlux) cho I/O-bound cao, nhưng KHÔNG tự chuyển từ MVC sang WebFlux
  giữa chừng nếu không được yêu cầu rõ ràng — đây là quyết định kiến trúc lớn, cần tradeoff
  rõ ràng và user duyệt.

## Issue thường gặp trong thực tế
- **Self-invocation làm mất hiệu lực proxy AOP**: gọi method có `@Transactional`/`@Async`/
  `@Cacheable` từ 1 method KHÁC trong CÙNG class (`this.methodX()`) bỏ qua proxy Spring hoàn
  toàn — annotation bị lờ đi âm thầm, không có lỗi/warning rõ ràng. Tách method đó sang bean
  khác nếu cần annotation có hiệu lực.
- **Bean singleton có mutable state không đồng bộ hóa**: field instance trên 1 `@Service`
  (mặc định singleton scope) bị nhiều request cùng lúc ghi/đọc gây race condition — service
  phải stateless (không field mutable theo request) hoặc đồng bộ hóa đúng nếu bắt buộc có state.
- **ThreadLocal không được clear**: dùng ThreadLocal lưu context theo request (userId,
  tenant...) mà không `remove()` sau khi xong — thread trong pool được tái sử dụng cho
  request khác vẫn còn giá trị cũ, gây rò rỉ dữ liệu giữa các request (nghiêm trọng nếu là
  thông tin phân quyền/tenant).

## Unit Test (JUnit5 + Mockito)
1. Cover từng Acceptance Criteria/Edge Case ở mức business logic thuần túy.
2. Mock mọi dependency ngoài (DB, HTTP client, message broker) — unit test không chạm
   I/O thật (integration test là phạm vi khác, phối hợp với `database-skill`/`kafka-skill`/
   `rabbitmq-skill` khi cần Testcontainers).
3. Test cả exception path, không chỉ happy path — đặc biệt validate input sai, dependency
   trả lỗi/timeout.
4. Assertion rõ ràng (AssertJ ưu tiên hơn assert thô nếu project đã dùng), tên test method
   mô tả rõ hành vi đang test (`should_X_when_Y`).
5. Chạy test thật (`mvn test`/`gradle test`), không chỉ viết xong là báo hoàn thành. Fail
   thì tự sửa trong phạm vi hợp lý rồi chạy lại.

## Ranh giới
Không tự quyết định kiến trúc lớn (đổi MVC↔WebFlux, thêm framework mới) — trình bày
tradeoff cho user chọn. Messaging (Kafka/RabbitMQ) → skill riêng. Thiết kế DB/schema →
`database-skill`. Contract API → `api-contract-skill`. Review cuối → `code-review-skill`.
