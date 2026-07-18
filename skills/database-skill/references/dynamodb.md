# DynamoDB (+ ScyllaDB Alternator) — Key-Value / Wide-Column NoSQL

DynamoDB khác biệt căn bản so với RDBMS/MongoDB: không có JOIN, không có ad-hoc query linh hoạt —
schema/index phải thiết kế THEO access pattern biết trước, không phải theo cấu trúc dữ liệu. Thiết kế
sai từ đầu (không đủ GSI cho pattern đọc cần) thường không sửa được nếu không tạo lại bảng.

**ScyllaDB dùng chung file này** — ScyllaDB có API tương thích DynamoDB gọi là **Alternator**, implement
lại đúng DynamoDB API (PutItem/Query/GSI/`ConditionExpression`...) trên engine ScyllaDB. Khi project dùng
ScyllaDB qua Alternator (thay vì CQL native), toàn bộ nội dung thiết kế data model bên dưới áp dụng y
hệt DynamoDB — chỉ khác ở tầng vận hành hạ tầng (xem mục "ScyllaDB Alternator — khác biệt vận hành" cuối
file). Nếu project dùng ScyllaDB qua CQL native (không qua Alternator) thì đó là data model khác hẳn —
xem `references/cassandra.md` thay vì file này.

## Nguyên tắc thiết kế: Access Pattern trước, sau đó mới tới bảng

Liệt kê TOÀN BỘ query pattern ứng dụng cần (VD "lấy đơn hàng theo customer", "lấy đơn hàng theo trạng
thái trong khoảng ngày") TRƯỚC khi thiết kế partition key/sort key — ngược hoàn toàn với RDBMS (normalize
trước, query sau). Không có pattern nào có thể bổ sung dễ dàng sau khi bảng đã có dữ liệu lớn mà không
tạo GSI mới (tốn chi phí backfill) hoặc thiết kế lại.

## Partition Key & Sort Key

```
Bảng "Orders":
  PK (partition key): CUSTOMER#<customer_id>
  SK (sort key):       ORDER#<order_id>
```

- **Partition key** quyết định phân phối dữ liệu vật lý — chọn cột có cardinality cao, tránh "hot
  partition" (VD dùng `status` làm PK khi status chỉ có vài giá trị → toàn bộ traffic dồn vào vài partition).
- **Sort key** cho phép query range trong cùng 1 partition (`begins_with`, `between`) — dùng để nhét nhiều
  loại entity liên quan vào cùng 1 item collection (**single-table design**).

### Single-Table Design (pattern phổ biến nhất trong production)

```
PK                  | SK                  | Attributes
CUSTOMER#123        | METADATA            | name, email, ...
CUSTOMER#123        | ORDER#2024-01-15-01 | total, status, ...
CUSTOMER#123        | ORDER#2024-02-01-02 | total, status, ...
```

1 `Query` với `PK = CUSTOMER#123` lấy được cả profile khách hàng lẫn toàn bộ order — thay thế cho JOIN
của RDBMS. Đánh đổi: khó đọc hơn nhiều so với bảng riêng biệt, và mọi access pattern phải biết trước khi
thiết kế key. Chỉ dùng single-table khi đã xác nhận rõ pattern; nếu access pattern còn chưa chắc chắn
(giai đoạn sớm của sản phẩm), multi-table đơn giản hơn dễ maintain hơn dù kém tối ưu chi phí.

## Global Secondary Index (GSI) & Local Secondary Index (LSI)

- **GSI**: partition key + sort key KHÁC với bảng gốc — dùng để hỗ trợ access pattern thứ 2 (VD tra cứu
  order theo `status` thay vì theo `customer_id`). Có `WriteCapacity`/eventual consistency riêng, tạo/xóa
  được sau khi bảng đã tồn tại (nhưng cần backfill nếu bảng đã có dữ liệu).
- **LSI**: cùng partition key với bảng gốc, chỉ khác sort key — PHẢI khai báo lúc tạo bảng, không thêm được
  sau. Giới hạn 20GB dữ liệu mỗi partition key value khi có LSI. Ít linh hoạt hơn GSI — chỉ dùng khi cần
  strongly consistent read trên 1 pattern phụ và chắc chắn ngay từ đầu.

