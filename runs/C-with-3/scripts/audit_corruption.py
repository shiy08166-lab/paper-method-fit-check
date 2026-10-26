#!/usr/bin/env python3
"""案例 C：独立审计「损坏材料」的表格结构 + 来源性质核验。

只做两件事，且都只用本地文件（不联网）：
  1) 解析 nanochat_README_table_corrupted.md 里的 Time-to-GPT-2 Leaderboard 表，
     逐行数单元格、比对表头/分隔行/数据行的列数、核对 `#` 编号与行序、
     找出被截断的数值单元格。
  2) 来源性质核验：把**损坏件**与上游原文快照 materials/A/nanochat_README.md
     做「逐字节比对」，但**排除整个 leaderboard 章节**（损坏件与原文在该章节
     本来就应当不同）。目的是证明「未受损的正文段落确实是作者原文」，
     而不是从原文里把被破坏的单元格补回来。

安全约束（硬编码）：clean 快照中 leaderboard 章节的文本**永不**被打印或落盘，
脚本在比对前就把它从 clean 文本中删除；输出只包含布尔值、哈希与计数。

用法：
    python scripts/audit_corruption.py \
        --material materials/nanochat_README_table_corrupted.md \
        --clean  "<workspace>/submission/materials/A/nanochat_README.md" \
        --out logs/corruption_audit.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

SECTION_HEAD = "## Time-to-GPT-2 Leaderboard"
NUM_RE = re.compile(r"^[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?$")
TRUNCATED_RE = re.compile(r"^[-+]?\d+\.$")  # 例如 "2." —— 看起来是数字但被截断


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def split_section(text: str) -> tuple[str, str]:
    """返回 (该章节之前的正文, 该章节正文)。找不到章节则原样返回。"""
    idx = text.find(SECTION_HEAD)
    if idx == -1:
        return text, ""
    rest = text[idx + len(SECTION_HEAD):]
    nxt = rest.find("\n## ")
    body = rest if nxt == -1 else rest[:nxt]
    return text[:idx], body


def strip_synthetic_header(text: str) -> str:
    """去掉损坏件顶部的人工合成声明块（它不是原文的一部分）。

    逐行判定：开头是引用块（以 '>' 开头）且含「合成材料声明」，其后紧跟一行
    '---' 分隔线，两者一并丢弃。
    """
    lines = text.split("\n")
    i = 0
    while i < len(lines) and lines[i].lstrip().startswith(">"):
        i += 1
    block = "\n".join(lines[:i])
    if i and "合成材料声明" in block:
        if i < len(lines) and lines[i].strip() == "---":
            i += 1
        return "\n".join(lines[i:])
    return text


def cells(line: str) -> list[str]:
    """markdown 表格行 -> 单元格列表（去掉首尾空串）。"""
    parts = line.split("|")
    if parts and parts[0].strip() == "":
        parts = parts[1:]
    if parts and parts[-1].strip() == "":
        parts = parts[:-1]
    return [p.strip() for p in parts]


def is_table_line(line: str) -> bool:
    return line.lstrip().startswith("|")


def is_separator(line: str) -> bool:
    return bool(re.fullmatch(r"\|[\s:\-|]+\|?", line.strip())) and "-" in line


def audit_table(material: str) -> dict:
    lines = material.splitlines()
    t_idx = next((i for i, l in enumerate(lines) if l.startswith(SECTION_HEAD)), None)
    if t_idx is None:
        return {"error": "leaderboard 章节未找到"}

    rows: list[dict] = []
    header = separator = None
    for i in range(t_idx, len(lines)):
        line = lines[i]
        if not is_table_line(line):
            if rows:  # 表格结束
                break
            continue
        cs = cells(line)
        if header is None:
            header = {"line_no": i + 1, "n_cells": len(cs), "cells": cs}
            continue
        if separator is None and is_separator(line):
            separator = {"line_no": i + 1, "n_cells": len(cs), "cells": cs}
            continue
        rows.append({
            "line_no": i + 1,
            "n_cells": len(cs),
            "cells": cs,
            "label": cs[0] if cs else "",
        })

    header_n = header["n_cells"] if header else 0
    sep_n = separator["n_cells"] if separator else 0

    data = []
    for idx, r in enumerate(rows, start=1):
        cs = r["cells"]
        anomalies = []
        if r["n_cells"] != header_n:
            anomalies.append(f"cell_count={r['n_cells']} != header={header_n}")
        for c_i, c in enumerate(cs):
            if TRUNCATED_RE.match(c):
                anomalies.append(f"truncated_numeric_cell[cell_index={c_i}]='{c}'")
        data.append({
            "physical_row": idx,
            "line_no": r["line_no"],
            "n_cells": r["n_cells"],
            "label": r["label"],
            "anomalies": anomalies,
        })

    labels = [r["label"] for r in rows]
    numeric_labels = [x for x in labels if x.isdigit()]
    sorted_labels = sorted(numeric_labels, key=int)
    order_is_sorted = numeric_labels == sorted_labels
    label_position = {}
    for pos, lab in enumerate(numeric_labels, start=1):
        label_position[lab] = pos

    # 行序错位：物理位置 != # 编号 的数据行
    displaced = [
        {"label": lab, "physical_position": pos, "expected_position": int(lab)}
        for pos, lab in enumerate(numeric_labels, start=1)
        if lab.isdigit() and pos != int(lab)
    ]

    return {
        "header": header,
        "separator": separator,
        "header_n_cells": header_n,
        "separator_n_cells": sep_n,
        "column_count_mismatch": (header_n != sep_n),
        "n_data_rows": len(rows),
        "data_row_cell_counts": sorted({r["n_cells"] for r in rows}),
        "rows": data,
        "labels_in_physical_order": labels,
        "row_order_is_sorted_by_label": order_is_sorted,
        "displaced_rows": displaced,
    }


def strip_leaderboard(text: str) -> str:
    """删掉整个 leaderboard 章节，保留它前后的全部正文。

    章节边界必须按「行首的标题行」定位：合成声明里也提到了
    '## Time-to-GPT-2 Leaderboard' 这个字符串，用 find() 会命中声明块内部。
    """
    lines = text.split("\n")
    idx = None
    for i, l in enumerate(lines):
        if l.strip() == SECTION_HEAD:
            idx = i
            break
    if idx is None:
        return text
    end = len(lines)
    for j in range(idx + 1, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    return "\n".join(lines[:idx] + lines[end:])


def provenance(material_text: str, clean_text: str) -> dict:
    """逐字节比对「除 leaderboard 章节外」的内容。clean 的该章节先删除。

    注意：不能只比对章节前缀——损坏件与上游把该章节放在不同位置（前缀长度差
    一千多字符），只比前缀会得出无意义的 False。正确口径是：两文件都删掉
    leaderboard 章节后，剩下的正文序列应当完全一致。
    """
    mat_body = strip_synthetic_header(material_text)
    _, clean_sec = split_section(clean_text)

    mat_pre_n = strip_leaderboard(mat_body).replace("\r\n", "\n").strip()
    clean_pre_n = strip_leaderboard(clean_text).replace("\r\n", "\n").strip()

    same = mat_pre_n == clean_pre_n
    result = {
        "clean_leaderboard_section_excluded": True,
        "clean_leaderboard_chars_removed": len(clean_sec),
        "prose_excluding_leaderboard_identical": same,
        "material_prose_sha256": sha256_bytes(mat_pre_n.encode("utf-8")),
        "clean_prose_sha256": sha256_bytes(clean_pre_n.encode("utf-8")),
        "material_prose_chars": len(mat_pre_n),
        "clean_prose_chars": len(clean_pre_n),
    }
    if not same:
        m_lines = mat_pre_n.splitlines()
        c_lines = clean_pre_n.splitlines()
        diff_idx = [i + 1 for i, (a, b) in enumerate(zip(m_lines, c_lines)) if a != b]
        result["differing_line_numbers"] = diff_idx[:40]
        result["n_differing_lines"] = len(diff_idx)
        result["line_count_material"] = len(m_lines)
        result["line_count_clean"] = len(c_lines)
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--material", required=True, type=Path)
    ap.add_argument("--clean", type=Path, default=None)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    raw = args.material.read_bytes()
    text = raw.decode("utf-8")

    report = {
        "schema_version": "caseC/corruption-audit/v1",
        "material_file": str(args.material),
        "material_sha256": sha256_bytes(raw),
        "material_bytes": len(raw),
        "table_audit": audit_table(text),
    }

    if args.clean and args.clean.exists():
        craw = args.clean.read_bytes()
        report["provenance"] = provenance(text, craw.decode("utf-8", errors="replace"))
        report["provenance"]["clean_file_sha256"] = sha256_bytes(craw)
        report["provenance"]["clean_file"] = str(args.clean)
    else:
        report["provenance"] = {"error": "clean snapshot not provided"}

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ta = report["table_audit"]
    print("material sha256 :", report["material_sha256"])
    print("header cells    :", ta.get("header_n_cells"))
    print("separator cells :", ta.get("separator_n_cells"))
    print("data row widths :", ta.get("data_row_cell_counts"))
    print("labels in order :", ta.get("labels_in_physical_order"))
    print("sorted by label :", ta.get("row_order_is_sorted_by_label"))
    print("displaced rows  :", [(d["label"], d["physical_position"]) for d in ta.get("displaced_rows", [])])
    for r in ta.get("rows", []):
        if r["anomalies"]:
            print(f"  row label={r['label']} line={r['line_no']} -> {r['anomalies']}")
    pv = report["provenance"]
    print("prose identical :", pv.get("prose_excluding_leaderboard_identical"))
    print("report          :", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
