# Cassandra — Wide-Column NoSQL (CQL)

Lưu ý phân biệt: **ScyllaDB dùng API tương thích DynamoDB (Alternator)** được gộp chung với DynamoDB ở
`references/dynamodb.md`. File này chỉ dành cho **Cassandra native qua CQL** — nếu project dùng ScyllaDB
qua CQL thuần (không qua Alternator), data model/CQL ở file này áp dụng gần như y hệt (ScyllaDB tương
thích giao thức/CQL với Cassandra), chỉ khác ở tầng vận hành: ScyllaDB viết bằng C++ (không có GC pause
như Cassandra JVM), kiến trúc shard-per-core tận dụng nhiều core/node hiệu quả hơn mà không cần tự tay
tune JVM heap.

## Nguyên tắc thiết kế: Access Pattern trước, bảng sau

Cassandra KHÔNG hỗ trợ JOIN và không có ad-hoc query linh hoạt như RDBMS. Một bảng (table) chỉ phục vụ
tốt CHO ĐÚNG 1 (hoặc vài) access pattern đã biết trước — cần access pattern khác thì tạo bảng khác chứa
cùng dữ liệu nhưng key khác (**denormalization theo query**, cùng tinh thần "query-first" của DynamoDB,
xem `references/dynamodb.md`).

## Partition Key & Clustering Key

```sql
CREATE TABLE orders_by_customer (
    customer_id  UUID,
    order_date   TIMESTAMP,
    order_id     UUID,
    status       TEXT,
    total        DECIMAL,
    PRIMARY KEY ((customer_id), order_date, order_id)
    -- (customer_id) = partition key — quyết định node/replica nào giữ dữ liệu
    -- order_date, order_id = clustering key — quyết định thứ tự sắp xếp TRONG partition
) WITH CLUSTERING ORDER BY (order_date DESC);
```

- **Partition key**: bắt buộc có trong `WHERE` của mọi query hiệu quả — quyết định dữ liệu nằm ở node
  nào. Cardinality thấp (VD dùng `status` làm partition key khi chỉ có vài giá trị) tạo **hot partition**
  — 1 node nhận toàn bộ traffic ghi/đọc trong khi node khác rảnh.
- **Clustering key**: sắp xếp vật lý dữ liệu trong partition, cho phép range query (`order_date > ?`)
  hiệu quả mà không cần đọc cả partition.

**Denormalize theo query** — bảng riêng cho từng access pattern, đồng bộ dữ liệu khi ghi (không JOIN lúc đọc):

```sql
-- Access pattern 1: tra đơn hàng theo customer → bảng ở trên
-- Access pattern 2: tra đơn hàng theo status → bảng riêng, PK khác
CREATE TABLE orders_by_status (
    status      TEXT,
    order_date  TIMESTAMP,
    order_id    UUID,
    customer_id UUID,
    total       DECIMAL,
    PRIMARY KEY ((status), order_date, order_id)
);
-- Ứng dụng phải ghi vào CẢ HAI bảng khi tạo order — đánh đổi: tốn 2x write, nhưng đọc luôn nhanh (không JOIN)
```

## CQL — giống SQL nhưng bị giới hạn có chủ đích

```sql
-- Query hiệu quả: LUÔN có partition key trong WHERE
SELECT * FROM orders_by_customer WHERE customer_id = ? AND order_date > '2024-01-01';

-- KHÔNG được: filter theo cột không phải partition/clustering key mà thiếu ALLOW FILTERING
SELECT * FROM orders_by_customer WHERE total > 1000;  -- lỗi, trừ khi thêm ALLOW FILTERING

-- ALLOW FILTERING = red flag hiệu năng — quét toàn bộ rồi filter, CQL cố tình chặn mặc định để buộc dev
-- nhận ra query sai thiết kế thay vì âm thầm chậm dần khi data lớn.
```

Không có JOIN, không có subquery, không có `GROUP BY` linh hoạt như SQL — mọi aggregation phức tạp nên
xử lý ở tầng ứng dụng hoặc qua Spark connector, không cố nhét vào CQL.

## Consistency Level — tunable, chọn theo từng query

Cassandra dùng mô hình eventually-consistent với consistency level (CL) chọn được PER QUERY, không cố định như replica RDBMS:

| CL | Ý nghĩa | Dùng khi |
|----|---------|----------|
| `ONE` | 1 replica xác nhận | Đọc/ghi nhanh nhất, chấp nhận stale data tạm thời |
| `QUORUM` | Đa số replica xác nhận (VD 2/3) | Cân bằng consistency/latency — mặc định hợp lý cho hầu hết use case |
| `ALL` | Toàn bộ replica xác nhận | Cần consistency mạnh nhất, chấp nhận latency cao nhất, giảm availability nếu 1 replica down |

**Read + Write CL cùng QUORUM** → đảm bảo read-your-write consistency (R + W > Replication Factor) — đây
là công thức quan trọng nhất khi cần đọc đúng giá trị vừa ghi mà không cần CL=ALL.

