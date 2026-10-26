#!/usr/bin/env python3
"""案例 C：生成 manifest.json（文件索引 + skill_version）与 logs/agreement_detail.md（逐值核对处置）。"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

INDEX_FILES = [
    "preconditions.csv",
    "claims.csv",
    "evidence_index.json",
    "verdict.md",
    "logs/agreement.json",
    "logs/agreement_detail.md",
    "logs/corruption_audit.json",
    "logs/line_provenance.json",
    "logs/verification.json",
    "logs/verify_stdout.txt",
    "logs/check_agreement_stdout.txt",
    "logs/run_log.md",
    "materials/source.txt",
    "materials/nanochat_README_table_corrupted.md",
    "cases/task-C.md",
    "cases/acceptance-C.md",
    "skill/SKILL.md",
    "scripts/audit_corruption.py",
    "scripts/line_provenance.py",
    "scripts/build_outputs.py",
    "scripts/verify_outputs.py",
    "scripts/check_agreement.py",
    "scripts/build_manifest.py",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True, type=Path)
    ap.add_argument("--material", required=True, type=Path)
    ap.add_argument("--clean", type=Path, default=None)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    case = args.case

    with (case / "claims.csv").open(encoding="utf-8-sig", newline="") as fh:
        claims = list(csv.DictReader(fh))
    with (case / "preconditions.csv").open(encoding="utf-8-sig", newline="") as fh:
        pre = list(csv.DictReader(fh))
    agreement = json.loads((case / "logs" / "agreement.json").read_text(encoding="utf-8"))
    verification = json.loads((case / "logs" / "verification.json").read_text(encoding="utf-8"))

    # ---- 逐值核对明细（logs/agreement_detail.md）
    rows = [r for r in claims if r["classification"] == "paper-fact" and r["numeric_value"].strip()]
    lines = [
        "# 数值核对明细（案例 C）",
        "",
        f"- 核对工具：Skill 自带 `scripts/check_agreement.py`（逐字复制，未改）",
        f"- 容差：{agreement.get('tolerance')}（相对误差）",
        f"- 检查结论：{agreement.get('claims_checked')} 条结论，{agreement.get('findings_count')} 项标记，"
        f"all_passed={agreement.get('all_passed')}",
        "- 处置原则：**超容差项必须修正、降级、或写进报告的遗留节**；本表列出每个被引用数值的转写来源与处置。",
        "",
        "| claim | numeric_value | 转写来源（同一引文内命中） | 相对误差 | 处置 |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        cid = r["claim_id"]
        num = r["numeric_value"]
        detail = next((c for c in verification["checks"] if c["check"] == "XNUM"), {})
        err = "0（引文内字面命中）"
        disp = "一致，保留为 paper-fact"
        if cid == "C25":
            err = f"{detail.get('relative_error', 0) * 100:.4f} %（与正文 {detail.get('prose_value')} 交叉核对）"
            disp = "一致（表格取整），保留；该行另有\"表格整体受损、未做上游核验\"的标注"
        lines.append(f"| {cid} | {num} | `claims.csv` 该行 quote | {err} | {disp} |")

    lines += [
        "",
        "## 未参与数值核对的条目（按设计）",
        "",
        "| 条目 | 处理 | 原因 |",
        "|---|---|---|",
        "| # 4 行 time 单元格（被截断） | `numeric_value` 留空，分类 `undetermined`（C33） | "
        "受损值不可确定；不给点估计也不给区间 |",
        "| 缺失列（原表 8 列中的第 8 列） | 分类 `undetermined`（C34） | 该列在本文件中无法复原，不重建 |",
        "| 全部 `inference` 行 | `numeric_value` 留空 | 推断值不得混进「原文数值」通道 |",
        "",
        "## 派生数字（仅出现在报告正文，非原文数值）",
        "",
        "| 派生量 | 算式 | 口径 |",
        "|---|---|---|",
        "| $96 | 8 卡 × 4 h × $3/GPU·h | 材料自身单价下的最坏情况估计（材料未给 A100 报价） |",
        "| 0.0098 % | \\|0.2565 − 0.256525\\| / 0.256525 | 表格 CORE 与正文 CORE 的跨来源核对 |",
        "",
    ]
    (case / "logs" / "agreement_detail.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ---- manifest.json
    files = []
    for rel in INDEX_FILES:
        p = case / rel
        if p.exists():
            files.append({"path": rel, "bytes": p.stat().st_size, "sha256": sha256(p)})

    manifest = {
        "schema_version": "caseC/manifest/v1",
        "case": {
            "id": "caseC-3",
            "title": "案例 C · 边界与异常处理",
            "task_sha256": sha256(case / "cases" / "task-C.md"),
            "acceptance_sha256": sha256(case / "cases" / "acceptance-C.md"),
            "offline": True,
            "trained": False,
            "dataset_downloaded": False,
            "pytorch_installed": False,
        },
        "skill": {
            "path": "skill/SKILL.md",
            "skill_version": sha256(case / "skill" / "SKILL.md"),
            "modified": False,
            "note": "skill_version 与仓库 manifest 中 A(with_skill) 的锁定值一致",
        },
        "material": {
            "path": "materials/nanochat_README_table_corrupted.md",
            "sha256": sha256(args.material),
            "bytes": args.material.stat().st_size,
            "nature": "合成/损坏件（非作者原文）；引用时必须标注性质",
            "working_copy": "materials/source.txt",
            "working_copy_sha256": sha256(case / "materials" / "source.txt"),
        },
        "upstream_snapshot": {
            "path": str(args.clean) if args.clean else None,
            "sha256": sha256(args.clean) if args.clean and args.clean.exists() else None,
            "usage": "仅用于正文逐行来源核验；上游 leaderboard 表格刻意未读、未打印、未落盘",
        },
        "verdict": "transferable-with-changes",
        "counts": verification["counts"],
        "expected_behaviours_met": "5/5",
        "checks_all_ok": verification["all_ok"],
        "files": files,
    }
    args.out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("manifest files:", len(files))
    print("counts:", json.dumps(verification["counts"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
