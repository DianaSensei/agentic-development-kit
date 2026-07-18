---
name: java-spring-skill
description: Kiến thức chuyên sâu Java + Spring ecosystem (Spring Boot > 2.4, Java > 8) — Spring MVC/WebFlux, Spring Data, Spring Security, Resilience4j — kèm unit test (JUnit5, Mockito). KHÔNG bao gồm Kafka/RabbitMQ (xem kafka-skill/rabbitmq-skill riêng) hay thiết kế DB (xem database-skill). Dùng khi implement business logic Java thuần.
---

# Java + Spring Ecosystem + Unit Test

## Discover trước khi code

Đọc `pom.xml`/`build.gradle`: version Java/Spring Boot chính xác, reactive (WebFlux) hay servlet (MVC), có Resilience4j/Spring Security không, framework test đang dùng (JUnit4 vs 5, có Mockito/AssertJ chưa). Đọc `CLAUDE.md`/convention. KHÔNG giả định nếu chưa thấy bằng chứng.

## Kiến trúc & layering

Giữ đúng layer convention hiện có (Controller → Service → Repository, hoặc hexagonal/onion nếu project đã dùng). Không tự đổi kiến trúc layering giữa chừng. Ưu tiên tách nghiệp vụ ra khỏi infrastructure (DB, HTTP client, message broker) để dễ test — nếu project đã có sẵn pattern này, dùng đúng convention hiện có, không cần hỏi. Nếu project chưa có, đánh giá việc tách ra có làm tăng độ phức tạp hoặc issue không.

Nếu không có nhu cầu đặc biệt, ưu tiên spring MVC thay vì WebFlux (reactive) — WebFlux chỉ dùng khi có I/O-bound cao, hoặc project đã dùng WebFlux từ đầu. Không tự đổi giữa MVC ↔ WebFlux giữa chừng nếu không được yêu cầu rõ ràng — đây là quyết định kiến trúc lớn ảnh hưởng toàn bộ service, khó đảo ngược nếu đã triển khai. Ưu tiên xử lý IO dưới dạng non-blocking nếu có thể.

## An toàn (safe)

- Transaction boundary rõ ràng (`@Transactional` đúng scope, tránh transactional method gọi lẫn nhau trong cùng class gây mất hiệu lực proxy).
- Idempotency ở nơi có thể gọi trùng (retry từ client, timeout rồi gọi lại).
- Thread-safety cho bean singleton có state (tránh mutable state không đồng bộ hóa).
- Validate input ở boundary (Bean Validation `@Valid`), không tin dữ liệu đầu vào.

## Hiệu năng (performance)

- Tránh N+1 (dùng `@EntityGraph`/`JOIN FETCH` nếu dùng JPA — chi tiết index/DB xem `database-skill`).
- Batch xử lý khi khối lượng lớn, tránh load toàn bộ dataset vào memory.
- Connection pool tuning (HikariCP): tự đề xuất và áp dụng giá trị hợp lý dựa trên bằng chứng đo được (query log, số connection đang dùng) — không đoán mò khi chưa có số liệu; nếu chưa đo được, giữ nguyên config hiện tại và nêu rõ cần đo trước khi đổi.

## Khả năng scale

- Ưu tiên tránh depend vào framework nếu có thể, nếu không có thể tránh phụ thuộc vào các detail infrastructure (DB, HTTP client, message broker) để tránh phụ thuộc vào dependency cụ thể, dễ thay thế/scale sau này.
- Ưu tiên stateless service để scale ngang.
- Resilience4j: tự áp dụng circuit breaker/retry/bulkhead/rate-limiter cho lời gọi phụ thuộc dịch vụ khác nếu project đã có sẵn pattern này (dùng đúng convention hiện có, không cần hỏi). Nếu project CHƯA có dependency này, tự thêm là hợp lý cho 1 call site cụ thể đang cần — chỉ nêu rõ trong báo cáo là đã thêm dependency mới, không cần dừng lại chờ duyệt trước.
- Cân nhắc reactive (WebFlux) cho I/O-bound cao, nhưng KHÔNG tự chuyển từ MVC sang WebFlux giữa chừng nếu không được yêu cầu rõ ràng — đây là quyết định kiến trúc lớn ảnh hưởng toàn bộ service (đổi runtime model, học lại cho team), khó đảo ngược nếu đã lỡ triển khai — luôn trình bày tradeoff và chờ user duyệt trước khi đổi.

## Issue thường gặp trong thực tế

- **Self-invocation làm mất hiệu lực proxy AOP**: gọi method có `@Transactional`/`@Async`/`@Cacheable` từ 1 method KHÁC trong CÙNG class (`this.methodX()`) bỏ qua proxy Spring hoàn toàn — annotation bị lờ đi âm thầm, không có lỗi/warning rõ ràng. Tách method đó sang bean khác nếu cần annotation có hiệu lực.
- **Bean singleton có mutable state không đồng bộ hóa**: field instance trên 1 `@Service` (mặc định singleton scope) bị nhiều request cùng lúc ghi/đọc gây race condition — service phải stateless (không field mutable theo request) hoặc đồng bộ hóa đúng nếu bắt buộc có state.
- **ThreadLocal không được clear**: dùng ThreadLocal lưu context theo request (userId, tenant...) mà không `remove()` sau khi xong — thread trong pool được tái sử dụng cho request khác vẫn còn giá trị cũ, gây rò rỉ dữ liệu giữa các request (nghiêm trọng nếu là thông tin phân quyền/tenant).

## Unit Test (JUnit5 + Mockito)

1. Cover từng Acceptance Criteria/Edge Case ở mức business logic thuần túy.
2. Mock mọi dependency ngoài (DB, HTTP client, message broker) — unit test không chạm I/O thật (integration test là phạm vi khác, phối hợp với `database-skill`/`kafka-skill`/`rabbitmq-skill` khi cần Testcontainers).
3. Test cả exception path, không chỉ happy path — đặc biệt validate input sai, dependency trả lỗi/timeout.
4. Assertion rõ ràng (AssertJ ưu tiên hơn assert thô nếu project đã dùng), tên test method mô tả rõ hành vi đang test (`should_X_when_Y`).
5. Chạy test thật (`mvn test`/`gradle test`), không chỉ viết xong là báo hoàn thành. Fail thì tự sửa trong phạm vi hợp lý rồi chạy lại.

## Ranh giới

Tự quyết định các lựa chọn kỹ thuật cục bộ trong phạm vi task (cấu trúc method, exception type, tên biến, cách chia nhỏ logic) mà không cần hỏi — đây là công việc thường ngày của skill này. Chỉ dừng lại trình bày tradeoff và chờ user duyệt cho quyết định kiến trúc LỚN, ảnh hưởng toàn service và khó đảo ngược (đổi MVC↔WebFlux, thêm framework runtime mới). Messaging (Kafka/RabbitMQ) → skill riêng. Thiết kế DB/schema → `database-skill`. Contract API → `api-contract-skill`. Review cuối → `code-review-skill`.