```
GSI "StatusIndex": PK = STATUS#<status>, SK = ORDER#<created_at>
→ Query đơn hàng theo status, sort theo thời gian tạo, không cần Scan toàn bảng.
```

## Query vs Scan — LUÔN ưu tiên Query, Scan là red flag hiệu năng

```
Query: đọc theo PK (và tùy chọn điều kiện SK) — hiệu quả, chi phí tỷ lệ với số item trả về.
Scan:  đọc TOÀN BỘ bảng rồi filter — chi phí tỷ lệ với TOÀN BỘ bảng bất kể filter match bao nhiêu item.
```

Nếu cần `Scan` thường xuyên cho 1 access pattern → dấu hiệu thiết kế key/GSI sai, không phải vấn đề tối
ưu query. Filter Expression trong Query/Scan chỉ giảm dữ liệu TRẢ VỀ, KHÔNG giảm chi phí đọc — DynamoDB
vẫn tính capacity theo số item quét trước khi filter.

## Capacity Mode

- **On-Demand**: trả theo request thật, tự scale — phù hợp traffic khó dự đoán hoặc giai đoạn đầu chưa
  rõ pattern tải. Chi phí/request cao hơn Provisioned khi traffic ổn định và lớn.
- **Provisioned** (+ Auto Scaling): rẻ hơn khi traffic dự đoán được và ổn định, nhưng cần theo dõi
  throttling (`ProvisionedThroughputExceededException`) — traffic v ượt capacity đặt sẵn bị từ chối chứ
  không tự động scale ngay lập tức như On-Demand.

Mặc định chọn On-Demand cho feature mới/chưa rõ traffic pattern; chuyển sang Provisioned khi đã đo được
traffic ổn định và cần tối ưu chi phí — đây là quyết định vận hành, không phải quyết định thiết kế schema,
có thể đổi qua lại mà không ảnh hưởng dữ liệu.

## Consistency & Concurrency

- Đọc mặc định là **eventually consistent** (rẻ hơn) — dùng `ConsistentRead: true` khi nghiệp vụ cần đọc
  đúng giá trị vừa ghi ngay lập tức (tốn gấp đôi read capacity so với eventual).
- **Conditional writes** — cơ chế atomic tương đương optimistic locking/atomic UPDATE của RDBMS, không có
  transaction dài như RDBMS:

```
PutItem/UpdateItem với ConditionExpression, VD:
  ConditionExpression: "attribute_not_exists(PK)"          -- chỉ insert nếu chưa tồn tại
  ConditionExpression: "version = :expected_version"        -- optimistic locking kiểu version column
  UpdateExpression: "SET stock = stock - :qty"
  ConditionExpression: "stock >= :qty"                       -- tương đương atomic conditional UPDATE của RDBMS
```

- **TransactWriteItems**: hỗ trợ multi-item ACID transaction (tối đa 100 item, cùng region) — dùng khi
  thực sự cần atomicity xuyên nhiều item/bảng, tốn chi phí gấp đôi write capacity so với write thường, chỉ
  dùng khi `ConditionExpression` trên 1 item không đủ giải quyết bài toán.

## Item Size & Design Constraint

- Giới hạn 400KB/item — dữ liệu lớn (file, blob) lưu ở S3, DynamoDB chỉ giữ reference/metadata.
- Không có `ALTER TABLE`/schema migration theo nghĩa RDBMS — DynamoDB schemaless ở attribute level (mỗi
  item có thể có attribute khác nhau), chỉ PK/SK và index là cố định lúc tạo bảng. "Migration" thực chất
  là thay đổi cách ứng dụng ghi/đọc attribute, hoặc backfill GSI mới — không phải DDL.

## DynamoDB Streams & TTL

- **Streams**: capture thay đổi item (INSERT/MODIFY/REMOVE) theo thời gian thực, trigger Lambda — dùng cho
  side-effect bất đồng bộ (audit log, sync sang hệ thống khác, cập nhật aggregate) thay vì trigger SQL của
  RDBMS.
- **TTL**: tự động xóa item hết hạn (dựa trên epoch timestamp attribute) — dùng cho session/cache data,
  không tính write capacity khi xóa qua TTL (khác với xóa thủ công).

