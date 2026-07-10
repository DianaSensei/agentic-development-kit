# Orchestration Guide: Feature Pipeline (Lead–Specialist)

## Cài đặt
Copy 4 file `.md` vào project của bạn:
```
your-project/.claude/agents/spec-writer.md
your-project/.claude/agents/db-schema-reviewer.md
your-project/.claude/agents/api-implementer.md
your-project/.claude/agents/test-generator.md
```
(Dùng `.claude/agents/` cấp project để share qua git cho cả team; dùng `~/.claude/agents/`
nếu chỉ muốn cá nhân bạn dùng.)

## Nguyên tắc quan trọng: RELAY, không phải BROADCAST
Vì các subagent **không share context với nhau**, lead-agent (chính là session bạn đang
chat) đóng vai trò người đưa thư — chỉ chuyển **phần liên quan** của output bước trước sang
prompt của bước sau, không chuyển nguyên JSON thô, không chuyển toàn bộ hội thoại.

## Luồng chạy (tuần tự, có chủ đích)

```
User request (raw)
      │
      ▼
[spec-writer]  ──► JSON: acceptance_criteria, entities_affected, open_questions
      │
      │  Lead-agent: NẾU open_questions không rỗng → dừng lại, hỏi user xác nhận
      │  trước khi đi tiếp. Đây là checkpoint bắt buộc, không bỏ qua.
      ▼
[db-schema-reviewer]  ◄── relay: entities_affected + acceptance_criteria + assumptions
      │
      ▼ JSON: erd_mermaid, entities, breaking_changes, migration_notes
      │
      │  Lead-agent: NẾU breaking_changes không rỗng → hiển thị cho user xem trước,
      │  vì đây là quyết định ảnh hưởng dữ liệu thật.
      ▼
[api-implementer]  ◄── relay: acceptance_criteria + entities + breaking_changes + migration_notes
      │
      ▼ JSON: files_changed, endpoints, kafka_events, todo_for_tests
      │
      ▼
[test-generator]  ◄── relay: acceptance_criteria + todo_for_tests + files_changed + kafka_events
      │
      ▼ JSON: test_files, test_run_result
      │
      │  Lead-agent: NẾU test_run_result = FAIL → không tạo PR, báo lại user + gợi ý
      │  gọi lại api-implementer với thông tin lỗi cụ thể (vòng lặp sửa lỗi có kiểm soát,
      │  không tự động lặp vô hạn).
      ▼
Lead-agent tổng hợp: tóm tắt cho user, đề xuất tạo PR nếu mọi thứ pass.
```

## Prompt mẫu để bạn gõ với lead-agent (Claude Code)

```
Chạy pipeline cho feature "Hủy đơn hàng trong 30 phút":
1. Gọi subagent spec-writer với yêu cầu: "Khách được hủy đơn trong 30 phút sau khi đặt,
   nếu đơn chưa processing. Khi hủy phải hoàn tiền và báo kho hủy giữ hàng."
2. Nếu spec-writer có open_questions, dừng lại và hỏi tôi trước.
3. Sau khi tôi xác nhận, gọi db-schema-reviewer với entities_affected + acceptance_criteria
   từ bước 1.
4. Nếu có breaking_changes, hiển thị cho tôi xem trước khi tiếp tục.
5. Gọi api-implementer với acceptance_criteria + entities + breaking_changes + migration_notes.
6. Gọi test-generator với acceptance_criteria + todo_for_tests + files_changed.
7. Tổng hợp kết quả cuối, nói rõ test_run_result và đề xuất bước tiếp theo.
```

## Xử lý trường hợp phụ thuộc chéo / conflict file
- Nếu 2 bước cùng chạm 1 file (ví dụ db-schema-reviewer và api-implementer đều sửa
  `OrderEntity.java`), PHẢI chạy tuần tự (đã thiết kế đúng ở trên) — không parallel.
- Nếu sau này bạn muốn parallel hóa các phần thực sự độc lập (ví dụ 2 feature khác module),
  cân nhắc `isolation: worktree` trong frontmatter của subagent ghi file, để mỗi subagent
  làm việc trên 1 git worktree riêng, tránh đụng độ.

## Checklist trước khi merge (lead-agent tự kiểm hoặc nhắc bạn)
- [ ] Không còn open_questions chưa xác nhận
- [ ] breaking_changes đã được user duyệt tường minh
- [ ] test_run_result = PASS
- [ ] Transaction boundary đúng (đặc biệt update DB + publish Kafka event)
- [ ] Cache invalidation strategy rõ ràng, không stale data
