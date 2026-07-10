---
name: database-skill
description: Kiến thức chuyên sâu thiết kế và tối ưu database quan hệ (Oracle, PostgreSQL, MySQL) và MongoDB — transaction isolation, concurrency control/locking, indexing, query optimization, migration. Dùng khi feature cần thiết kế/thay đổi schema hoặc tối ưu truy vấn.
---

# Database — RDBMS (Oracle/Postgres/MySQL) + MongoDB

## Discover
Xác nhận DB đang dùng qua dependency/driver cụ thể (Oracle JDBC, `postgresql`, `mysql-
connector-j`, `spring-data-mongodb`). Đọc schema/entity hiện có, migration tool đang dùng
(Flyway/Liquibase). KHÔNG giả định RDBMS nào nếu chưa xác nhận — cú pháp/hành vi khác nhau
đáng kể giữa Oracle/Postgres/MySQL.

## Transaction Isolation Level
- Mặc định: Postgres/MySQL(InnoDB) = `READ COMMITTED`, Oracle = `READ COMMITTED`. Hiểu rõ
  hiện tượng có thể gặp ở mức mặc định: non-repeatable read, phantom read.
- Nâng lên `REPEATABLE READ`/`SERIALIZABLE` chỉ khi nghiệp vụ thực sự cần (VD: kiểm tra
  rồi ghi trong 1 transaction không cho phép dữ liệu đổi giữa chừng) — đánh đổi giảm
  throughput do tăng khả năng conflict/rollback. Trình bày tradeoff nếu đề xuất nâng
  isolation level.

## Concurrency Control
- **Optimistic locking** (version column/`@Version` JPA): phù hợp khi conflict hiếm xảy
  ra, tránh giữ lock lâu — cần xử lý `OptimisticLockException` (retry hoặc báo user).
- **Pessimistic locking** (`SELECT ... FOR UPDATE`): phù hợp khi conflict thường xuyên,
  cần đảm bảo tuần tự — cẩn thận deadlock nếu nhiều transaction lock theo thứ tự khác nhau
  (luôn lock theo 1 thứ tự nhất quán để tránh deadlock).
- MongoDB: dùng transaction (từ 4.0+, cần replica set) chỉ khi thực sự cần multi-document
  atomicity — ưu tiên thiết kế document tự chứa (embed) để tránh cần transaction nếu có thể.

## Indexing
- Index đúng cột dùng trong `WHERE`/`JOIN`/`ORDER BY` thường xuyên — không index thừa (mỗi
  index tốn chi phí ghi, tăng thời gian INSERT/UPDATE).
- Composite index: thứ tự cột quan trọng (cột dùng filter chính xác trước, range sau).
- Kiểm tra query plan (`EXPLAIN ANALYZE` Postgres, `EXPLAIN` MySQL, execution plan Oracle)
  trước khi khẳng định 1 index sẽ cải thiện hiệu năng — không đoán mò.
- MongoDB: index đơn/compound tương tự, chú ý index trên field dùng `$sort`/`$match` trong
  aggregation pipeline.

## Query Optimization
- Tránh `SELECT *` khi chỉ cần vài cột (giảm I/O, tránh lock thừa).
- Phân trang: `LIMIT/OFFSET` đơn giản nhưng chậm với offset lớn — cân nhắc keyset
  pagination (`WHERE id > last_id`) nếu dataset lớn và phân trang sâu.
- MongoDB: dùng `$project` sớm trong pipeline để giảm dữ liệu xử lý ở stage sau.

## Migration
- Backward-compatible ưu tiên: thêm cột nullable, không đổi kiểu cột đang dùng trực tiếp
  (thêm cột mới, migrate dữ liệu, rồi mới bỏ cột cũ ở lần sau).
- Migration lớn (đổi kiểu dữ liệu, đổi index trên bảng lớn) cân nhắc chạy ngoài giờ cao
  điểm, có rollback plan rõ ràng — luôn cần user duyệt trước khi áp dụng lên production.

## Test
Testcontainers cho đúng DB thật (Oracle/Postgres/MySQL/Mongo) trong integration test —
test transaction rollback đúng khi lỗi, test concurrency (2 transaction cùng sửa 1 record)
không gây lost update.

## Ranh giới
Không tự chọn RDBMS/NoSQL nào nếu project chưa có sẵn — nếu là quyết định mới, trình bày
tradeoff (xem thêm nguyên tắc chọn ở phần "Data/Storage" của skill điều phối), chờ user
quyết định. Không tự nâng isolation level hay đổi locking strategy production mà không
giải thích rủi ro.
