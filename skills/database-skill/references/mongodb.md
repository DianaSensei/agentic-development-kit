# MongoDB — Document-Oriented NoSQL

MongoDB linh hoạt hơn nhiều so với DynamoDB/Cassandra (vẫn hỗ trợ query ad-hoc, aggregation phức tạp,
secondary index tùy ý) nhưng vẫn là NoSQL — không có JOIN thật (chỉ có `$lookup` mô phỏng, chi phí cao),
và quyết định **embed vs reference** khi thiết kế document quan trọng ngang với quyết định normalize của
RDBMS.

## Nguyên tắc thiết kế: Embed vs Reference

- **Embed** (nhúng dữ liệu con vào document cha): đọc 1 lần là đủ (không cần round-trip thứ 2), phù hợp
  quan hệ 1-1 hoặc 1-nhiều với số lượng con GIỚI HẠN và luôn đọc cùng nhau (VD `address` trong `user`,
  `line items` trong 1 `order`).
- **Reference** (lưu `_id` tham chiếu, query riêng hoặc `$lookup`): dùng khi dữ liệu con có thể tăng
  KHÔNG GIỚI HẠN (comment, log, event), khi dữ liệu con cần truy cập độc lập không qua cha, hoặc khi
  nhiều document cha cùng tham chiếu 1 dữ liệu con (tránh trùng lặp/mismatch khi update).

```javascript
// Embed — order và line items luôn đọc/ghi cùng nhau, số lượng item có giới hạn hợp lý
{
  _id: ObjectId("..."),
  customer_id: ObjectId("..."),
  items: [
    { product_id: ObjectId("..."), name: "Widget", qty: 2, price: 29.99 },
    { product_id: ObjectId("..."), name: "Gadget", qty: 1, price: 49.99 }
  ],
  total: 109.97
}

// Reference — comment có thể tăng vô hạn theo thời gian, không nhúng vào post
{ _id: ObjectId("..."), post_id: ObjectId("..."), author_id: ObjectId("..."), text: "..." }
```

**Giới hạn 16MB/document** — nhúng mảng không giới hạn (comment, activity log) là lỗi thiết kế phổ biến
nhất, document sẽ chạm giới hạn này khi dữ liệu tăng theo thời gian dù ban đầu nhỏ. Luôn tự hỏi "mảng
này có giới hạn trên rõ ràng không?" trước khi embed.

## Schema Design Pattern

```javascript
// Subset pattern — chỉ nhúng N item gần nhất/quan trọng nhất, còn lại query riêng khi cần
{
  _id: ObjectId("..."),
  name: "Product X",
  recent_reviews: [ /* 5 review gần nhất */ ],   // đủ cho trang chi tiết sản phẩm
  review_count: 1204                              // để hiển thị tổng, không cần load hết
}

// Extended reference pattern — nhúng vài field hay dùng của bản ghi tham chiếu để tránh $lookup ở query đọc thường xuyên
{
  _id: ObjectId("..."),
  customer: { _id: ObjectId("..."), name: "Alice", email: "alice@example.com" }, // đủ hiển thị, không cần join
  total: 109.97
}
// Đánh đổi: field nhúng (name/email) có thể lệch nếu customer đổi thông tin sau — chấp nhận được cho dữ
// liệu ít đổi hoặc đây là snapshot tại thời điểm tạo order (giống unit_price snapshot ở RDBMS).
```

## Indexing

```javascript
db.orders.createIndex({ customer_id: 1, created_at: -1 });  // compound — thứ tự field quan trọng như RDBMS
db.orders.createIndex({ status: 1 }, { partialFilterExpression: { status: "pending" } }); // partial index
db.products.createIndex({ tags: 1 });                         // multikey — tự động khi index field là mảng
db.posts.createIndex({ title: "text", content: "text" });     // text search
db.locations.createIndex({ coordinates: "2dsphere" });        // geospatial

// Kiểm tra plan trước khi khẳng định index cải thiện hiệu năng — giống EXPLAIN của RDBMS
db.orders.find({ customer_id: ObjectId("...") }).explain("executionStats");
// Tìm "COLLSCAN" (quét toàn collection, tương đương Seq Scan) vs "IXSCAN" (dùng index).
```

Composite index: field dùng equality trước, field dùng sort/range sau — cùng nguyên tắc B-tree composite
index của RDBMS (xem `references/explain-and-indexing.md`).

## Aggregation Pipeline — tối ưu thứ tự stage

```javascript
db.orders.aggregate([
  { $match: { status: "completed", created_at: { $gte: ISODate("2024-01-01") } } }, // lọc SỚM nhất có thể — giảm dữ liệu cho stage sau
  { $project: { customer_id: 1, total: 1 } },   // chỉ giữ field cần — giảm I/O giữa các stage
  { $group: { _id: "$customer_id", total_spent: { $sum: "$total" } } },
  { $sort: { total_spent: -1 } },
  { $limit: 20 }
]);
```

`$match`/`$project` đặt càng sớm trong pipeline càng tốt — MongoDB có thể tận dụng index cho `$match` ở
đầu pipeline (giống `WHERE` trước `GROUP BY`), nhưng KHÔNG dùng được index nếu `$match` đặt sau các stage
biến đổi dữ liệu (`$group`, `$unwind`...).

