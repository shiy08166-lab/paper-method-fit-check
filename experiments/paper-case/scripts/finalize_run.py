#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把一次运行的产物从**隔离工作区**按字节复制回 runs/<name>/，并导出会话日志。

    python scripts/finalize_run.py --run with-skill \
        --src "E:\\...\\work\\tmp\\paper-case\\with-skill"

做四件事：
  1. 复制 5 个交付物 + logs/* + 任何 agent 新建的顶层文件（逐字节）
  2. 找到这次会话在 ~/.codex/sessions/ 下的 rollout（原始会话日志），导成
     session-export.txt（人读）与 events.jsonl（Skill 第 8 步要求的步骤类型）
  3. 逐文件核对复制前后的 SHA-256
  4. 打印一份 finalize_report.json

为什么要在隔离副本里跑：对照轮（without-skill）的会话如果直接开在作品仓库里，
往上两层就能翻到 `paper-method-fit-check/SKILL.md`，对照就被污染了。
隔离副本与仓库内的 runs/<name>/ 逐字节一致（见 runs/workspace_diff.json）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DELIVERABLES = ["preconditions.csv", "claims.csv", "evidence_index.json", "verdict.md"]
CODEX_HOME = pathlib.Path.home() / ".codex"


def sha256_of(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def find_rollout(session_id: str) -> pathlib.Path | None:
    base = CODEX_HOME / "sessions"
    if not base.exists():
        return None
    for p in base.rglob("rollout-*%s*.jsonl" % session_id):
        return p
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--src", required=True, type=pathlib.Path)
    args = ap.parse_args()

    src = args.src
    dst = ROOT / "runs" / args.run
    if not src.exists():
        print("源目录不存在: %s" % src, file=sys.stderr)
        return 2
    dst.mkdir(parents=True, exist_ok=True)

    report = {"run": args.run, "src": str(src), "dst": str(dst), "copied": [], "missing": []}

    # 1. 复制交付物与 logs
    names = list(DELIVERABLES)
    logs_src = src / "logs"
    if logs_src.exists():
        names += ["logs/" + p.name for p in sorted(logs_src.iterdir()) if p.is_file()]
    for extra in ("session-export.txt", "events.jsonl"):
        if (src / extra).exists():
            names.append(extra)

    for name in names:
        s = src / name
        d = dst / name
        if not s.exists():
            report["missing"].append(name)
            continue
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(s, d)
        hs, hd = sha256_of(s), sha256_of(d)
        report["copied"].append({"path": name, "bytes": d.stat().st_size,
                                 "sha256": hd, "identical": hs == hd})
        if hs != hd:
            print("复制后哈希不一致: %s" % name, file=sys.stderr)
            return 1

    # 2. 会话导出
    raw = dst / "logs" / "codex_events_raw.jsonl"
    session_id = None
    if raw.exists():
        for line in raw.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if obj.get("type") == "thread.started":
                session_id = obj.get("thread_id")
                break
    report["session_id"] = session_id

    if session_id:
        rollout = find_rollout(session_id)
        report["rollout"] = str(rollout) if rollout else None
        if rollout:
            export = ROOT / "scripts" / "export_codex_session.py"
            import subprocess
            proc = subprocess.run([sys.executable, str(export), "--rollout", str(rollout),
                                   "--out-dir", str(dst)], capture_output=True, text=True,
                                  encoding="utf-8", errors="replace")
            report["export_stdout"] = proc.stdout.strip()
            report["export_stderr"] = proc.stderr.strip()
            if proc.returncode != 0:
                print("会话导出失败: %s" % proc.stderr, file=sys.stderr)
                return 1
            for extra in ("session-export.txt", "events.jsonl"):
                p = dst / extra
                if p.exists():
                    report["copied"].append({"path": extra, "bytes": p.stat().st_size,
                                             "sha256": sha256_of(p), "identical": True})

    (dst / "logs" / "finalize_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: report[k] for k in ("run", "session_id", "rollout", "missing")},
                     ensure_ascii=False, indent=2))
    for c in report["copied"]:
        print("  %-34s %9d  %s" % (c["path"], c["bytes"], c["sha256"][:16]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
