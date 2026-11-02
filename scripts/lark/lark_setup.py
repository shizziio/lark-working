#!/usr/bin/env python3
"""lark_setup — check env/tools, install lark-cli, sync upstream skills, fan out to claude/codex.

Stdlib only; runs on macOS, Linux and Windows (Python >= 3.8).

  lark_setup.py check [--json]
  lark_setup.py install [--dry-run]            npm i -g @larksuite/cli (skipped if up to date)
  lark_setup.py sync-upstream [--dry-run]      larksuite/cli skills/ -> harness core/plugins/lark (source of truth)
  lark_setup.py fanout --agent claude|codex|both [--scope global|project] [--dry-run]
      global : link ~/.agents/skills/lark-* -> harness copy (codex reads this);
               ~/.claude/skills/lark-* -> ~/.agents/skills/lark-*
               link strategy: symlink -> (Windows) junction -> copy
      project: COPY into ./.claude/skills and ./.agents/skills (links to ~ would break on clone)
  lark_setup.py status                         lark-* skills per agent
"""
import argparse
import filecmp
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

PKG = "@larksuite/cli"
UPSTREAM = "https://github.com/larksuite/cli"
OWN = {"lark-env-check", "lark-install"}  # this project's own skills, not part of the lark bundle
ROOT = Path(__file__).resolve().parents[2]  # project root
IS_WIN = os.name == "nt"
HOME = Path.home()


# ----------------------------------------------------------------- helpers
def have(tool):
    return shutil.which(tool) is not None


def out(cmd, timeout=60):
    """Run a command (no shell), return first line of combined output or None."""
    exe = shutil.which(cmd[0])
    if not exe:
        return None
    try:
        p = subprocess.run([exe] + cmd[1:], capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = (p.stdout + p.stderr).strip()
    return text.splitlines()[0] if text else ""


def full_out(cmd, timeout=60):
    exe = shutil.which(cmd[0])
    if not exe:
        return None
    try:
        p = subprocess.run([exe] + cmd[1:], capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return p.returncode, p.stdout + p.stderr


def run(cmd, dry):
    print(("[dry-run] " if dry else "+ ") + " ".join(map(str, cmd)))
    if dry:
        return 0
    exe = shutil.which(cmd[0]) or cmd[0]
    return subprocess.call([exe] + [str(c) for c in cmd[1:]])


def semver(text):
    m = re.search(r"\d+\.\d+\.\d+", text or "")
    return m.group(0) if m else None


def harness_root():
    env = os.environ.get("HARNESS_ROOT")
    if env:
        return Path(env)
    lock = ROOT / ".harness" / "lock.yaml"
    if lock.exists():
        m = re.search(r"source:\s*git\+file://(\S+)", lock.read_text(encoding="utf-8"))
        if m:
            p = m.group(1)
            if re.match(r"^/[A-Za-z]:", p):  # file:///C:/x -> C:/x
                p = p[1:]
            return Path(p)
    return None


def agent_dir(agent, base):
    # claude -> <base>/.claude/skills ; codex -> <base>/.agents/skills
    return Path(base) / (".claude" if agent == "claude" else ".agents") / "skills"


def is_link(p):
    p = Path(p)
    isj = getattr(os.path, "isjunction", lambda _: False)
    return p.is_symlink() or isj(p)


def all_on_path(name):
    """Every distinct executable `name` on PATH (by real path), in PATH order."""
    exts = [""] + (os.environ.get("PATHEXT", ".EXE;.CMD;.BAT").lower().split(";") if IS_WIN else [])
    seen, found = set(), []
    for d in os.environ.get("PATH", "").split(os.pathsep):
        for e in exts:
            f = Path(d) / (name + e)
            if f.is_file() and os.access(f, os.X_OK):
                rp = str(f.resolve())
                if rp not in seen:
                    seen.add(rp)
                    found.append(str(f))
    return found


def lark_skills(d):
    if not d.is_dir():
        return []
    return sorted(x for x in d.iterdir() if x.name.startswith("lark-") and x.name not in OWN)


def remove_any(p):
    p = Path(p)
    if p.is_symlink():
        p.unlink()
    elif is_link(p):  # junction
        os.rmdir(p)
    elif p.is_dir():
        shutil.rmtree(p)
    elif p.exists():
        p.unlink()


def make_link(target, link, dry):
    """Link `link` -> `target` dir. Returns mode used: symlink|junction|copy."""
    link = Path(link)
    real = (link.parent / target).resolve()  # target may be relative to the link's parent
    if dry:
        print(f"[dry-run] link {link} -> {target}")
        return "symlink"
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink() or link.exists():
        remove_any(link)
    try:
        os.symlink(str(target), link, target_is_directory=True)
        return "symlink"
    except OSError:
        if not IS_WIN:
            raise
    r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(real)],
                       capture_output=True, text=True)
    if r.returncode == 0:
        return "junction"
    shutil.copytree(real, link)
    return "copy"