## Replication Factor & Multi-Datacenter

```sql
CREATE KEYSPACE ecommerce WITH replication = {
    'class': 'NetworkTopologyStrategy',
    'datacenter1': 3   -- 3 bản sao trong DC này — RF=3 là baseline production phổ biến
};
```

RF=3 + CL=QUORUM là combo mặc định hợp lý cho production — chịu được 1 node down mà không mất
availability lẫn consistency. Multi-datacenter replication (`NetworkTopologyStrategy` với nhiều DC) dùng
khi cần disaster recovery hoặc giảm latency đọc/ghi theo vùng địa lý — quyết định hạ tầng lớn, cần bàn
riêng với user, không tự thêm.

## Lightweight Transaction (LWT) — conditional write, tương đương ConditionExpression của DynamoDB

```sql
INSERT INTO orders (order_id, status) VALUES (?, 'pending') IF NOT EXISTS;
UPDATE inventory SET stock = stock - :qty WHERE product_id = ? IF stock >= :qty;
```

LWT dùng Paxos protocol nội bộ — chi phí cao hơn write thường đáng kể (round-trip nhiều hơn), chỉ dùng
khi thực sự cần atomicity có điều kiện, không dùng cho mọi write mặc định.

## Ops & Tuning

- **Compaction strategy**: `SizeTieredCompactionStrategy` (mặc định, tốt cho write-heavy) vs
  `LeveledCompactionStrategy` (tốt cho read-heavy, giảm số SSTable phải đọc) — chọn theo tải thật, không
  đổi mặc định nếu chưa đo được vấn đề cụ thể.
- **JVM heap & GC**: Cassandra chạy trên JVM — cần tune heap size, theo dõi GC pause. GC pause dài là
  nguyên nhân phổ biến nhất gây latency spike đột ngột. (ScyllaDB dùng CQL không có bước tune này — C++,
  kiến trúc shard-per-core tự phân bổ theo core CPU, nhưng vẫn cần theo dõi hot partition tương tự.)
- **Tombstone**: `DELETE` không xóa ngay mà đánh dấu tombstone (giống MVCC dead tuple của Postgres) — quá
  nhiều tombstone trong 1 partition (pattern delete thường xuyên) làm chậm read đáng kể; cần `nodetool
  compact` định kỳ hoặc thiết kế TTL thay vì DELETE thủ công khi có thể.
- **`nodetool repair`**: chạy định kỳ (thường hàng tuần) để đồng bộ lại dữ liệu giữa các replica sau
  network partition/node down — bỏ qua lâu ngày làm tăng rủi ro đọc dữ liệu không nhất quán.

## Testcontainers / Local Testing

Dùng image `cassandra` (hoặc `scylladb/scylla` nếu project dùng ScyllaDB qua CQL) qua `testcontainers-skill`
— test đúng hành vi CQL/consistency level thật, đặc biệt quan trọng để phát hiện query thiếu partition key
(lỗi ngay lúc chạy CQL) sớm.

## Khi nào chọn Cassandra (so với DynamoDB/ScyllaDB Alternator/RDBMS/MongoDB — xem SKILL.md chính)

- Ghi cực lớn, phân tán nhiều datacenter, cần kiểm soát hạ tầng (self-hosted) thay vì managed service.
- Đã có nhiều access pattern rõ ràng, chấp nhận denormalize/ghi nhiều bảng để đổi lấy đọc nhanh.
- Muốn ecosystem/tooling CQL truyền thống (driver ổn định đa ngôn ngữ, Spark connector) — nếu chỉ cần
  cùng data model nhưng hiệu năng tốt hơn trên cùng phần cứng và không muốn tune JVM, cân nhắc ScyllaDB
  qua CQL thay vì Cassandra (nội dung file này áp dụng gần như nguyên vẹn, xem ghi chú Ops ở trên).
- KHÔNG phù hợp khi: query pattern chưa ổn định, cần JOIN/ad-hoc query phức tạp, team chưa có kinh nghiệm
  vận hành hệ phân tán (chi phí vận hành self-hosted không nhỏ) — cân nhắc DynamoDB/ScyllaDB Alternator
  nếu muốn managed, hoặc RDBMS/MongoDB nếu access pattern chưa chốt.

## Quick Reference

| Khái niệm | Vai trò |
|-----------|---------|
| Partition Key | Phân phối dữ liệu vật lý, bắt buộc trong WHERE |
| Clustering Key | Sắp xếp trong partition, cho phép range query |
| `ALLOW FILTERING` | Red flag — quét không dùng index, tránh dùng |
| Consistency Level (CL) | Chọn per-query: ONE/QUORUM/ALL |
| Replication Factor (RF) | Số bản sao — RF=3 + CL=QUORUM là baseline phổ biến |
| Lightweight Transaction (LWT) | Conditional write (`IF NOT EXISTS`/`IF ...`), tốn chi phí Paxos |
| Tombstone | Dấu vết `DELETE` — nhiều tombstone làm chậm read |
| `nodetool repair` | Đồng bộ lại replica định kỳ |
