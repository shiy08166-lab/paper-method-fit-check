#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""作者侧工具：从 PDF 的**几何位置**重建表格（行 × 列）。

为什么需要它：
  PDF 里没有"表格"这个对象，只有带坐标的文字块。抽文本会把表格压平成一串单元格，
  **行/列身份就丢了**——这正是本案例里最危险的一环（一个数字被安到相邻的行/列上，
  引文仍然逐字命中、数值仍然 1% 以内，机械检查全绿）。
  作者侧要独立复核这些数字属于哪一行哪一列，就必须回到几何：
  按 y 坐标聚成行，按 x 间隙聚成列。

用法：
    python scripts/extract_tables_geom.py --pdf materials/lora_2106.09685.pdf --pages 4,6,8
    python scripts/extract_tables_geom.py --pdf ... --out logs/author_tables.txt
"""
from __future__ import annotations

import argparse
import pathlib
import sys


def rows_from_words(words, y_tol=3.0, x_gap=6.0):
    """words: list of (x0,y0,x1,y1,text,...) -> list of rows, each row = list of cells."""
    items = sorted(words, key=lambda w: (round(w[1], 1), w[0]))
    rows = []
    cur = []
    cur_y = None
    for w in items:
        if cur_y is None or abs(w[1] - cur_y) <= y_tol:
            cur.append(w)
            cur_y = w[1] if cur_y is None else cur_y
        else:
            rows.append(cur)
            cur = [w]
            cur_y = w[1]
    if cur:
        rows.append(cur)

    out = []
    for r in rows:
        cells = []
        cur_cell = []
        last_x1 = None
        for w in sorted(r, key=lambda w: w[0]):
            if last_x1 is not None and (w[0] - last_x1) > x_gap:
                cells.append(cur_cell)
                cur_cell = []
            cur_cell.append(w[4])
            last_x1 = w[2]
        if cur_cell:
            cells.append(cur_cell)
        out.append([" ".join(c) for c in cells])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True, type=pathlib.Path)
    ap.add_argument("--pages", default="", help="逗号分隔的页码（1 起）；留空 = 全部")
    ap.add_argument("--out", default="", type=pathlib.Path)
    ap.add_argument("--y-tol", type=float, default=3.0)
    ap.add_argument("--x-gap", type=float, default=6.0)
    args = ap.parse_args()

    import fitz  # type: ignore

    doc = fitz.open(args.pdf)
    if args.pages:
        wanted = [int(x) for x in args.pages.split(",") if x.strip()]
    else:
        wanted = list(range(1, doc.page_count + 1))

    chunks = []
    for pno in wanted:
        page = doc[pno - 1]
        words = page.get_text("words")
        chunks.append("========== PAGE %d ==========" % pno)
        for r in rows_from_words(words, args.y_tol, args.x_gap):
            line = " | ".join(r)
            if line.strip(" |"):
                chunks.append(line)
    text = "\n".join(chunks)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8", newline="\n")
        print("wrote %s (%d bytes)" % (args.out, len(text.encode("utf-8"))))
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
