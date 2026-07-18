---
name: elasticsearch-skill
description: Kiến thức chuyên sâu Elasticsearch — thiết kế index/mapping, analyzer, Query DSL, aggregation, chiến lược reindex, shard/replica. Dùng khi feature cần tìm kiếm full-text hoặc phân tích/aggregation dữ liệu lớn.
---

# Elasticsearch

## Discover
Xác nhận project đã dùng ES qua dependency (`spring-data-elasticsearch` hoặc client trực tiếp), đọc index/mapping hiện có, version ES đang dùng (khác biệt đáng kể giữa major version).

## Khi nào phù hợp / KHÔNG phù hợp
Phù hợp: full-text search, log analytics, aggregation trên dataset lớn cần tốc độ. **KHÔNG nên dùng ES làm nguồn dữ liệu chính (source of truth)** — luôn có 1 DB chính (RDBMS/Mongo) giữ dữ liệu gốc, ES chỉ là index phái sinh đồng bộ sang. Đồng bộ này có độ trễ (eventual consistency, mặc định `refresh_interval` 1s) — nếu nghiệp vụ cần đọc NGAY sau ghi với dữ liệu vừa ghi, không dựa vào ES cho path đó.

## Issue thường gặp trong thực tế
- **Cluster health**: `yellow` = thiếu replica (vẫn đọc/ghi được, giảm chịu lỗi), `red` = thiếu primary shard (mất khả năng đọc/ghi phần dữ liệu đó, có thể mất dữ liệu) — luôn theo dõi cluster health khi thiết kế số shard/replica, không chỉ set lúc đầu rồi bỏ quên.
- **Mapping explosion**: dynamic mapping không kiểm soát (field mới tự sinh liên tục từ dữ liệu không đồng nhất) có thể chạm giới hạn `index.mapping.total_fields.limit` gây lỗi ghi — lý do chính để ưu tiên explicit mapping thay vì dynamic cho field quan trọng.
- **Circuit breaker (memory)**: aggregation/sort trên field không giới hạn kích thước có thể gây `CircuitBreakingException` (tràn heap) — giới hạn kích thước response, dùng `search_after` thay vì `from`/`size` cho phân trang sâu (deep pagination cũng chậm dần vì ES phải load + sort toàn bộ kết quả từ đầu tới offset).

## Thiết kế Index & Mapping
- Xác định field nào cần full-text search (`text` + analyzer) vs field nào chỉ cần exact match/filter/sort (`keyword`) — dùng sai kiểu gây kết quả search sai hoặc tốn tài nguyên.
- `mapping` nên khai báo tường minh (explicit mapping), tránh dựa vào dynamic mapping cho field quan trọng (dynamic mapping có thể đoán sai kiểu dữ liệu).
- Đặt tên index theo convention có version/ngày nếu dùng chiến lược reindex qua alias (VD: `products_v2`, alias `products` trỏ tới bản mới nhất).

## Analyzer
- Chọn analyzer phù hợp ngôn ngữ nội dung (standard, hoặc analyzer riêng cho tiếng Việt/ngôn ngữ khác nếu cần xử lý dấu, từ ghép).
- Custom analyzer (tokenizer + filter) nếu cần yêu cầu tìm kiếm đặc thù (synonym, ngram cho autocomplete) — tự thiết kế và áp dụng khi yêu cầu tìm kiếm đã rõ (VD: "hỗ trợ tìm gần đúng/autocomplete"), nêu ngắn gọn tradeoff độ phức tạp/hiệu năng index đã chấp nhận trong báo cáo thay vì hỏi trước.

## Query DSL
- Dùng đúng loại query theo nhu cầu: `match`/`multi_match` cho full-text, `term`/`terms` cho exact match, `bool` để kết hợp must/should/filter (ưu tiên `filter` cho điều kiện không cần tính relevance score — nhanh hơn vì được cache).
- Tránh query kiểu wildcard/regex ở đầu chuỗi (`*abc`) — cực kỳ chậm, cân nhắc thiết kế lại mapping (n-gram) nếu cần kiểu tìm kiếm này thường xuyên.

## Aggregation
- Phân biệt bucket aggregation (group by) và metric aggregation (sum/avg/min/max) — kết hợp đúng thứ tự lồng nhau theo nhu cầu phân tích.
- Cân nhắc `cardinality` (approximate distinct count) thay vì đếm chính xác nếu dataset lớn và không cần độ chính xác tuyệt đối (đánh đổi tốc độ).

## Reindex Strategy
Khi cần đổi mapping (breaking change): tạo index mới, reindex dữ liệu cũ sang, chuyển alias sang index mới, xóa index cũ sau khi xác nhận ổn — KHÔNG sửa mapping trực tiếp trên index đang chạy (nhiều thay đổi mapping không cho phép sau khi tạo field).

## Shard & Replica (ghi chú, tradeoff nếu ảnh hưởng lớn)
Số shard quyết định lúc tạo index, khó đổi sau (phải reindex) — cân nhắc kỹ dựa trên dữ liệu dự kiến. Replica ảnh hưởng độ sẵn sàng và tốc độ đọc, không ảnh hưởng ghi.

## Test
Testcontainers Elasticsearch cho integration test — test mapping đúng kiểu dữ liệu mong đợi, test query trả kết quả đúng, test aggregation ra số liệu đúng.

## Ranh giới
Với index MỚI hoặc chưa có dữ liệu thật, tự thiết kế mapping/analyzer tốt nhất theo yêu cầu mà không cần hỏi. Không tự đổi mapping của index ĐANG CHẠY production có dữ liệu thật mà không có kế hoạch reindex — luôn trình bày kế hoạch migrate mapping, chờ user duyệt vì đây là thay đổi khó đảo ngược và có rủi ro downtime/mất khả năng đọc trong lúc reindex.
