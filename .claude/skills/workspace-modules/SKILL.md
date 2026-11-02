---
name: workspace-modules
description: 'Chọn và clone các module (sub-repo phòng ban) vào workspace lark-working theo chức năng của người dùng. Liệt kê module từ modules.json, hỏi user chọn, clone đúng vào dự án, cập nhật .gitignore. Dùng khi "clone module", "lấy repo phòng ban", "tôi làm bên sales/hr/finance/ops", "setup workspace cho tôi", hoặc user mới nhận dự án.'
---

# workspace-modules

Nguồn sự thật: `modules.json` ở root (tên, path, `repo` URL, phòng ban, `functions`, mô tả). Script: `python3 scripts/modules.py` (Windows: `py -3 scripts\modules.py`).

## Quy trình
1. **Liệt kê:** `python3 scripts/modules.py list --json` (có thể lọc `--function <vai trò>`). Mỗi module có `state`: `cloned` | `dir-exists` | `not-cloned` | `no-repo`.
2. **Hỏi user** bằng AskUserQuestion: trước hết hỏi chức năng/vai trò (lấy từ trường `functions`) để gợi ý, rồi cho chọn module quan tâm (multiSelect, ghi rõ mô tả + trạng thái). Tối đa 4 lựa chọn mỗi câu: nếu nhiều module hơn thì lọc theo chức năng/phòng ban trước hoặc chia nhiều câu. Không tự chọn thay user.
3. **Dry-run rồi clone:** `python3 scripts/modules.py clone <name>... --dry-run`, xác nhận, rồi chạy thật (bỏ `--dry-run`). Script chỉ nhận URL `https://`, `ssh://`, `git://`, `git@host:`, bỏ qua module đã có, tự thêm `/<path>/` vào `.gitignore` root.
4. **Module `no-repo`:** chưa có URL trong `modules.json`, báo user nhờ owner điền `repo` (không tự bịa URL, không ghi token vào URL).
5. **Sau clone:** chạy `python3 scripts/lark/lark_setup.py check` (skill `lark-env-check`) và nhắc user đọc `<module>/CLAUDE.md` + `<module>/docs/lark-resources.md`.
6. Cập nhật sau: `python3 scripts/modules.py pull [name...]` (chỉ `--ff-only`).

## Quy tắc
- Không commit/push thay user. Module là git repo riêng, root chỉ ignore chúng.
- Thêm module mới: thêm entry vào `modules.json` (name, path tương đối, repo, department, functions, description).