# ----------------------------------------------------------------- check
class Report:
    def __init__(self, as_json):
        self.rows, self.fail, self.as_json = [], False, as_json

    def add(self, level, name, detail):
        self.rows.append({"level": level, "name": name, "detail": detail})
        self.fail |= level == "FAIL"
        if not self.as_json:
            print(f"{level:<5} {name:<14} {detail}")


def cmd_check(args):
    r = Report(args.json)
    for t, flag in (("node", ["-v"]), ("npm", ["-v"]), ("npx", ["-v"])):
        v = out([t] + flag)
        r.add("OK", t, v) if v is not None else r.add("FAIL", t, "missing — install Node.js (https://nodejs.org)")
    nv = out(["node", "-v"])
    if nv and int(re.sub(r"\D.*", "", nv.lstrip("v")) or 0) < 18:
        r.add("FAIL", "node-version", f"need >=18, have {nv}")
    for t, flag in (("go", ["version"]), ("python3", ["-V"]), ("git", ["--version"])):
        v = out([t] + flag)
        if v is not None:
            r.add("OK", t, v)
        else:
            r.add("WARN", t, "optional (go/python only for building lark-cli from source)" if t != "git" else "missing")
    r.add("OK", "python", f"{sys.version.split()[0]} (running this script)")

    if have("lark-cli"):
        cur = semver(out(["lark-cli", "--version"]))
        lat = semver(out(["npm", "view", PKG, "version"]))
        if lat and cur != lat:
            r.add("WARN", "lark-cli", f"installed {cur}, latest {lat} — run: lark_setup.py install")
        else:
            r.add("OK", "lark-cli", f"{cur} ({shutil.which('lark-cli')})")
        dups = all_on_path("lark-cli")
        if len(dups) > 1:
            r.add("WARN", "lark-cli-path", f"{len(dups)} installs on PATH (first wins): " + "; ".join(dups))
        res = full_out(["lark-cli", "auth", "status"])
        if res and res[0] == 0 and '"appId"' in res[1]:
            r.add("OK", "lark-auth", "app configured")
        else:
            r.add("WARN", "lark-auth", "not configured: lark-cli config init --new && lark-cli auth login --recommend")
    else:
        r.add("FAIL", "lark-cli", "not installed — run: lark_setup.py install")

    for a in ("claude", "codex"):
        v = out([a, "--version"])
        r.add("OK", a, v) if v is not None else r.add("WARN", a, f"not found (needed for --agent {a})")

    for a in ("claude", "codex"):
        g, p = len(lark_skills(agent_dir(a, HOME))), len(lark_skills(agent_dir(a, ROOT)))
        if g + p:
            r.add("OK", f"skills:{a}", f"global={g} project={p}")
        else:
            r.add("WARN", f"skills:{a}", f"no lark-* skills — run: lark_setup.py fanout --agent {a}")

    for a in ("claude", "codex"):  # link audit
        items = lark_skills(agent_dir(a, HOME))
        if not items:
            continue
        copies = [x for x in items if not is_link(x) and x.is_dir()]
        broken = [x for x in items if is_link(x) and not x.exists()]
        ends = {}
        for x in items:
            if is_link(x) and x.exists():
                k = str(x.resolve().parent.parent)
                ends[k] = ends.get(k, 0) + 1
        if broken:
            r.add("FAIL", f"links:{a}", f"{len(broken)} broken link(s)")
        if copies:
            r.add("WARN", f"links:{a}", f"{len(copies)} skill(s) are copies, not links (will drift)")
        if ends:
            r.add("OK", f"links:{a}", "links resolve to " + max(ends, key=ends.get))

    if args.json:
        print(json.dumps(r.rows, ensure_ascii=False))
    return 1 if r.fail else 0


# ----------------------------------------------------------------- install
def cmd_install(args):
    if not have("npm"):
        print("npm missing — run check", file=sys.stderr)
        return 1
    cur = semver(out(["lark-cli", "--version"])) if have("lark-cli") else None
    lat = semver(out(["npm", "view", PKG, "version"]))
    if cur and cur == lat:
        print(f"lark-cli {cur} already latest")
        return 0
    print(f"lark-cli: {cur or 'none'} -> {lat or 'latest'}")
    return run(["npm", "install", "-g", f"{PKG}@latest"], args.dry_run)


# ----------------------------------------------------------------- sync-upstream
def tree_files(base):
    base = Path(base)
    return {p.relative_to(base).as_posix(): p for p in base.rglob("*") if p.is_file()}


