---
name: testcontainers-skill
description: Kiến thức chuyên sâu setup/chạy Testcontainers cho integration test — dependency, lifecycle container (singleton pattern, reuse, cleanup), wait strategy, network giữa nhiều container, tích hợp CI. KHÔNG bao gồm kịch bản test nghiệp vụ theo từng hạ tầng (xem database-skill/kafka-skill/rabbitmq-skill/redis-skill/elasticsearch-skill). Dùng khi cần dựng hạ tầng thật (container) cho integration test thay vì mock.
---

# Testcontainers — Setup & Chạy Container cho Integration Test

## Discover trước khi setup
Đọc `pom.xml`/`build.gradle` (hoặc `package.json` nếu dùng binding Node) xem đã có
dependency Testcontainers chưa, module nào đã dùng (postgresql/mysql/kafka/rabbitmq/
elasticsearch/...). Xác nhận Docker daemon đang chạy trên máy/CI (`docker info`). Đọc
config test hiện có (`application-test.yml`, `docker-compose.test.yml` nếu có) trước khi
thêm mới — không tạo trùng cơ chế đã tồn tại.

## Khi nào dùng Testcontainers / KHÔNG dùng
Dùng khi integration test cần hành vi **thật** của hạ tầng (SQL dialect thật, Kafka
delivery semantic thật, TTL Redis thật...) mà mock/in-memory (H2, embedded Kafka) không
tái hiện đúng — đặc biệt khi trước đó dự án từng gặp lỗi do khác biệt giữa mock và prod.
KHÔNG dùng cho unit test thuần business logic (mock dependency theo `java-spring-skill`) —
Testcontainers chỉ ở tầng integration test, chạy chậm hơn nên không nên lạm dụng cho mọi
test case.

## Setup cơ bản (JVM/JUnit5)
1. Thêm `testcontainers-bom` + module tương ứng (`postgresql`, `kafka`, `rabbitmq`,
   `elasticsearch`...) đúng version, không tự ý nâng version khác với các dependency test
   khác trong project.
2. Dùng `@Testcontainers` + `@Container` (JUnit5 extension) thay vì tự quản lý lifecycle
   thủ công bằng `start()`/`stop()` rải rác — extension tự đảm bảo cleanup kể cả khi test
   fail.
3. Pin version image cụ thể (VD: `postgres:15.4`), KHÔNG dùng tag `latest` — tránh test
   flaky/không tái lập được khi image đổi hành vi giữa các lần chạy.

## Lifecycle & Hiệu năng — vấn đề thường gặp nhất
- **Container khởi động lại cho mỗi test class** là nguyên nhân hàng đầu khiến test suite
  chậm (mỗi container mất vài giây tới chục giây để healthy). Ưu tiên **singleton container
  pattern**: 1 container static dùng chung cho toàn bộ test suite (base test class hoặc
  JUnit5 extension riêng), start 1 lần, không `stop()` giữa các test class — để Ryuk (xem
  dưới) dọn khi JVM test kết thúc.
- **Container reuse giữa các lần chạy test cục bộ** (không phải CI): bật
  `testcontainers.reuse.enable=true` trong `~/.testcontainers.properties` và gọi
  `.withReuse(true)` khi cần lặp lại chạy test nhanh trong lúc dev — KHÔNG bật reuse mặc
  định trong CI vì container có thể mang state cũ giữa các build.
- **Ryuk (resource reaper)**: Testcontainers tự chạy container Ryuk để dọn container/
  network/volume mồ côi khi JVM test process chết đột ngột — không tắt Ryuk
  (`TESTCONTAINERS_RYUK_DISABLED=true`) trừ khi CI runner không cho phép container quản lý
  container khác (privileged), vì tắt Ryuk dễ để lại container rác tích lũy trên máy CI.

## Wait Strategy — tránh test flaky do container "chưa sẵn sàng"
Container ở trạng thái "running" không đồng nghĩa service bên trong đã sẵn sàng nhận kết
nối — luôn khai báo wait strategy đúng thay vì dựa vào delay cố định (`Thread.sleep`):
- `Wait.forListeningPort()` cho service chỉ cần mở port (yếu, dễ false positive nếu app
  mở port trước khi thực sự init xong).
- `Wait.forLogMessage(...)` khớp log dòng báo hiệu đã sẵn sàng (VD: "database system is
  ready to accept connections") — chính xác hơn `forListeningPort`.
- `Wait.forHealthcheck()` nếu image có healthcheck sẵn trong Dockerfile.
- Tăng `startupTimeout` khi chạy trên CI runner yếu/chậm hơn máy dev, tránh timeout giả do
  máy chậm chứ không phải container lỗi thật.

## Network giữa nhiều container
Khi test cần nhiều container giao tiếp với nhau (VD: app container gọi Kafka + Zookeeper,
hoặc service A gọi service B) — dùng chung `Network.newNetwork()` và đặt
`.withNetworkAliases(...)` cho từng container, KHÔNG dùng `localhost`/port map từ container
này sang container khác (chỉ host test JVM mới thấy được port map ra ngoài qua
`getMappedPort()`).

## Tích hợp CI
- CI runner cần Docker daemon khả dụng (Docker-in-Docker, hoặc mount
  `/var/run/docker.sock` — tuỳ chính sách bảo mật CI, không tự ý đổi cấu hình runner mà
  không báo vì ảnh hưởng tới các job khác).
- Kiểm tra resource limit CI (RAM/CPU) đủ cho số container chạy song song — nhiều
  Testcontainers module cùng lúc (Postgres + Kafka + Elasticsearch...) trên runner nhỏ dễ
  timeout do đói tài nguyên chứ không phải lỗi code.
- Nếu CI chạy test song song nhiều job, kiểm tra port conflict — Testcontainers tự map
  random port ra host nên thường không xung đột, nhưng nếu project tự pin port cố định thì
  cần rà lại.

## Issue thường gặp trong thực tế
- **Test pass local, fail CI**: thường do wait strategy yếu (`forListeningPort`) hoặc
  `startupTimeout` mặc định quá ngắn so với runner CI chậm hơn máy dev.
- **Container rác tích lũy trên máy CI/dev**: do tắt Ryuk hoặc `kill -9` process test giữa
  chừng khiến cleanup không kịp chạy — dọn định kỳ bằng `docker system prune` nếu phát
  hiện, không phải lỗi code cần fix.
- **Image pull chậm/timeout lần đầu trên CI**: cân nhắc pre-pull image trong bước cache
  riêng của pipeline CI nếu ảnh hưởng đáng kể thời gian build.

## Ranh giới
Skill này chỉ lo **cơ chế setup/chạy container** (dependency, lifecycle, wait strategy,
network, CI). Kịch bản test cụ thể theo từng hạ tầng (test đúng SQL dialect gì, test
delivery semantic Kafka nào, test TTL Redis ra sao, test mapping Elasticsearch gì) → phối
hợp với skill tương ứng: `database-skill`, `kafka-skill`, `rabbitmq-skill`, `redis-skill`,
`elasticsearch-skill`. Unit test thuần (mock, không container) → `java-spring-skill`.
