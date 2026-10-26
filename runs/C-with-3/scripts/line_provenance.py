#!/usr/bin/env python3
"""案例 C：逐行核验「损坏件正文 vs 上游原文快照正文」的真实差异。

做法（与位置无关，抗行号漂移）：
  对损坏件里 leaderboard 章节之外的每一行，检查它是否**原样**出现在上游快照
  里。列出「在上游找不到的行」= 损坏件相对上游新增/改写的内容。

安全约束：上游快照的 leaderboard 章节在比对前就被剔除；本脚本只输出
损坏件一侧的行内容与上游匹配结果，不输出上游表格内容。
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

SECTION_HEAD = "## Time-to-GPT-2 Leaderboard"


def strip_synthetic_header(text: str) -> str:
    lines = text.split("\n")
    i = 0
    while i < len(lines) and lines[i].lstrip().startswith(">"):
        i += 1
    if i and "合成材料声明" in "\n".join(lines[:i]):
        if i < len(lines) and lines[i].strip() == "---":
            i += 1
        return "\n".join(lines[i:])
    return text


def strip_leaderboard(text: str) -> list[str]:
    lines = text.split("\n")
    idx = next((i for i, l in enumerate(lines) if l.strip() == SECTION_HEAD), None)
    if idx is None:
        return lines
    end = len(lines)
    for j in range(idx + 1, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    return lines[:idx] + lines[end:]


def strip_table_lines(lines: list[str]) -> list[str]:
    """只剔除 markdown 表格行（以 '|' 开头的行），保留章节里的正文段落。"""
    return [l for l in lines if not l.lstrip().startswith("|")]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--material", required=True, type=Path)
    ap.add_argument("--clean", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    m_text = strip_synthetic_header(args.material.read_text(encoding="utf-8"))
    c_raw = args.clean.read_text(encoding="utf-8", errors="replace")
    c_lines = strip_leaderboard(c_raw)
    m_lines = strip_leaderboard(m_text)

    comparisons = {}
    for mode, mat_lines, cln_lines in [
        ("exclude_whole_leaderboard_section", m_lines, c_lines),
        ("exclude_table_lines_only", strip_table_lines(m_lines), strip_table_lines(c_lines)),
    ]:
        c_set = {l.strip() for l in cln_lines}
        unmatched = [(i + 1, l) for i, l in enumerate(mat_lines) if l.strip() and l.strip() not in c_set]
        m_set = {l.strip() for l in mat_lines}
        clean_only = [l.strip() for l in cln_lines if l.strip() and l.strip() not in m_set]
        comparisons[mode] = {
            "material_lines": len(mat_lines),
            "clean_lines": len(cln_lines),
            "material_lines_not_found_upstream": [{"line_no": i, "text": t} for i, t in unmatched],
            "n_material_lines_not_found_upstream": len(unmatched),
            "upstream_lines_not_found_in_material": clean_only[:20],
            "n_upstream_lines_not_found_in_material": len(clean_only),
        }

    report = {
        "schema_version": "caseC/line-provenance/v2",
        "material_sha256": hashlib.sha256(args.material.read_bytes()).hexdigest(),
        "clean_sha256": hashlib.sha256(args.clean.read_bytes()).hexdigest(),
        "note": "上游 leaderboard 表格内容从未被打印或落盘；比对只用于证明正文逐字一致。",
        "comparisons": comparisons,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for mode, r in comparisons.items():
        print(f"[{mode}] material_lines={r['material_lines']} clean_lines={r['clean_lines']} "
              f"unmatched={r['n_material_lines_not_found_upstream']} "
              f"clean_only={r['n_upstream_lines_not_found_in_material']}")
        for item in r["material_lines_not_found_upstream"][:10]:
            print(f"   L{item['line_no']}: {item['text'][:140]}")
    print("report:", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