def cmd_sync(args):
    hr = harness_root()
    plugin = hr / "core" / "plugins" / "lark" if hr else None
    if not plugin or not (plugin / "skills").is_dir():
        print(f"harness plugin not found: {plugin} (set HARNESS_ROOT)", file=sys.stderr)
        return 1
    if not have("git"):
        print("git missing", file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory() as tmp:
        up = Path(tmp) / "up"
        if subprocess.call([shutil.which("git"), "clone", "-q", "--depth", "1", UPSTREAM, str(up)]):
            return 1
        sha = out(["git", "-C", str(up), "rev-parse", "--short", "HEAD"])
        pkg = json.loads((up / "package.json").read_text(encoding="utf-8"))
        cliv = pkg.get("version")
        print(f"upstream {UPSTREAM} @ {sha} (cli {cliv})")
        src, dst = tree_files(up / "skills"), tree_files(plugin / "skills")
        added = [k for k in src if k not in dst]
        removed = [k for k in dst if k not in src]
        changed = [k for k in src if k in dst and not filecmp.cmp(src[k], dst[k], shallow=False)]
        print(f"  added: {len(added)}  changed: {len(changed)}  deleted: {len(removed)}")
        if args.dry_run:
            print(f"[dry-run] would mirror into {plugin / 'skills'}, bump plugin.json, append CHANGELOG")
            return 0
        shutil.rmtree(plugin / "skills")
        shutil.copytree(up / "skills", plugin / "skills")
    pj = plugin / ".claude-plugin" / "plugin.json"
    meta = json.loads(pj.read_text(encoding="utf-8"))
    old = meta["version"]
    major, minor = (int(x) for x in old.split(".")[:2])
    new = f"{major}.{minor + 1}.0"
    meta["version"] = new
    pj.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    n = sum(1 for d in (plugin / "skills").iterdir() if d.is_dir())
    cl = plugin / "CHANGELOG.md"
    lines = cl.read_text(encoding="utf-8").splitlines()
    entry = ["", f"## [{new}] - {date.today().isoformat()}",
             f"- Sync từ {UPSTREAM} @ {sha} (lark-cli {cliv}): {n} skill, mirror --delete."]
    cl.write_text("\n".join(lines[:1] + entry + lines[1:]) + "\n", encoding="utf-8")
    print(f"plugin:lark {old} -> {new} ({n} skills). Next: run `harness index` in {hr}")
    return 0


# ----------------------------------------------------------------- fanout
def cmd_fanout(args):
    hr = harness_root()
    skills = hr / "core" / "plugins" / "lark" / "skills" if hr else None
    if not skills or not skills.is_dir():
        print(f"harness plugin not found: {skills} (set HARNESS_ROOT)", file=sys.stderr)
        return 1
    agents = ["claude", "codex"] if args.agent == "both" else [args.agent]
    dry = args.dry_run
    for a in agents:
        base = ROOT if args.scope == "project" else HOME
        dest = agent_dir(a, base)
        modes = {}
        for sk in sorted(d for d in skills.iterdir() if d.is_dir()):
            t = dest / sk.name
            if args.scope == "project":
                if dry:
                    print(f"[dry-run] copy {sk} -> {t}")
                else:
                    if t.exists() or is_link(t):
                        remove_any(t)
                    t.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(sk, t)
                mode = "copy"
            elif a == "codex":
                mode = make_link(sk, t, dry)
            else:  # claude: via ~/.agents/skills (create if codex is not in this run)
                hub = agent_dir("codex", HOME) / sk.name
                if not hub.exists():
                    make_link(sk, hub, dry)
                rel = os.path.relpath(hub, t.parent)  # relative link, as installed by `npx skills`
                mode = make_link(rel, t, dry)
            modes[mode] = modes.get(mode, 0) + 1
        print(f"fanout {a} ({args.scope}): {sum(modes.values())} skills -> {dest} {modes}")
    return 0


# ----------------------------------------------------------------- status
def cmd_status(_):
    for a in ("claude", "codex"):
        names = {x.name for b in (HOME, ROOT) for x in lark_skills(agent_dir(a, b))}
        print(f"== {a}\n{' '.join(sorted(names))}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check"); c.add_argument("--json", action="store_true"); c.set_defaults(fn=cmd_check)
    i = sub.add_parser("install"); i.add_argument("--dry-run", action="store_true"); i.set_defaults(fn=cmd_install)
    s = sub.add_parser("sync-upstream"); s.add_argument("--dry-run", action="store_true"); s.set_defaults(fn=cmd_sync)
    f = sub.add_parser("fanout")
    f.add_argument("--agent", required=True, choices=["claude", "codex", "both"])
    f.add_argument("--scope", choices=["global", "project"], default="global")
    f.add_argument("--dry-run", action="store_true"); f.set_defaults(fn=cmd_fanout)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    args = ap.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
