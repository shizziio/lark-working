---
name: lark-env-check
description: 'Kiểm tra môi trường và công cụ để làm việc với Lark: node/npm/npx, go/python (tuỳ chọn), lark-cli (bản cài vs bản mới nhất), trạng thái auth, claude/codex CLI, và các skill lark-* đã cài cho từng agent. Dùng khi "check lark env", "kiểm tra lark cli", "lark có sẵn sàng chưa", hoặc trước khi cài/fanout.'
---

# lark-env-check

Chạy từ root project `lark-working`:

```bash
python3 scripts/lark/lark_setup.py check          # bảng OK/WARN/FAIL
python3 scripts/lark/lark_setup.py check --json   # cho agent parse
python3 scripts/lark/lark_setup.py status         # skill lark-* theo agent
```

Quy ước kết quả: `FAIL` = chặn (thiếu node/npm/lark-cli), `WARN` = nên xử lý (lark-cli cũ, chưa auth, thiếu skill cho agent).

Xử lý theo kết quả:
- lark-cli thiếu/cũ → skill `lark-install` (mục install).
- thiếu skill cho claude/codex → skill `lark-install` (mục fanout).
- chưa auth → báo user chạy `lark-cli config init --new` rồi `lark-cli auth login --recommend` (cần mở trình duyệt; chạy nền, trích URL gửi user). Không tự điền credential.
- Sau khi auth xong, dùng skill `lark-shared`.
