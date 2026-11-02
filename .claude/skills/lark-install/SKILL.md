---
name: lark-install
description: 'Cài lark-cli (npm @larksuite/cli) và fanout bộ skill lark-* từ repo larksuite/cli sang Claude Code và/hoặc Codex, global hoặc project-level. Dùng khi "cài lark cli", "setup lark cho codex/claude", "fanout lark skills", "cập nhật lark cli".'
---

# lark-install

Luôn chạy `lark-env-check` trước. Mọi lệnh hỗ trợ `--dry-run`; **hỏi user agent/scope rồi mới chạy thật** (cài global là thay đổi ngoài project).

## 1. Cài / cập nhật lark-cli
```bash
python3 scripts/lark/lark_setup.py install --dry-run
python3 scripts/lark/lark_setup.py install        # npm i -g @larksuite/cli@latest, bỏ qua nếu đã mới nhất
```

## 2. Fanout skill (nguồn duy nhất: harness `core/plugins/lark`, đồng bộ từ github.com/larksuite/cli)
```bash
python3 scripts/lark/lark_setup.py sync-upstream --dry-run   # xem thay đổi upstream
python3 scripts/lark/lark_setup.py sync-upstream             # mirror vào harness, bump version + CHANGELOG
python3 scripts/lark/lark_setup.py fanout --agent both --scope global [--dry-run]
python3 scripts/lark/lark_setup.py fanout --agent codex --scope project   # copy vào repo
```
- `--agent`: `claude` | `codex` | `both`. Codex đọc `~/.agents/skills`, Claude đọc `~/.claude/skills` (link sang `~/.agents/skills`).
- `global`: symlink (Windows: symlink → junction → copy, in ra cách đã dùng). `project`: copy, để repo tự đủ khi clone.
- Sau `sync-upstream` chạy `harness index` ở HARNESS_ROOT và cập nhật version trong `.harness/project.yaml` + `lock.yaml`.
- Windows: dùng `scripts\lark\lark-setup.cmd <lệnh>` hoặc `py -3 scripts\lark\lark_setup.py <lệnh>`.

## 3. Xác nhận
```bash
python3 scripts/lark/lark_setup.py status && python3 scripts/lark/lark_setup.py check
```

## Lưu ý
- Skill `lark-*` là shared asset (harness `plugin:lark`): **không sửa tại project**, chỉ cập nhật bằng cách fanout lại hoặc `harness-sync`.
- Đăng nhập Lark (`lark-cli config init --new`, `lark-cli auth login --recommend`) cần user thao tác trình duyệt; không tự làm thay.
