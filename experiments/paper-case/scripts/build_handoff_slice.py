#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统计 experiments/paper-case/ 下新增文件的字节数，并给出「若只有 N KiB 余量该带哪几个」的切片建议。

    python scripts/build_handoff_slice.py --budget-kib 14

输出：
  * 新增文件清单（按字节从大到小）
  * 贪心地按「信息密度」排序（作者侧重算材料 > 对照 > 报告 > 原始会话），
    给出在预算内能装下的组合
"""
from __future__ import annotations

import argparse
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

# 信息密度排序：同一优先级里先挑小的（同样的信息，占更少字节）
TIERS = [
    ("A 作者侧独立重算（本案例最值钱的部分）", [
        "ledger_slim.md", "ledger.md", "ledger.json", "scripts/verify_paper_results.py",
        "scripts/build_ledger.py", "scripts/extract_tables_geom.py",
        "logs/author_table1_geom.txt", "logs/author_table12_geom.txt",
    ]),
    ("B 有/无 Skill 对照", [
        "comparison.md", "scripts/build_comparison.py",
    ]),
    ("C 冻结的任务书与验收标准", [
        "cases/task-paper.md", "cases/acceptance-paper.md", "cases/frozen_hashes.json",
    ]),
    ("D 两次运行的产物（原始证据）", [
        "runs/with-skill/claims.csv", "runs/with-skill/preconditions.csv",
        "runs/with-skill/verdict.md", "runs/with-skill/evidence_index.json",
        "runs/without-skill/claims.csv", "runs/without-skill/preconditions.csv",
        "runs/without-skill/verdict.md", "runs/without-skill/evidence_index.json",
        "runs/with-skill/logs/agreement.json", "runs/without-skill/logs/agreement.json",
        "runs/with-skill/prompt.txt", "runs/without-skill/prompt.txt",
    ]),
    ("E 材料与说明", [
        "README.md", "HANDOFF.md", "materials/source_manifest.json",
        "scripts/extract_source.py", "scripts/build_runs.py",
        "scripts/export_codex_session.py", "scripts/finalize_run.py",
        "scripts/build_handoff_slice.py", "scripts/sync_workspace.py",
        "scripts/run_session.py", "scripts/finalize_all.py",
        "scripts/check_workspace_parity.py",
    ]),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget-kib", type=int, default=14)
    args = ap.parse_args()

    files = {}
    for p in ROOT.rglob("*"):
        if p.is_file():
            rel = str(p.relative_to(ROOT)).replace("\\", "/")
            files[rel] = p.stat().st_size

    lines = []
    total = 0
    for tier, names in TIERS:
        rows = [(n, files[n]) for n in names if n in files]
        rows.sort(key=lambda r: r[1])
        if not rows:
            continue
        lines.append("### %s" % tier)
        lines.append("")
        lines.append("| 文件 | 字节 |")
        lines.append("|---|---|")
        for n, b in rows:
            lines.append("| `%s` | %d |" % (n, b))
            total += b
        lines.append("")

    budget = args.budget_kib * 1024
    lines.append("### 预算内切片建议（预算 %d KiB = %d B）" % (args.budget_kib, budget))
    lines.append("")
    lines.append("| 组合 | 累计字节 | 装得下 |")
    lines.append("|---|---|---|")
    picked, acc = [], 0
    for tier, names in TIERS:
        for n in sorted([x for x in names if x in files], key=lambda x: files[x]):
            if acc + files[n] <= budget:
                picked.append(n)
                acc += files[n]
    lines.append("| A + B（作者侧重算 + 对照表） | %d | %s |" % (acc, "是" if acc <= budget else "否"))
    lines.append("| A（只要作者侧重算） | %d | 是 |"
                 % sum(files[n] for n in files if n in TIERS[0][1]))
    lines.append("| 全部 Tier A–E | %d | %s |" % (total, "是" if total <= budget else "否"))
    lines.append("")
    lines.append("**在 %d KiB 余量下建议带：**" % args.budget_kib)
    lines.append("")
    for n in picked:
        lines.append("- `%s`（%d B）" % (n, files[n]))
    lines.append("")
    lines.append("合计 %d B（%.1f KiB），余量 %d B。" % (acc, acc / 1024, budget - acc))

    (ROOT / "logs" / "handoff_slice.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
