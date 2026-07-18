---
name: database-skill
description: Kiến thức chuyên sâu thiết kế và tối ưu database quan hệ server-side (Oracle, PostgreSQL, MySQL) và MongoDB — transaction isolation, concurrency control/locking, indexing, query optimization, migration. Dùng khi feature cần thiết kế/đổi schema hoặc tối ưu truy vấn với DB có server riêng. KHÔNG dùng cho lưu trữ local/offline Tauri (SQLite qua `tauri-plugin-sql`) — xem `data-storage-skill`.
---

# Database — RDBMS (Oracle/Postgres/MySQL) + MongoDB

## Discover

Xác nhận DB đang dùng qua dependency/driver cụ thể (Oracle JDBC, `postgresql`, `mysql-connector-j`, `spring-data-mongodb`). Đọc schema/entity hiện có, migration tool đang dùng (Flyway/Liquibase). KHÔNG giả định RDBMS nào nếu chưa xác nhận — cú pháp/hành vi khác nhau đáng kể giữa Oracle/Postgres/MySQL.

## Transaction Isolation Level

- Mặc định: Postgres = `READ COMMITTED`, Oracle = `READ COMMITTED`, **MySQL (InnoDB) = `REPEATABLE READ`** (khác Postgres/Oracle — dễ nhầm). Hiểu rõ hiện tượng có thể gặp ở mức mặc định: Postgres/Oracle (`READ COMMITTED`) có thể gặp non-repeatable read và phantom read; MySQL (`REPEATABLE READ`) tự chặn non-repeatable read và (nhờ next-key locking) phần lớn phantom read trong cùng transaction, nhưng dùng gap lock nhiều hơn nên dễ deadlock/block hơn ở mức mặc định so với Postgres — cần lưu ý khi port logic concurrency giữa 2 DB này.
- Nâng lên `REPEATABLE READ`/`SERIALIZABLE` (Postgres/Oracle) chỉ khi nghiệp vụ thực sự cần (hạn chế tối đa) (VD: kiểm tra rồi ghi trong 1 transaction không cho phép dữ liệu đổi giữa chừng) — đánh đổi giảm throughput do tăng khả năng conflict/rollback. Với transaction/method MỚI, tự chọn isolation level phù hợp theo yêu cầu nghiệp vụ và nêu lý do ngắn gọn. Chỉ hỏi lại khi đề xuất nâng isolation level ảnh hưởng transaction/table ĐANG CHẠY production ở quy mô lớn (nguy cơ giảm throughput hệ thống hiện có, không chỉ 1 tính năng mới).

## Concurrency Control

- **Optimistic locking** (version column/`@Version` JPA): phù hợp khi conflict hiếm xảy ra, tránh giữ lock lâu — cần xử lý `OptimisticLockException` (retry hoặc báo user).
- **Pessimistic locking** (`SELECT ... FOR UPDATE`): (hạn chế sử dụng tối đa) phù hợp khi conflict thường xuyên, cần đảm bảo tuần tự — cẩn thận deadlock nếu nhiều transaction lock theo thứ tự khác nhau (luôn lock theo 1 thứ tự nhất quán để tránh deadlock).
- **Atomic conditional UPDATE** (VD: `UPDATE product SET stock = stock - :qty WHERE id = :id AND stock >= :qty`, kiểm tra `updatedRows == 0` để biết thao tác có thành công không): phù hợp NHẤT cho các thao tác tăng/giảm số lượng có điều kiện (trừ tồn kho, trừ số dư, giới hạn quota) — Postgres/MySQL/Oracle tự lock row trong chính câu UPDATE, không cần round-trip riêng để lock (nhanh hơn pessimistic lock), không cần vòng lặp retry ở tầng app (đơn giản hơn optimistic lock). Đây thường là lựa chọn TỐT NHẤT khi điều kiện kiểm tra (`stock >= :qty`) có thể biểu diễn trực tiếp trong mệnh đề `WHERE` của câu UPDATE — chỉ cần optimistic/pessimistic lock khi logic quá phức tạp để nhét vào 1 câu UPDATE duy nhất (VD: cần đọc và validate nhiều điều kiện phụ thuộc dữ liệu khác trước khi quyết định có ghi hay không). MongoDB: dùng transaction (từ 4.0+, cần replica set) chỉ khi thực sự cần multi-document atomicity — ưu tiên thiết kế document tự chứa (embed) để tránh cần transaction nếu có thể. Với thao tác tăng/giảm field số trong 1 document, dùng `$inc` (atomic tự nhiên của Mongo, tương đương tinh thần atomic conditional update ở trên).

