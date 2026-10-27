#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""核对两次运行的**工作区**在仓库里是否仍然逐字节一致。

只比对工作区文件（cases/ materials/ scripts/ skill/ prompt.txt），
**不比对**运行产物（交付物本来就应当不同）。

    python scripts/check_workspace_parity.py
    # -> runs/workspace_parity.json
"""
from __future__ import annotations

import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
# 工作区文件 = **运行前就装配好**的那些。scripts/ 下会话自己新建的脚本（如
# build_deliverables.py）属于**运行产物**，不是工作区，不参与比对。
WORKSPACE_PREFIXES = ("cases/", "materials/", "skill/")
WORKSPACE_FILES = ("prompt.txt", "scripts/check_agreement.py")


def sha256_of(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def workspace_files(run_dir: pathlib.Path) -> dict:
    out = {}
    for p in sorted(run_dir.rglob("*")):
        if not p.is_file():
            continue
        rel = str(p.relative_to(run_dir)).replace("\\", "/")
        if rel in WORKSPACE_FILES or rel.startswith(WORKSPACE_PREFIXES):
            out[rel] = {"bytes": p.stat().st_size, "sha256": sha256_of(p)}
    return out


def main() -> int:
    a = workspace_files(ROOT / "runs" / "with-skill")
    b = workspace_files(ROOT / "runs" / "without-skill")
    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    diff = sorted(k for k in set(a) & set(b) if a[k]["sha256"] != b[k]["sha256"])
    out = {
        "schema": "paper-case/workspace_parity/v1",
        "note": ("只比对工作区文件；交付物（claims.csv 等）本来就不同，不参与比对。"
                 "两次工作区在装配时即逐字节相同（见 runs/workspace_diff.json）。"),
        "with_skill": a,
        "without_skill": b,
        "only_in_with_skill": only_a,
        "only_in_without_skill": only_b,
        "content_differs": diff,
        "identical_except_skill_and_prompt": (
            diff == ["prompt.txt"] and only_a == ["skill/SKILL.md"] and not only_b),
    }
    p = ROOT / "runs" / "workspace_parity.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: out[k] for k in ("only_in_with_skill", "only_in_without_skill",
                                          "content_differs", "identical_except_skill_and_prompt")},
                     ensure_ascii=False, indent=2))
    return 0 if out["identical_except_skill_and_prompt"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
