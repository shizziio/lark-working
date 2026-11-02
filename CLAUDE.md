# lark-working

Workspace làm việc với **Lark** theo kiến trúc **sub-repository theo phòng ban**.

## Cấu trúc
| Sub-repo | Phòng ban | Ghi chú |
|---|---|---|
| `hr/` | Nhân sự | git repo riêng |
| `sales/` | Kinh doanh | git repo riêng |
| `finance/` | Tài chính | git repo riêng |
| `ops/` | Vận hành | git repo riêng |

Mỗi sub-repo có `CLAUDE.md` riêng (+ `AGENTS.md` là symlink tới `CLAUDE.md`). Root repo chỉ track cấu hình chung (`_bmad/`, `.harness/`, `docs/`); các sub-repo được `.gitignore` ở root.

## Công cụ
- **BMAD**: config ở `_bmad/config.toml`, output ở `_bmad-output/`, tài liệu dự án ở `docs/`. Skill `bmad-*` dùng qua harness (global).
- **Lark**: skill `lark-*` và `harness-lark-*` (wiki/base sync, integration).
- **Harness**: manifest `.harness/project.yaml`; ngữ cảnh cho agent khác ở `.harness/CONTEXT.md`.

## Quy tắc
- Không commit/push khi chưa được yêu cầu rõ ràng.
- Kiểm thử bằng lệnh nhắm mục tiêu, không khởi động cả app.
- Không start/stop/restart server tự động.
- Thêm phòng ban mới: tạo thư mục, `git init`, thêm `CLAUDE.md` + symlink `AGENTS.md`, rồi khai báo component trong `.harness/project.yaml` và `.gitignore` root.

## Lark setup
- `python3 scripts/lark/lark_setup.py check|install|sync-upstream|fanout|status` (Windows: `scripts\lark\lark-setup.cmd`) — dùng qua skill `lark-env-check`, `lark-install` (Claude: `.claude/skills/`, Codex: `.agents/skills/` symlink).
