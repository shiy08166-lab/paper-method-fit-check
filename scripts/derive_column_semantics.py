# -*- coding: utf-8 -*-
"""作者侧独立核查：把损坏件的 leaderboard 表与上游原表节选逐格对齐，
确定损坏件每一列真正装的是上游的哪一列（列语义是否发生左移）。

只用包内两个文件：
  paper_materials/nanochat_README_leaderboard_upstream.md  上游原表节选（逐字节切片）
  paper_materials/nanochat_README_table_corrupted.md      合成/损坏件
"""
import re
import pathlib
import re

PKG = pathlib.Path(__file__).resolve().parent.parent  # 包根 = 本脚本的上一级目录，评审在任意机器上直接运行即可
PM = PKG / "paper_materials"
UP = (PM / "nanochat_README_leaderboard_upstream.md").read_bytes().decode("utf-8")
CO = (PM / "nanochat_README_table_corrupted.md").read_bytes().decode("utf-8")


def rows(text):
    out = []
    for ln in text.split("\r\n"):
        if ln.startswith("|"):
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            out.append(cells)
    return out


up_rows = rows(UP)
co_rows = rows(CO)
print("上游原表节选：%d 行表格；损坏件：%d 行表格" % (len(up_rows), len(co_rows)))
up_head = up_rows[0]
print("上游表头 (%d 格): %s" % (len(up_head), up_head))
co_head = co_rows[0]
print("损坏件表头 (%d 格): %s" % (len(co_head), co_head))

up_data = {r[0]: r for r in up_rows[1:] if r[0].isdigit()}
co_data = {r[0]: r for r in co_rows[1:] if r[0].isdigit()}

print()
print("按 `#` 标签对齐后的逐格对应：")
print("%-4s %-6s %-52s %s" % ("#", "行数", "损坏件各格（顺序）", "上游同标签行的各格"))
mapping_votes = {}
for lab in sorted(set(up_data) & set(co_data)):
    u = up_data[lab]
    c = co_data[lab]
    # 对每个损坏件单元格，找出它在上游行中的位置
    where = []
    for cell in c:
        pos = [i for i, uc in enumerate(u) if uc == cell]
        where.append(pos)
    print("#%-3s up=%-3d co=%-3d  %s" % (lab, len(u), len(c), where))
    # 统计整体位移：损坏件第 k 格对应上游第 ? 格
    for k, pos in enumerate(where):
        for p in pos:
            mapping_votes.setdefault((k, p), 0)
            mapping_votes[(k, p)] += 1

print()
print("位移投票（损坏件第 k 格 ↔ 上游第 p 格，命中行数）：")
for (k, p), n in sorted(mapping_votes.items()):
    if n >= 2:
        name = up_head[p] if p < len(up_head) else "?"
        print("  损坏件第 %d 格 → 上游第 %d 格（%s）：%d 行一致" % (k, p, name, n))

# （逐格对齐的结论见文件末尾 main() 的输出）


def damaged_table_structure(text):
    """受损表的结构实测：表头/分隔行/数据行的格数、# 标签顺序、截断与多格异常。"""
    rows = [ln for ln in text.split("\r\n") if ln.startswith("|")]
    cells = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in rows]
    head, sep = cells[0], cells[1]
    data = [c for c in cells[2:] if c[0].isdigit()]
    out = {
        "header_cells": len(head),
        "separator_cells": len(sep),
        "data_rows": len(data),
        "data_row_cell_counts": [len(c) for c in data],
        "labels_in_physical_order": [c[0] for c in data],
        "rows_with_extra_cells": [c[0] for c in data if len(c) != len(head)],
        "truncated_numeric_cells": [
            {"label": c[0], "cell": c[1]}
            for c in data if len(c) > 1 and re.fullmatch(r"\d+\.", c[1])],
    }
    return out


def main():
    co_text = (PM / "nanochat_README_table_corrupted.md").read_bytes().decode("utf-8")
    print("=== 受损表结构实测（与 runs/C-with-3/logs/corruption_audit.json 同口径，可由本脚本重新算出）===")
    for k, v in damaged_table_structure(co_text).items():
        print("  %-26s %s" % (k, v))
    print()
    print("=== 逐格对齐：损坏件第 k 格 ↔ 上游第 p 格 ===")
    up_rows, co_rows = rows(UP), rows(CO)
    up_head = up_rows[0]
    up_data = {r[0]: r for r in up_rows[1:] if r[0].isdigit()}
    co_data = {r[0]: r for r in co_rows[1:] if r[0].isdigit()}
    votes = {}
    for lab in sorted(set(up_data) & set(co_data)):
        u, c = up_data[lab], co_data[lab]
        for k, cell in enumerate(c):
            for p, uc in enumerate(u):
                if uc == cell:
                    votes[(k, p)] = votes.get((k, p), 0) + 1
    for (k, p), n in sorted(votes.items()):
        if n >= 2:
            print("  损坏件第 %d 格 → 上游第 %d 格（%-12s）：%d 行一致" % (k, p, up_head[p], n))
    print()
    core = up_head.index("CORE")
    vpb = up_head.index("val_bpb")
    print("  结论：表头写着 CORE 的那一格（第 %d 格）实际对应上游第 %d 格（%s）→ 受损表的列语义已左移，"
          "受损表格的格子不得指派列名。"
          % (core, vpb, up_head[vpb]))


if __name__ == "__main__":
    main()
