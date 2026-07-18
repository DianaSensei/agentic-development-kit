---
name: code-review-skill
description: Checklist review code khách quan trước khi báo hoàn thành — convention chung, clean-code, checklist riêng theo công nghệ đã dùng. Đây là bước TỰ KIỂM Claude LUÔN chủ động chạy ở bước cuối trước khi báo hoàn thành với mọi thay đổi có code — không cần user yêu cầu riêng. KHÔNG dùng khi user chủ động yêu cầu review diff/PR ("review this", "/code-review") — dùng skill `code-review`/`review` built-in cho trường hợp đó.
---

# Code Review Checklist

## Discover

Đọc `CLAUDE.md`/convention hiện có. Xác định công nghệ THỰC SỰ liên quan tới thay đổi vừa làm (không cần áp toàn bộ checklist bên dưới nếu không liên quan) qua bằng chứng cụ thể trong file đã đổi.

## Checklist chung (mọi thay đổi)

- Đặt tên rõ ràng, nhất quán convention.
- Không trùng lặp lớn (DRY), không hàm/class ôm quá nhiều trách nhiệm.
- Không hardcode secret/credential/API key.
- Exception xử lý rõ ràng, không nuốt lỗi im lặng.
- Comment cần thiết cho logic phức tạp, không comment thừa.

## Checklist riêng theo công nghệ (chỉ áp dụng phần liên quan tới thay đổi)

**Java/Spring**: transaction boundary đúng, không N+1, exception handling theo convention, đặt log tại trước/sau critical session để dễ dàng tracing, debug, tránh các issue liên quan về self invoke của aop, ưu tiên dùng abstraction của framework thay vì tight-coupling vào các specific dependencies, các configuration phải được cấu hình để dễ thay đổi thay vì hardcode, tránh magic code.

**Kafka**: idempotency ở consumer cho các consumer quan trọng, delivery semantic đúng như đã thiết kế, dead-letter có cấu hình nếu cần, partition key hợp lý.

**RabbitMQ**: ack/nack xử lý đúng, DLX cấu hình nếu cần, prefetch hợp lý, không giữ connection/channel quá lâu không cần thiết.

**Redis**: TTL có đặt cho cache (không cache vô thời hạn vô tình), lock có TTL (tránh deadlock vĩnh viễn), lock giải phóng đúng chủ sở hữu.

**Elasticsearch**: mapping field đúng kiểu (text vs keyword), không dùng wildcard đầu chuỗi trong query thường xuyên, không sửa mapping trực tiếp trên index production.

**Database (RDBMS/Mongo)**: index đúng cột dùng filter/join/sort, isolation level phù hợp nghiệp vụ, migration backward-compatible, không có deadlock tiềm ẩn (lock theo thứ tự nhất quán).

**Google Pub/Sub**: ack deadline đủ cho thời gian xử lý thực tế, idempotency ở subscriber, dead-letter topic cấu hình nếu cần.

**API Contract (REST/RPC/Message)**: response/message khớp đúng contract đã chốt (`api-contract-skill`), không có breaking change âm thầm với schema/proto field.

**Tauri/React**: path handling đúng API (không path traversal), capabilities least- privilege khai báo đủ cho command đang dùng, plugin chuẩn cho dialog, `#[cfg(target_os)]` đủ 3 OS, command Rust không panic (trả `Result`), listener event được cleanup khi unmount, React đủ loading/error/empty state.

**Data/Storage local (Tauri offline)**: migration SQLite chạy được lúc app khởi động và có fallback nếu fail (không làm app không mở được), TTL/schema key-value nhất quán, không lưu blob lớn vào SQLite nếu `tauri-plugin-fs` phù hợp hơn.

**UI/UX**: nhất quán với design system hiện có, có xử lý trạng thái lỗi/loading rõ ràng cho user, đủ accessibility cơ bản (label, contrast, điều hướng bàn phím).

## Lưu ý về tính khách quan

Nếu đây là tự-review (cùng agent vừa viết code), độ khách quan thấp hơn có 1 phiên/agent riêng biệt review. Issue nghiêm trọng (severity cao) PHẢI sửa trước khi báo hoàn thành, không bỏ qua chỉ vì "đây chỉ là tự-review". Muốn khách quan hơn, đề xuất user mở 1 phiên Claude Code mới (không chia sẻ context) để review độc lập.
