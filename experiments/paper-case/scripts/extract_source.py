#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 PDF 抽成**带页码锚点**的可检索文本。

用法：
    python scripts/extract_source.py \
        --pdf materials/lora_2106.09685.pdf \
        --txt materials/source.txt \
        --json materials/source_pages.json

产出：
  * materials/source.txt        —— 逐页文本，页与页之间用 `=== PAGE n ===` 分隔（行首标记）
  * materials/source_pages.json —— {页码(字符串): 该页文本}，页码从 1 开始

抽取与归一规则（全部写进 materials/source_manifest.json，可复现）：
  1. 引擎：pdfminer.high_level.extract_pages，逐页取文本，**保留原始换行**；
  2. 归一：Unicode NFC；
  3. 归一：连字 → ASCII（ﬁ→fi、ﬂ→fl、ﬀ→ff、ﬃ→ffi、ﬄ→ffl）。
     LaTeX 排版里的 ﬁ 是一个字形，归成 fi 才是读者看到的样子；
  4. **不做**断词连字符合并（"self-\nattention" 保持原样），因为自动合并并不安全
     （会造出 "selfattention" 这种原文没有的词）。代价是引文若跨行必须原样带换行。

为什么不做成"干净段落"文本：引文要能**逐字节**回到原文；任何重排/合词都可能造出
原文不存在的字符串，那样的引文命中了也没有证据价值。页码锚点靠 `=== PAGE n ===`
标记行承担。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import unicodedata

LIGATURES = {
    "\ufb00": "ff",
    "\ufb01": "fi",
    "\ufb02": "fl",
    "\ufb03": "ffi",
    "\ufb04": "ffl",
    "\ufb05": "st",
    "\ufb06": "st",
}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    out = []
    for ch in text:
        out.append(LIGATURES.get(ch, ch))
    return "".join(out)


def extract_pages(pdf_path: pathlib.Path):
    """返回 [(page_no, text)]，page_no 从 1 开始。"""
    import pdfminer.high_level  # type: ignore
    from pdfminer.layout import LAParams  # type: ignore

    laparams = LAParams(line_margin=0.5, char_margin=2.0, word_margin=0.1)
    texts = []
    for idx, layout in enumerate(
        pdfminer.high_level.extract_pages(str(pdf_path), laparams=laparams), start=1
    ):
        parts = []
        for element in layout:
            if hasattr(element, "get_text"):
                parts.append(element.get_text())
        texts.append((idx, normalize("".join(parts))))
    return texts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True, type=pathlib.Path)
    ap.add_argument("--txt", required=True, type=pathlib.Path)
    ap.add_argument("--json", required=True, type=pathlib.Path)
    args = ap.parse_args()

    if not args.pdf.exists():
        print("缺少 PDF: %s" % args.pdf, file=sys.stderr)
        return 2

    pages = extract_pages(args.pdf)
    body = "\n".join("=== PAGE %d ===\n%s" % (no, text) for no, text in pages)

    args.txt.parent.mkdir(parents=True, exist_ok=True)
    args.txt.write_text(body, encoding="utf-8", newline="\n")
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(
        json.dumps({str(no): text for no, text in pages}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )

    print("pages=%d bytes(txt)=%d sha256(txt)=%s"
          % (len(pages), len(body.encode("utf-8")),
             hashlib.sha256(body.encode("utf-8")).hexdigest()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
