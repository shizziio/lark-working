#!/usr/bin/env python3
"""modules — list / clone / pull the department modules (sub-repos) declared in modules.json.

Stdlib only; macOS, Linux, Windows.
  modules.py list   [--function F] [--json]
  modules.py clone  NAME... | --all  [--dry-run] [--branch B]
  modules.py pull   [NAME...]
Options: --root DIR (default: project root), --manifest FILE (default: <root>/modules.json)
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
URL_OK = re.compile(r"^(https://|ssh://|git://|git@[\w.\-]+:)[^\s]+$")


def load(root, manifest):
    f = Path(manifest) if manifest else root / "modules.json"
    data = json.loads(f.read_text(encoding="utf-8"))
    for m in data["modules"]:
        p = Path(m["path"])
        if p.is_absolute() or ".." in p.parts or not m["name"].replace("-", "").replace("_", "").isalnum():
            sys.exit(f"invalid module entry: {m['name']!r} path={m['path']!r}")
        if m.get("repo") and not URL_OK.match(m["repo"]):
            sys.exit(f"invalid repo URL for {m['name']}: only https/ssh/git URLs allowed")
    return data["modules"]


def state(root, m):
    d = root / m["path"]
    if (d / ".git").exists():
        return "cloned"
    if d.exists() and any(d.iterdir()):
        return "dir-exists"
    return "not-cloned" if m.get("repo") else "no-repo"


def git(*a):
    exe = shutil.which("git")
    if not exe:
        sys.exit("git not found")
    return subprocess.call([exe, *a])


def ensure_ignored(root, rel):
    gi = root / ".gitignore"
    line = "/" + Path(rel).as_posix().strip("/") + "/"
    text = gi.read_text(encoding="utf-8") if gi.exists() else ""
    if line not in text.splitlines():
        gi.write_text(text + ("" if text.endswith("\n") or not text else "\n") + line + "\n", encoding="utf-8")
        print(f"  .gitignore += {line}")


def cmd_list(a, root, mods):
    rows = [m for m in mods if not a.function or a.function in m.get("functions", [])]
    out = [{**m, "state": state(root, m)} for m in rows]
    if a.json:
        print(json.dumps(out, ensure_ascii=False))
        return 0
    for m in out:
        print(f"{m['name']:<10} [{m['state']:<10}] {m.get('department','')} — {m.get('description','')}"
              f"  (functions: {', '.join(m.get('functions', []))})")
    return 0


def cmd_clone(a, root, mods):
    by = {m["name"]: m for m in mods}
    names = list(by) if a.all else a.names
    if not names:
        sys.exit("give module names or --all")
    unknown = [n for n in names if n not in by]
    if unknown:
        sys.exit(f"unknown module(s): {', '.join(unknown)} (known: {', '.join(by)})")
    rc = 0
    for n in names:
        m, st = by[n], state(root, by[n])
        if st in ("cloned", "dir-exists"):
            print(f"{n}: already present ({st}) — skip")
        elif st == "no-repo":
            print(f"{n}: chưa có `repo` trong modules.json — nhờ owner điền URL rồi chạy lại")
            rc = 1
        else:
            cmd = ["clone"] + (["--branch", a.branch] if a.branch else []) + ["--", m["repo"], str(root / m["path"])]
            print(("[dry-run] git " if a.dry_run else "+ git ") + " ".join(cmd))
            if not a.dry_run:
                if git(*cmd):
                    rc = 1
                    continue
        if not a.dry_run and st != "no-repo":
            ensure_ignored(root, m["path"])
    return rc


def cmd_pull(a, root, mods):
    rc = 0
    for m in mods:
        if (a.names and m["name"] not in a.names) or state(root, m) != "cloned":
            continue
        print(f"== {m['name']}")
        rc |= 1 if git("-C", str(root / m["path"]), "pull", "--ff-only") else 0
    return rc


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--manifest")
    sub = ap.add_subparsers(dest="cmd", required=True)
    l = sub.add_parser("list"); l.add_argument("--function"); l.add_argument("--json", action="store_true"); l.set_defaults(fn=cmd_list)
    c = sub.add_parser("clone"); c.add_argument("names", nargs="*"); c.add_argument("--all", action="store_true")
    c.add_argument("--dry-run", action="store_true"); c.add_argument("--branch"); c.set_defaults(fn=cmd_clone)
    p = sub.add_parser("pull"); p.add_argument("names", nargs="*"); p.set_defaults(fn=cmd_pull)
    a = ap.parse_args()
    root = Path(a.root).resolve()
    sys.exit(a.fn(a, root, load(root, a.manifest)))


if __name__ == "__main__":
    main()