## DAX (DynamoDB Accelerator)

Cache layer riêng cho DynamoDB (tương tự Redis nhưng tích hợp sẵn, microsecond latency) — chỉ thêm khi đã
xác nhận read-heavy workload cần latency thấp hơn nữa và đã tối ưu key design, không phải bước đầu tiên
khi thấy chậm.

## ScyllaDB Alternator — khác biệt vận hành so với DynamoDB thật

- **Self-hosted/multi-cloud**: ScyllaDB không bị khóa vào AWS như DynamoDB — chọn Alternator khi muốn data
  model/API của DynamoDB nhưng cần tự vận hành hạ tầng (on-prem, multi-cloud, hoặc đã có cluster ScyllaDB
  sẵn cho mục đích khác qua CQL).
- **Không có khái niệm On-Demand/Provisioned capacity kiểu AWS billing** — throughput giới hạn bởi tài
  nguyên cluster thật (CPU/RAM/disk của node), cần tự capacity-plan như mọi hệ self-hosted, không tự động
  scale theo request như DynamoDB On-Demand thật.
- **Không có DAX, Streams giới hạn hơn** — 1 số tính năng managed-only của AWS (DAX cache layer, Streams
  tích hợp Lambda) không có sẵn hoặc cần tự dựng tương đương; kiểm tra tài liệu Alternator hiện tại của
  ScyllaDB trước khi giả định tính năng nào khả dụng.
- **Vận hành cluster** (compaction, repair, GC-less shard-per-core) giống hệt phần Ops của ScyllaDB khi
  dùng CQL — xem `references/cassandra.md` mục cuối để hiểu kiến trúc shard-per-core, dù ở đây dùng qua
  Alternator API chứ không phải CQL.

## Testcontainers / Local Testing

Dùng `amazon/dynamodb-local` image (DynamoDB thật) hoặc `scylladb/scylla` với cờ bật Alternator (ScyllaDB)
qua `testcontainers-skill` cho integration test — hành vi Query/GSI/conditional write tái hiện đúng như
production, khác với mock SDK thuần (mock không bắt được lỗi thiết kế key/GSI).

## Khi nào chọn DynamoDB vs ScyllaDB Alternator (so với RDBMS/MongoDB/Cassandra — xem SKILL.md chính)

- Access pattern đã rõ ràng, ổn định, và có thể liệt kê hết trước khi thiết kế — điều kiện tiên quyết
  chung cho cả 2.
- Cần scale ghi/đọc theo chiều ngang gần như không giới hạn, latency single-digit millisecond ổn định.
- **DynamoDB thật**: đã ở AWS, muốn managed hoàn toàn, không muốn vận hành cluster.
- **ScyllaDB qua Alternator**: muốn giữ nguyên data model/API quen thuộc của DynamoDB nhưng cần tự vận
  hành hạ tầng (self-hosted/multi-cloud), hoặc đã có sẵn ScyllaDB cluster.
- KHÔNG phù hợp (cả 2) khi: cần query ad-hoc linh hoạt (báo cáo, phân tích đa chiều), cần JOIN phức tạp,
  hoặc access pattern còn thay đổi liên tục ở giai đoạn sản phẩm đầu — RDBMS/MongoDB linh hoạt hơn nhiều
  cho các trường hợp này.

## Quick Reference

| Khái niệm | Vai trò |
|-----------|---------|
| Partition Key (PK) | Phân phối dữ liệu vật lý, bắt buộc trong mọi Query |
| Sort Key (SK) | Query range trong 1 partition, cho phép single-table design |
| GSI | Access pattern phụ, key khác bảng gốc, thêm được sau |
| LSI | Access pattern phụ, cùng PK, khai báo lúc tạo bảng, không đổi sau |
| Query | Đọc hiệu quả theo PK — luôn ưu tiên |
| Scan | Đọc toàn bảng — red flag, tránh dùng cho access pattern thường xuyên |
| ConditionExpression | Atomic write có điều kiện — tương đương optimistic lock/atomic UPDATE |
| TransactWriteItems | ACID xuyên nhiều item, tốn gấp đôi capacity |
| On-Demand / Provisioned | Chế độ tính capacity — On-Demand mặc định khi chưa rõ traffic |
