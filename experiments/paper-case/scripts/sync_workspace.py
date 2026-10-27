#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把隔离工作区里的**工作区文件**同步回仓库的 runs/<name>/（不碰交付物）。

为什么需要：最终对照的两轮是在隔离副本里跑的（避免对照轮从父目录翻到 SKILL.md），
交付物由 scripts/finalize_run.py 复制回来；但工作区本身（cases/ materials/ scripts/ skill/
prompt.txt）也应该在仓库里齐备，评审不用离开仓库就能复现。

    python scripts/sync_workspace.py
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMP = pathlib.Path(r"E:\minimax\project\DP match\work\tmp\paper-case")
WORKSPACE = ("cases", "materials", "scripts", "skill")


def sha256_of(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    report = {}
    for run in ("with-skill", "without-skill"):
        src, dst = TEMP / run, ROOT / "runs" / run
        if not src.exists():
            continue
        dst.mkdir(parents=True, exist_ok=True)
        copied = []
        for sub in WORKSPACE:
            s_dir = src / sub
            if not s_dir.exists():
                continue
            for p in sorted(s_dir.rglob("*")):
                if not p.is_file():
                    continue
                rel = p.relative_to(src)
                d = dst / rel
                d.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(p, d)
                copied.append({"path": str(rel).replace("\\", "/"), "bytes": d.stat().st_size,
                               "sha256": sha256_of(d)})
        sp = src / "prompt.txt"
        if sp.exists():
            shutil.copyfile(sp, dst / "prompt.txt")
            copied.append({"path": "prompt.txt", "bytes": (dst / "prompt.txt").stat().st_size,
                           "sha256": sha256_of(dst / "prompt.txt")})
        report[run] = copied
        print("== %s：同步 %d 个工作区文件" % (run, len(copied)))
    (ROOT / "runs" / "workspace_sync.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
