#!/usr/bin/env python3
"""数值一致性自检：核对 claims.csv 里的引文与数值是否真的落在原文上。

用法：
    python3 scripts/check_agreement.py \
        --claims claims.csv \
        --preconditions preconditions.csv \
        --source materials/source.txt \
        --tolerance 0.01 \
        --report logs/agreement.json

判定三件事：
  1. 每条 paper-fact 的 quote 必须是 source 里的一段**连续**子串（拼接引文会被判失败）
  2. 每条 paper-fact 必须有 locator
  3. 若给出 numeric_value，它必须能在 quote 里找到对应数字，相对误差超过容差即标记

退出码：0 = 全部通过；1 = 存在未处置的标记；2 = 输入文件缺失或格式错误。
只用 Python 标准库。
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

NUM_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")

VALID_CLASSIFICATIONS = {"paper-fact", "inference", "undetermined"}


def parse_number(raw: str) -> float | None:
    if raw is None:
        return None
    text = raw.strip().replace(",", "").replace("%", "")
    if not text:
        return None
    match = NUM_RE.search(text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def close_enough(a: float, b: float, tol: float) -> bool:
    scale = max(abs(a), abs(b), 1e-12)
    return abs(a - b) / scale <= tol


def load_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def normalize(text: str) -> str:
    """只折叠空白，不动字符本身 —— 免得把排版差异误判成引文造假。"""
    return re.sub(r"[ \t]+", " ", text.replace("\r\n", "\n").replace("\r", "\n"))


def check_claim(row: dict, source: str, tol: float) -> list[dict]:
    findings: list[dict] = []
    claim_id = (row.get("claim_id") or "").strip()
    classification = (row.get("classification") or "").strip()
    locator = (row.get("locator") or "").strip()
    quote = (row.get("quote") or "").strip()
    numeric = parse_number(row.get("numeric_value") or "")

    if classification not in VALID_CLASSIFICATIONS:
        findings.append({
            "claim_id": claim_id,
            "kind": "invalid_classification",
            "detail": f"classification 必须是 {sorted(VALID_CLASSIFICATIONS)} 之一，实际为 {classification!r}",
        })
        return findings

    if classification != "paper-fact":
        if numeric is not None:
            findings.append({
                "claim_id": claim_id,
                "kind": "numeric_on_non_fact",
                "detail": "非 paper-fact 的结论不应带 numeric_value（那是推断，不是原文数值）",
            })
        return findings

    if not locator:
        findings.append({
            "claim_id": claim_id,
            "kind": "missing_locator",
            "detail": "paper-fact 必须给出原文定位（章节/图表/公式/页码）",
        })

    if not quote:
        findings.append({
            "claim_id": claim_id,
            "kind": "missing_quote",
            "detail": "paper-fact 必须给出原文引文",
        })
        return findings

    haystack = normalize(source)
    needle = normalize(quote)
    if needle not in haystack:
        findings.append({
            "claim_id": claim_id,
            "kind": "quote_not_contiguous",
            "detail": "引文不是原文的连续子串（可能是改写、拼接，或抽文本与原文有出入）",
            "quote_preview": quote[:160],
        })
        return findings

    if numeric is not None:
        candidates = [float(m) for m in NUM_RE.findall(quote.replace(",", ""))]
        if not candidates:
            findings.append({
                "claim_id": claim_id,
                "kind": "numeric_not_in_quote",
                "detail": f"numeric_value={numeric} 在引文里找不到对应数字",
            })
        else:
            best = min(candidates, key=lambda c: abs(c - numeric))
            if not close_enough(best, numeric, tol):
                findings.append({
                    "claim_id": claim_id,
                    "kind": "numeric_mismatch",
                    "detail": f"转写值 {numeric} 与引文中的 {best} 相对误差超过容差 {tol}",
                    "expected_in_quote": best,
                    "written": numeric,
                })
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="claims.csv 的引文与数值一致性自检")
    parser.add_argument("--claims", required=True, type=Path)
    parser.add_argument("--preconditions", type=Path, default=None)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--tolerance", type=float, default=0.01)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()

    for path in (args.claims, args.source):
        if not path.exists():
            print(f"缺少输入文件: {path}", file=sys.stderr)
            return 2

    claims = load_csv(args.claims)
    source = args.source.read_text(encoding="utf-8", errors="replace")

    findings: list[dict] = []
    for row in claims:
        findings.extend(check_claim(row, source, args.tolerance))

    preconditions_summary = None
    if args.preconditions and args.preconditions.exists():
        pre_rows = load_csv(args.preconditions)
        missing_locator = [
            (r.get("id") or "").strip()
            for r in pre_rows
            if not (r.get("source_locator") or "").strip()
            and (r.get("confidence") or "").strip() != "absent"
        ]
        categories = sorted({
            (r.get("category") or "").strip()
            for r in pre_rows
            if (r.get("category") or "").strip()
        })
        preconditions_summary = {
            "total": len(pre_rows),
            "categories_present": categories,
            "rows_without_locator_or_absent": missing_locator,
        }

    report = {
        "schema_version": "paper-method-fit-check/agreement/v1",
        "source_file": str(args.source),
        "source_sha256_note": "建议同时记录 source 文件的 SHA-256，便于评审核对",
        "tolerance": args.tolerance,
        "claims_checked": len(claims),
        "findings": findings,
        "findings_count": len(findings),
        "all_passed": len(findings) == 0,
        "preconditions": preconditions_summary,
    }

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"检查 {len(claims)} 条结论，标记 {len(findings)} 项 -> {args.report}")
    for item in findings:
        print(f"  [{item['kind']}] {item['claim_id']}: {item['detail']}")
    if preconditions_summary and preconditions_summary["rows_without_locator_or_absent"]:
        print(f"  [precondition] 未定位也未标 absent: "
              f"{preconditions_summary['rows_without_locator_or_absent']}")
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