## Indexing

- Index đúng cột dùng trong `WHERE`/`JOIN`/`ORDER BY` thường xuyên — không index thừa (mỗi index tốn chi phí ghi, tăng thời gian INSERT/UPDATE).
- Composite index: thứ tự cột quan trọng (cột dùng filter chính xác trước, range sau).
- Kiểm tra query plan (`EXPLAIN ANALYZE` Postgres, `EXPLAIN` MySQL, execution plan Oracle) trước khi khẳng định 1 index sẽ cải thiện hiệu năng — không đoán mò.
- MongoDB: index đơn/compound tương tự, chú ý index trên field dùng `$sort`/`$match` trong aggregation pipeline.

## Query Optimization

- Tránh `SELECT *` khi chỉ cần vài cột (giảm I/O, tránh lock thừa).
- Phân trang: `LIMIT/OFFSET` đơn giản nhưng chậm với offset lớn — cân nhắc keyset pagination (`WHERE id > last_id`) nếu dataset lớn và phân trang sâu.
- MongoDB: dùng `$project` sớm trong pipeline để giảm dữ liệu xử lý ở stage sau.

## Migration

- Backward-compatible ưu tiên: thêm cột nullable, không đổi kiểu cột đang dùng trực tiếp (thêm cột mới, migrate dữ liệu, rồi mới bỏ cột cũ ở lần sau).
- Migration lớn (đổi kiểu dữ liệu, đổi index trên bảng lớn) cân nhắc chạy ngoài giờ cao điểm, có rollback plan rõ ràng — luôn cần user duyệt trước khi áp dụng lên production (dữ liệu thật, khó/không thể đảo ngược nếu sai). Migration cho bảng mới/chưa có dữ liệu thật thì tự viết và chạy bình thường, không cần chờ duyệt riêng.

## Khi nào chọn RDBMS vs MongoDB (nếu là quyết định mới, chưa bị ràng buộc bởi hệ hiện có)

- RDBMS: dữ liệu có quan hệ rõ ràng cần join, cần transaction ACID mạnh xuyên nhiều bảng, schema tương đối ổn định.
- MongoDB: dữ liệu semi-structured/schema thay đổi thường xuyên, truy cập tự nhiên theo document (đọc/ghi 1 document là đủ, ít cần join), cần scale ghi ngang dễ dàng hơn.

## Issue thường gặp trong thực tế

- **Long-running transaction**: giữ lock lâu chặn transaction khác; ở Postgres còn chặn `VACUUM` chạy đúng lúc, gây bloat table dần theo thời gian — luôn giữ transaction NGẮN, không gọi I/O chậm (HTTP call, xử lý nặng) bên trong transaction boundary.
- **Missing index âm thầm**: không có lỗi rõ ràng khi thiếu index — chỉ chậm dần khi dữ liệu tăng, dễ bị bỏ sót nếu chỉ kiểm tra hiệu năng lúc data còn ít. Nên theo dõi qua slow query log/`EXPLAIN` định kỳ, không chỉ 1 lần lúc launch feature.
- **Connection pool cạn**: transaction không đóng đúng (leak connection do exception không release, hoặc quên đóng) làm cạn pool (HikariCP...) — gây timeout ở request KHÁC hoàn toàn không liên quan tới transaction gây leak, dễ nhầm là lỗi ở chỗ khác.

## Test

Testcontainers cho đúng DB thật (Oracle/Postgres/MySQL/Mongo) trong integration test — test transaction rollback đúng khi lỗi, test concurrency (2 transaction cùng sửa 1 record) không gây lost update.

## Ranh giới

Nếu project đã dùng 1 RDBMS/NoSQL cụ thể, luôn dùng đúng cái đó, không tự đổi. Nếu là project HOÀN TOÀN mới chưa có DB nào — đây là quyết định kiến trúc nền tảng ảnh hưởng toàn bộ hệ thống lâu dài, nên trình bày tradeoff (RDBMS vs MongoDB, xem phần trên) và chờ user quyết định thay vì tự chọn. Không tự nâng isolation level hay đổi locking strategy ảnh hưởng dữ liệu/transaction ĐANG CHẠY production mà không giải thích rủi ro trước — nhưng với code/bảng mới trong phạm vi task, tự chọn chiến lược concurrency phù hợp mà không cần hỏi.