`$lookup` (JOIN mô phỏng) chi phí cao hơn embed đáng kể, đặc biệt khi không có index trên field join ở
collection đích — chỉ dùng khi reference pattern thực sự cần thiết (xem Embed vs Reference ở trên), không
lạm dụng như JOIN thông thường của RDBMS.

## Transaction & Concurrency

- Multi-document ACID transaction có từ 4.0+ (replica set) / 4.2+ (sharded cluster) — nhưng ưu tiên thiết
  kế document TỰ CHỨA (embed) để hầu hết thao tác chỉ cần atomic ở 1 document (MongoDB đảm bảo atomicity
  tự nhiên ở cấp document, không cần transaction), transaction đa document chỉ dùng khi thực sự cần
  atomicity xuyên nhiều document/collection.
- Tăng/giảm field số nguyên tử: dùng `$inc` — tương đương tinh thần atomic conditional UPDATE của RDBMS,
  không cần đọc-rồi-ghi qua 2 round-trip:

```javascript
db.inventory.updateOne(
  { _id: productId, stock: { $gte: qty } },   // điều kiện trong filter — atomic, tương đương WHERE stock >= :qty
  { $inc: { stock: -qty } }
);
// Kiểm tra matchedCount === 0 để biết thao tác có thành công không (giống updatedRows == 0 của SQL UPDATE)
```

- Optimistic locking: thêm field `version`, điều kiện trong filter (`{ _id, version: expectedVersion }`),
  `$inc` version khi update thành công — cùng pattern `@Version` của JPA.

## Sharding — shard key quan trọng như partition key của DynamoDB/Cassandra

Chọn shard key cardinality cao, phân phối đều traffic — shard key cardinality thấp tạo **hot shard**
(cùng vấn đề hot partition của DynamoDB/Cassandra, xem `references/dynamodb.md`/`references/cassandra.md`).
Đổi shard key sau khi cluster đã có dữ liệu lớn là thao tác nặng (cần resharding) — cân nhắc kỹ trước khi
chọn, đặc biệt nếu dự kiến scale ngang trong tương lai.

## Migration — schemaless nhưng vẫn cần quản lý version document

MongoDB không có DDL `ALTER TABLE`, nhưng ứng dụng vẫn cần xử lý document cũ thiếu field mới (KHÔNG có
constraint ép mọi document cùng shape). 2 cách phổ biến:
1. **Migration script chạy 1 lần**: `updateMany` toàn collection để thêm field mới với default — giống
   migration RDBMS, cần rollback plan và chạy qua duyệt nếu dữ liệu lớn.
2. **Lazy migration ở tầng code**: đọc field mới với fallback default nếu thiếu, ghi lại giá trị mới khi
   document được update tự nhiên — tránh 1 lần ghi hàng loạt tốn tài nguyên, đánh đổi document cũ tồn tại
   ở nhiều "version" cùng lúc trong thời gian dài hơn.

## Testcontainers / Local Testing

Dùng image `mongo` qua `testcontainers-skill` cho integration test — cần replica set (`--replSet`) nếu
test transaction đa document, vì transaction MongoDB yêu cầu replica set ngay cả khi chỉ chạy 1 node.

## Khi nào chọn MongoDB (so với RDBMS và NoSQL key-value/column-based khác)

- Dữ liệu semi-structured, schema thay đổi thường xuyên, nhưng vẫn cần query linh hoạt (filter theo nhiều
  field khác nhau, aggregation, không chỉ theo 1 key cố định như DynamoDB/Cassandra).
- Truy cập tự nhiên theo document (đọc/ghi 1 document là đủ cho phần lớn use case), cần scale ghi ngang
  dễ hơn RDBMS nhưng access pattern CHƯA đủ ổn định/hẹp để chấp nhận đánh đổi của key-value/column-based
  store (xem `references/dynamodb.md`/`references/cassandra.md`).
- KHÔNG phù hợp khi: dữ liệu quan hệ chặt chẽ cần JOIN phức tạp thường xuyên xuyên nhiều bảng, cần
  transaction ACID mạnh làm trung tâm thiết kế (RDBMS phù hợp hơn).

## Quick Reference

| Khái niệm | Vai trò |
|-----------|---------|
| Embed | Nhúng dữ liệu con — đọc 1 lần, dùng cho quan hệ có giới hạn, luôn đọc cùng nhau |
| Reference + `$lookup` | Tách dữ liệu con — dùng khi không giới hạn số lượng hoặc cần truy cập độc lập |
| Compound Index | Thứ tự field: equality trước, sort/range sau — giống B-tree RDBMS |
| `$match`/`$project` sớm | Tối ưu aggregation pipeline, tận dụng index |
| `$inc` + filter điều kiện | Atomic conditional update — tương đương `WHERE x >= :y` của SQL |
| Shard Key | Phân phối dữ liệu vật lý — cardinality thấp gây hot shard |
| 16MB/document | Giới hạn cứng — dấu hiệu cần chuyển embed sang reference |
