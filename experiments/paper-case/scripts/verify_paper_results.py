#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""作者侧独立重算：把本案例报告里引用的每个数字，**回到论文原文**重算一遍。

    cd experiments/paper-case && python scripts/verify_paper_results.py

结尾打印 `status: passed` / `status: failed`；任一条对不上 → 退出码 1。只依赖标准库。

它检查五层：
  A. 材料完整性 —— PDF / source.txt / source_pages.json 的 SHA-256 与 source_manifest.json 一致
  B. 账本逐条重算 —— 每条：引文逐字命中 + 页码 + 算式复算 + 判定自洽
  C. 两轮运行的计数与官方 checker 复跑
  D. 语义层检查 —— 表格行列身份、相对降幅的绝对量闭合（机械检查抓不到的那一层）
  E. 冻结件 —— cases/ 与 SKILL.md 自冻结起未被改动

数据在 `ledger.json`（机器可读账本），人读版在 `ledger.md`。
"""
from __future__ import annotations

import ast
import csv
import hashlib
import json
import operator
import pathlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = pathlib.Path(__file__).resolve().parent.parent
LEDGER = ROOT / "ledger.json"
MANIFEST = ROOT / "materials" / "source_manifest.json"
SOURCE_TXT = ROOT / "materials" / "source.txt"

OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}
RESULTS = []


def safe_eval(expr: str) -> float:
    """只允许数字与四则运算的算式求值（算式来自 ledger.json，作者自己写的）。"""
    tree = ast.parse(expr.strip(), mode="eval")

    def walk(node):
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in OPS:
            return OPS[type(node.op)](walk(node.left), walk(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
            return OPS[type(node.op)](walk(node.operand))
        raise ValueError("算式里有不被允许的语法: %r" % (expr,))

    return float(walk(tree))


def add(i, item, source, recomputed, ok, note="", gap=False):
    RESULTS.append((i, "GAP" if gap else ("OK" if ok else "MISMATCH"), item, source, recomputed, note))
    return ok


def sha256_of(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def page_of(text: str, quote: str):
    """引文落在 source.txt 的哪一页（页码从 1 开始）。"""
    parts = re.split(r"(?m)^=== PAGE (\d+) ===$", text)
    i = 1
    while i < len(parts):
        no, body = parts[i], parts[i + 1]
        if quote in body:
            return int(no)
        i += 2
    return None


def check_entries(ledger, source_text):
    ok_all = True
    for e in ledger["entries"]:
        i = e["id"]
        item = e["item"]
        src = e.get("source_locator", "")
        note = e.get("notes", "")

        # B1. 引文逐字命中（唯一）且页码正确
        quote = e.get("quote", "")
        qfile = ROOT / e.get("quote_file", "materials/source.txt")
        if quote:
            hay = qfile.read_text(encoding="utf-8")
            n_all = hay.count(quote)
            pg = page_of(source_text, quote) if qfile == SOURCE_TXT else e.get("page")
            want_pg = e.get("page")
            ok_q = (n_all == 1) and (want_pg is None or pg == want_pg)
            ok_all &= add(i + "q", "引文逐字命中（唯一）且页码正确", src,
                          "命中 %d 次，落在第 %s 页（账本写 %s）" % (n_all, pg, want_pg),
                          ok_q, note)
            if not ok_q:
                continue

        # B2. 算式复算（作者侧写下的算式，重新求值）
        if e.get("computation"):
            try:
                val = safe_eval(e["computation"])
            except Exception as exc:  # noqa: BLE001
                ok_all &= add(i + "c", "算式复算：%s" % item, src, "算式无法求值: %s" % exc, False)
                continue
            exp = float(e["recomputed_value"])
            tol = float(e.get("tolerance", 1e-9))
            close = abs(val - exp) <= tol * max(1.0, abs(exp))
            ok_all &= add(i + "c", "算式复算：%s" % item, src,
                          "%s = %.10g（账本记 %.10g）" % (e["computation"], val, exp), close)

            # B2b. 若论文给的是四舍五入后的值，核对四舍五入
            if e.get("round_to") is not None and e.get("paper_value") is not None:
                nd = int(e["round_to"])
                got = round(val, nd)
                want = float(e["paper_value"])
                ok_all &= add(i + "r", "论文写的数是复算值四舍五入到 %d 位小数" % nd, src,
                              "复算 %.10g → %g（论文写 %g）" % (val, got, want),
                              abs(got - want) < 1e-12)

        # B3. 论文写的数 vs 作者复算值：符 / 不符
        if e.get("paper_value") is not None and e.get("paper_tolerance") is not None:
            pv = float(e["paper_value"])
            rv = float(e["recomputed_value"])
            pt = float(e["paper_tolerance"])
            rel = abs(pv - rv) / max(abs(pv), 1e-12)
            if e.get("verdict") in ("不符", "discrepancy"):
                ok = rel > pt
                why = ("确认不一致：论文写 %g，作者复算 %g，相对差 %.4f%%（超过容差 %.4f%%）"
                       % (pv, rv, rel * 100, pt * 100))
            else:
                ok = rel <= pt
                why = ("论文写 %g，作者复算 %g，相对差 %.4f%%（容差 %.4f%%）"
                       % (pv, rv, rel * 100, pt * 100))
            ok_all &= add(i + "p", "论文写的数 vs 作者复算值：%s" % e["item"], src, why, ok,
                          e.get("notes", ""))
    return ok_all


def check_runs(ledger):
    ok_all = True
    for run in ledger["runs"]:
        rd = ROOT / "runs" / run["dir"]
        claims_p = rd / "claims.csv"
        pre_p = rd / "preconditions.csv"
        if not claims_p.exists():
            ok_all &= add("D-" + run["dir"], "%s 的结论台账存在" % run["dir"], run["dir"], "文件缺失", False)
            continue
        cl = list(csv.DictReader(claims_p.open(encoding="utf-8-sig")))
        c3 = [sum(1 for r in cl if (r.get("classification") or "").strip() == k)
              for k in ("paper-fact", "inference", "undetermined")]
        pre = list(csv.DictReader(pre_p.open(encoding="utf-8-sig"))) if pre_p.exists() else []
        absent = sum(1 for r in pre if (r.get("confidence") or "").strip() == "absent")
        got = {"claims": len(cl), "paper-fact": c3[0], "inference": c3[1],
               "undetermined": c3[2], "preconditions": len(pre), "absent": absent}
        ok_all &= add("D-" + run["dir"], "%s 的台账计数" % run["dir"],
                      "%s/{claims,preconditions}.csv" % run["dir"],
                      json.dumps(got, ensure_ascii=False),
                      all(got[k] == v for k, v in run["expected"].items()),
                      "与账本登记一致才算数")

        outp = ROOT / "runs" / ("_recheck_%s.json" % run["dir"])
        proc = subprocess.run(
            [sys.executable, str(rd / "scripts" / "check_agreement.py"),
             "--claims", "claims.csv", "--preconditions", "preconditions.csv",
             "--source", "materials/source.txt", "--tolerance", "0.01",
             "--report", str(outp)],
            cwd=str(rd), capture_output=True, text=True, encoding="utf-8", errors="replace")
        repj = json.loads(outp.read_text(encoding="utf-8")) if outp.exists() else {}
        ok_all &= add("D-%s-check" % run["dir"], "%s 官方 checker 复跑" % run["dir"],
                      "scripts/check_agreement.py",
                      "exit=%d claims_checked=%s findings=%s all_passed=%s"
                      % (proc.returncode, repj.get("claims_checked"),
                         repj.get("findings_count"), repj.get("all_passed")),
                      proc.returncode == 0 and repj.get("findings_count") == 0
                      and repj.get("all_passed") is True,
                      "脚本原样跑，退出码 0 才算通过")
    return ok_all


def check_semantic(ledger):
    """语义层：机械检查抓不到的那一层。expect_differs=true 表示「确认存在差异」。"""
    ok_all = True
    for e in ledger.get("semantic_checks", []):
        try:
            val = safe_eval(e["computation"])
        except Exception as exc:  # noqa: BLE001
            ok_all &= add(e["id"], e["item"], e.get("source_locator", ""),
                          "算式无法求值: %s" % exc, False)
            continue
        exp = float(e["expected_value"])
        tol = float(e.get("tolerance", 1e-9))
        if e.get("expect_differs"):
            ok = abs(val - exp) > tol * max(1e-12, abs(exp))
            why = "确认存在差异（复算 %.10g ≠ 期望参照 %.10g）" % (val, exp)
        else:
            ok = abs(val - exp) <= tol * max(1.0, abs(exp))
            why = "%s = %.10g（期望 %.10g）" % (e["computation"], val, exp)
        ok_all &= add(e["id"], e["item"], e.get("source_locator", ""), why, ok, e.get("notes", ""))
    return ok_all


def check_frozen(ledger):
    ok_all = True
    frozen = json.loads((ROOT / "cases" / "frozen_hashes.json").read_text(encoding="utf-8"))
    for f in frozen["files"]:
        if f["path"] == "skill/SKILL.md":
            p = ROOT / "runs" / "with-skill" / "skill" / "SKILL.md"
        else:
            p = ROOT / "cases" / Path(f["path"]).name
        if not p.exists():
            ok_all &= add("E-" + f["path"], "冻结件仍在", f["path"], "文件缺失", False)
            continue
        got_b, got_h = p.stat().st_size, sha256_of(p)
        ok_all &= add("E-" + f["path"], "冻结件未被改动（%s）" % f["path"], "cases/frozen_hashes.json",
                      "%d B / %s" % (got_b, got_h),
                      got_b == f["bytes"] and got_h == f["sha256"],
                      "冻结于 %s" % frozen["frozen_at_utc"])
    return ok_all


def main() -> int:
    ok_all = True
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    source_text = SOURCE_TXT.read_text(encoding="utf-8")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    for f in manifest["files"]:
        p = ROOT / f["path"]
        if not p.exists():
            ok_all &= add("A-" + f["path"], "材料文件存在且哈希一致", f["path"], "文件缺失", False)
            continue
        got_b, got_h = p.stat().st_size, sha256_of(p)
        ok_all &= add("A-" + f["path"], "%s 字节数 + SHA-256" % f["path"], "materials/source_manifest.json",
                      "%d B / %s" % (got_b, got_h),
                      got_b == f["bytes"] and got_h == f["sha256"])

    ok_all &= check_entries(ledger, source_text)
    ok_all &= check_runs(ledger)
    ok_all &= check_semantic(ledger)
    ok_all &= check_frozen(ledger)

    print("=== 作者侧独立重算（本案例的每个数字回到论文原文重算一遍）===")
    for i, v, item, src, rec, note in RESULTS:
        print("%-24s %-8s %s" % (i, v, item))
        print("%-24s 来源: %s" % ("", src))
        print("%-24s 复算: %s" % ("", rec))
        if note:
            print("%-24s 注  : %s" % ("", note))
    bad = [r for r in RESULTS if r[1] == "MISMATCH"]
    gap = [r for r in RESULTS if r[1] == "GAP"]
    print()
    print("status: %s（%d 条检查，%d 条不符，%d 条已知缺口）"
          % ("passed" if not bad else "failed", len(RESULTS), len(bad), len(gap)))
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
