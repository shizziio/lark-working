# lark-working Context

## What This Project Is
Workspace làm việc với Lark cho nhiều phòng ban. Mỗi phòng ban là một sub-repo git độc lập nằm dưới root.

## Components
- `hr/`, `sales/`, `finance/`, `ops/`: sub-repo theo phòng ban, mỗi nơi có `CLAUDE.md` riêng (`AGENTS.md` là symlink).

## Operational Notes For Other Agents
- Root chỉ track cấu hình chung; sub-repo được ignore ở root, commit trong từng repo.
- Tương tác Lark qua `lark-cli` / skill `lark-*`; không hardcode token.
- Không commit/push hoặc start/stop server khi chưa được yêu cầu.
