#!/usr/bin/env python3
"""案例 C：交付物自检（对照 cases/acceptance-C.md 的 C-P1…C-P11）。

只读材料与产出，不修改任何文件。输出 logs/verification.json。
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

VALID_CLASS = {"paper-fact", "inference", "undetermined"}
VALID_VERDICTS = {"transferable-as-is", "transferable-with-changes", "not-transferable", "undetermined"}
REQUIRED_CATS = {"compute", "data scale", "hyperparameters", "hidden assumptions"}


def load_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return [dict(r) for r in csv.DictReader(fh)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", required=True, type=Path)
    ap.add_argument("--material", required=True, type=Path)
    ap.add_argument("--clean", type=Path, default=None)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    case = args.case

    raw = args.material.read_bytes()
    text = raw.decode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()

    claims = load_csv(case / "claims.csv")
    pre = load_csv(case / "preconditions.csv")
    evidence = json.loads((case / "evidence_index.json").read_text(encoding="utf-8"))
    agreement = json.loads((case / "logs" / "agreement.json").read_text(encoding="utf-8"))
    verdict = (case / "verdict.md").read_text(encoding="utf-8")

    checks: list[dict] = []

    def add(cid: str, desc: str, ok: bool, detail=None) -> None:
        checks.append({"check": cid, "desc": desc, "ok": bool(ok), "detail": detail})

    # C-P1 四类前置条件齐全
    cats = {r["category"].strip() for r in pre}
    add("C-P1", "四类前置条件齐全", REQUIRED_CATS <= cats, {"present": sorted(cats), "missing": sorted(REQUIRED_CATS - cats)})

    # C-P2 定位必填 + absent 行带原因
    blank_loc = [r["id"] for r in pre if not r["source_locator"].strip()]
    absent_no_reason = [r["id"] for r in pre if r["confidence"].strip() == "absent" and "原因" not in r["value"]]
    add("C-P2", "无空 source_locator；absent 行带原因", not blank_loc and not absent_no_reason,
        {"blank_locator": blank_loc, "absent_without_reason": absent_no_reason})

    # C-P3 三分类合法
    bad_cls = sorted({r["classification"] for r in claims} - VALID_CLASS)
    add("C-P3", "classification 三选一", not bad_cls, {"invalid": bad_cls})

    # C-P4 paper-fact 必须有引文 + 定位
    pf_no_quote = [r["claim_id"] for r in claims if r["classification"] == "paper-fact" and not r["quote"].strip()]
    pf_no_loc = [r["claim_id"] for r in claims if r["classification"] == "paper-fact" and not r["locator"].strip()]
    add("C-P4", "paper-fact 行引文与定位均非空", not pf_no_quote and not pf_no_loc,
        {"no_quote": pf_no_quote, "no_locator": pf_no_loc})

    # C-P5 引文可程序化命中（连续片段，命中 >= 1）
    misses, hit_counts = [], {}
    for r in claims:
        q = r["quote"].strip()
        if not q:
            continue
        n = text.count(q)
        hit_counts[r["claim_id"]] = n
        if n < 1:
            misses.append({"claim_id": r["claim_id"], "quote_preview": q[:80]})
    add("C-P5", "每条引文都能在材料里检索命中且为连续片段", not misses,
        {"not_found": misses, "min_hits": min(hit_counts.values()) if hit_counts else None,
         "n_quotes_checked": len(hit_counts)})

    # 证据索引：引文连续 + sha256 与被引文件一致
    ev_miss = [e["id"] for e in evidence if e["quote"] not in text]
    ev_sha = sorted({e["sha256"] for e in evidence})
    add("EVID", "evidence_index 引文可在原文命中且 sha256 指向被引文件",
        not ev_miss and ev_sha == [digest], {"not_found": ev_miss, "sha256_set": ev_sha, "material_sha256": digest})

    # 本案例专属：非 paper-fact 行不得带引文/数值
    nf_quote = [r["claim_id"] for r in claims if r["classification"] != "paper-fact" and r["quote"].strip()]
    nf_num = [r["claim_id"] for r in claims if r["classification"] != "paper-fact" and r["numeric_value"].strip()]
    add("C-CASE-1", "非 paper-fact 行不带引文、不带 numeric_value", not nf_quote and not nf_num,
        {"with_quote": nf_quote, "with_numeric": nf_num})

    # 本案例专属：受损（截断）单元格不得以任何形式进入引文或数值
    truncated_hits = [r["claim_id"] for r in claims
                      if "| 2." in r["quote"] or r["numeric_value"].strip() in {"2.", "2"}]
    add("C-CASE-2", "被截断的单元格未出现在任何 quote / numeric_value", not truncated_hits,
        {"offenders": truncated_hits})

    # C-P8 数值处置完整
    flags = agreement.get("findings", [])
    add("C-P8", "agreement 无未处置标记", agreement.get("findings_count", len(flags)) == 0,
        {"findings_count": agreement.get("findings_count"), "all_passed": agreement.get("all_passed")})

    # C-P6 / C-P7 / C-P11 verdict 结构
    sec_map = {
        "① Verdict": "① Verdict",
        "② What is established": "② What is established",
        "③ What I inferred": "③ What I inferred",
        "④ What remains open": "④ What remains open",
        "异常处理对照": "⑥ 异常处理对照",
    }
    missing_secs = [k for k, v in sec_map.items() if v not in verdict]
    verdict_word = None
    m = re.search(r"\*\*`(transferable-as-is|transferable-with-changes|not-transferable|undetermined)`\*\*", verdict)
    if m:
        verdict_word = m.group(1)
    add("C-P6", "结论唯一且取自四选一", bool(m) and verdict_word in VALID_VERDICTS, {"verdict": verdict_word})
    add("C-P7", "四段齐全", all(v in verdict for v in list(sec_map.values())[:4]), {"missing": missing_secs})
    add("C-P11", "存在独立「异常处理对照」小节", "异常处理对照" in verdict, {"missing": missing_secs})
    beh_rows = len(re.findall(r"^\| [1-5] \|", verdict, flags=re.M))
    add("C-P11b", "异常处理对照逐条覆盖 5 条预期行为", beh_rows >= 5, {"behaviour_rows_found": beh_rows})

    # C-P10 Skill 未改动（与仓库内锁定的 Skill 比对哈希）
    skill_local = case / "skill" / "SKILL.md"
    skill_sha = hashlib.sha256(skill_local.read_bytes()).hexdigest() if skill_local.exists() else None
    skill_repo = None
    if args.clean and args.clean.exists():
        cand = args.clean.parent.parent / "skill" / "SKILL.md"
        if cand.exists():
            skill_repo = hashlib.sha256(cand.read_bytes()).hexdigest()
    add("C-P10", "本次加载的 Skill 与仓库锁定版本一致（未改动）",
        bool(skill_sha) and (skill_repo is None or skill_sha == skill_repo),
        {"local_skill_sha256": skill_sha, "repo_skill_sha256": skill_repo})

    # 跨来源数值交叉核对：表格 0.2565 vs 正文 0.256525
    def num_of(cid: str) -> float | None:
        for r in claims:
            if r["claim_id"] == cid:
                try:
                    return float(r["numeric_value"])
                except ValueError:
                    return None
        return None

    a, b = num_of("C25"), num_of("C02")
    rel = abs(a - b) / max(abs(a), abs(b)) if (a is not None and b is not None) else None
    add("XNUM", "表格 CORE 0.2565 与正文 0.256525 的相对误差 < 1%", rel is not None and rel <= 0.01,
        {"table_value": a, "prose_value": b, "relative_error": rel})

    counts = {
        "claims_total": len(claims),
        "paper_fact": sum(1 for r in claims if r["classification"] == "paper-fact"),
        "inference": sum(1 for r in claims if r["classification"] == "inference"),
        "undetermined": sum(1 for r in claims if r["classification"] == "undetermined"),
        "preconditions_total": len(pre),
        "preconditions_stated": sum(1 for r in pre if r["confidence"].strip() == "stated"),
        "preconditions_absent": sum(1 for r in pre if r["confidence"].strip() == "absent"),
        "downgraded_total": sum(1 for r in claims if r["classification"] == "undetermined")
        + sum(1 for r in pre if r["confidence"].strip() == "absent"),
        "evidence_entries": len(evidence),
    }

    report = {
        "schema_version": "caseC/verification/v1",
        "material_sha256": digest,
        "all_ok": all(c["ok"] for c in checks),
        "checks": checks,
        "counts": counts,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for c in checks:
        print(f"[{'PASS' if c['ok'] else 'FAIL'}] {c['check']}: {c['desc']}")
    print("counts:", json.dumps(counts, ensure_ascii=False))
    print("all_ok:", report["all_ok"])
    return 0 if report["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
