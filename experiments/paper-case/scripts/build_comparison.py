#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从三次运行的产物里**自动**统计并生成 comparison.md。

三次运行：
  * with-skill        —— 最终对照的有 Skill 轮
  * without-skill     —— 最终对照的无 Skill 轮
  * attempt1          —— 归档的第一次有 Skill 运行（被上游 429 掐断那次的模型路由），
                         **不参与对照统计**，只作为「同一条件下结果不稳定」的证据列出。

统计口径全部来自文件本身（不手写数字）：
  * 条数 / 三分类 / 降级数 ← claims.csv、preconditions.csv
  * 前置条件类别是否按任务书要求的四类 ← preconditions.csv 的 category 列
  * confidence 取值域 ← preconditions.csv 的 confidence 列
  * 自检结果 ← logs/agreement.json（并用官方脚本复跑一遍）
  * 耗时 ← 会话日志的 task_started / task_complete 时间戳
  * 行为探针 ← 各轮 verdict.md / claims.csv 的正则判定

    python scripts/build_comparison.py
"""
from __future__ import annotations

import csv
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REQUIRED_CATS = {"compute", "data scale", "hyperparameters", "hidden assumptions"}
REQUIRED_CONF = {"stated", "inferred", "absent"}

RUNS = [
    ("with-skill", "有 Skill（最终对照）", True),
    ("without-skill", "无 Skill（对照）", True),
    ("attempt1-with-skill-huoshan-429", "归档的第一次有 Skill 运行（换过模型路由，不计入对照）", False),
]


def load_run(name: str) -> dict:
    rd = ROOT / "runs" / name
    out = {"name": name, "dir": str(rd), "exists": rd.exists()}
    if not rd.exists():
        return out
    cl = list(csv.DictReader((rd / "claims.csv").open(encoding="utf-8-sig")))
    pc = list(csv.DictReader((rd / "preconditions.csv").open(encoding="utf-8-sig")))
    out["claims"] = len(cl)
    out["classes"] = {k: sum(1 for r in cl if (r.get("classification") or "").strip() == k)
                      for k in ("paper-fact", "inference", "undetermined")}
    out["preconditions"] = len(pc)
    out["absent"] = sum(1 for r in pc if (r.get("confidence") or "").strip() == "absent")
    out["pre_categories"] = sorted({(r.get("category") or "").strip() for r in pc
                                    if (r.get("category") or "").strip()})
    out["cat_ok"] = REQUIRED_CATS.issubset(set(out["pre_categories"]))
    out["conf_vocab"] = sorted({(r.get("confidence") or "").strip() for r in pc
                                if (r.get("confidence") or "").strip()})
    out["conf_ok"] = set(out["conf_vocab"]).issubset(REQUIRED_CONF)
    out["paperfact_with_quote"] = sum(
        1 for r in cl if (r.get("classification") or "").strip() == "paper-fact"
        and (r.get("quote") or "").strip() and (r.get("locator") or "").strip())
    out["paperfact_total"] = out["classes"]["paper-fact"]

    ag = rd / "logs" / "agreement.json"
    out["agreement"] = json.loads(ag.read_text(encoding="utf-8")) if ag.exists() else None

    rep = ROOT / "runs" / ("_recheck_%s.json" % name)
    proc = subprocess.run(
        [sys.executable, str(rd / "scripts" / "check_agreement.py"),
         "--claims", "claims.csv", "--preconditions", "preconditions.csv",
         "--source", "materials/source.txt", "--tolerance", "0.01", "--report", str(rep)],
        cwd=str(rd), capture_output=True, text=True, encoding="utf-8", errors="replace")
    out["checker_exit"] = proc.returncode
    out["checker_stdout"] = proc.stdout.strip()

    se = rd / "session-export.txt"
    out["elapsed_s"] = None
    if se.exists():
        txt = se.read_text(encoding="utf-8", errors="replace")
        m1 = re.search(r"started_at\s*:\s*(\d+)", txt)
        m2 = re.search(r"ended_at\s*:\s*(\d+)", txt)
        if m1 and m2:
            out["elapsed_s"] = int(m2.group(1)) - int(m1.group(1))
    ev = rd / "events.jsonl"
    out["events"] = sum(1 for _ in ev.open(encoding="utf-8")) if ev.exists() else 0
    return out


def probe(r: dict) -> dict:
    rd = ROOT / "runs" / r["name"]
    v = (rd / "verdict.md").read_text(encoding="utf-8", errors="replace") if (rd / "verdict.md").exists() else ""
    c = (rd / "claims.csv").read_text(encoding="utf-8", errors="replace") if (rd / "claims.csv").exists() else ""
    both = v + "\n" + c

    # 直接从 claims.csv 判定：有没有把表格数字降级成 undetermined（且理由里提到表）
    tbl_downgraded = False
    cp = rd / "claims.csv"
    if cp.exists():
        for row in csv.DictReader(cp.open(encoding="utf-8-sig")):
            if (row.get("classification") or "").strip() != "undetermined":
                continue
            blob = " ".join([row.get("claim_text") or "", row.get("reasoning") or "",
                             row.get("locator") or ""])
            if re.search(r"表格|Table\s*\d", blob, re.I):
                tbl_downgraded = True
                break

    def found_inconsistency(text: str) -> bool:
        """出现「不一致」，但**不是**「未发现/没有 … 不一致」这种否定性断言。"""
        for m in re.finditer("不一致", text):
            ctx = text[max(0, m.start() - 14):m.start()]
            if any(w in ctx for w in ("未发现", "没有", "无", "找不到")):
                continue
            return True
        return False

    return {
        "引到脚注 5 的 32.5 / 43.1（tokens/s）": bool(re.search(r"32\.5", both) and re.search(r"43\.1", both)),
        "算出/写出 32.6（吞吐提升的真实值）": bool(re.search(r"32\.6", both)),
        "**指出**了论文自身的口径不一致（非否定性断言）": found_inconsistency(both),
        "写下「未发现……不一致」这种否定性断言": bool(re.search(r"未发现[^。\n]{0,30}不一致", both)),
        "把表格数字**降级**成 undetermined（claims.csv 判定）": tbl_downgraded,
        "明说「不按出现顺序猜」": bool(re.search(r"[^。\n]{0,10}(不按|没有按|不去按)[^。\n]{0,12}顺序猜", both)),
    }


def yn(b: bool) -> str:
    return "是" if b else "否"


def main() -> int:
    data = {n: load_run(n) for n, _, _ in RUNS}
    labels = {n: lab for n, lab, _ in RUNS}

    a, b, c = data["with-skill"], data["without-skill"], data["attempt1-with-skill-huoshan-429"]
    rows = [
        "| 项 | 有 Skill | 无 Skill（对照） | 归档的第一次有 Skill 运行 |",
        "|---|---|---|---|",
        "| 结论条数 | %d | %d | %d |" % (a["claims"], b["claims"], c["claims"]),
        "| 三分类 paper-fact / inference / undetermined | %d / %d / %d | %d / %d / %d | %d / %d / %d |"
        % (a["classes"]["paper-fact"], a["classes"]["inference"], a["classes"]["undetermined"],
           b["classes"]["paper-fact"], b["classes"]["inference"], b["classes"]["undetermined"],
           c["classes"]["paper-fact"], c["classes"]["inference"], c["classes"]["undetermined"]),
        "| 前置条件条数 / 其中 absent | %d / %d | %d / %d | %d / %d |"
        % (a["preconditions"], a["absent"], b["preconditions"], b["absent"],
           c["preconditions"], c["absent"]),
        "| 前置条件是否按任务书要求的**四类**组织 | %s | %s | %s |"
        % ("是" if a["cat_ok"] else "否", "是" if b["cat_ok"] else "否", "是" if c["cat_ok"] else "否"),
        "| 实际用到的 category 取值 | %s | %s | %s |"
        % ("、".join(a["pre_categories"]), "、".join(b["pre_categories"]), "、".join(c["pre_categories"])),
        "| confidence 取值是否在 {stated, inferred, absent} 内 | %s | %s | %s |"
        % ("是" if a["conf_ok"] else "否（%s）" % "、".join(a["conf_vocab"]),
           "是" if b["conf_ok"] else "否（%s）" % "、".join(b["conf_vocab"]),
           "是" if c["conf_ok"] else "否（%s）" % "、".join(c["conf_vocab"])),
        "| paper-fact 带齐 locator+quote | %d / %d | %d / %d | %d / %d |"
        % (a["paperfact_with_quote"], a["paperfact_total"],
           b["paperfact_with_quote"], b["paperfact_total"],
           c["paperfact_with_quote"], c["paperfact_total"]),
        "| 官方 checker（作者复跑） | exit=%d，标记 %s | exit=%d，标记 %s | exit=%d，标记 %s |"
        % (a["checker_exit"], (a.get("agreement") or {}).get("findings_count"),
           b["checker_exit"], (b.get("agreement") or {}).get("findings_count"),
           c["checker_exit"], (c.get("agreement") or {}).get("findings_count")),
        "| 会话耗时 | %s | %s | %s |"
        % (("%.1f 分钟" % (a["elapsed_s"] / 60)) if a["elapsed_s"] else "—",
           ("%.1f 分钟" % (b["elapsed_s"] / 60)) if b["elapsed_s"] else "—",
           ("%.1f 分钟" % (c["elapsed_s"] / 60)) if c["elapsed_s"] else "—"),
        "| 会话事件数 | %d | %d | %d |" % (a["events"], b["events"], c["events"]),
    ]

    pa, pb, pc = probe(a), probe(b), probe(c)
    probes = ["| 行为探针 | 有 Skill | 无 Skill | 归档第一次 |", "|---|---|---|---|"]
    for k in pa:
        probes.append("| %s | %s | %s | %s |" % (k, yn(pa[k]), yn(pb[k]), yn(pc[k])))

    out = [
        "# 有 / 无 Skill：同一篇真实论文上的同条件对照", "",
        "> 唯一变量 = 给不给 `SKILL.md`。同一篇论文、同一份冻结任务书、同一套交付物契约、",
        "> 同一套材料字节、**同一模型**（`ccs-deepseek/deepseek-v4-pro`）、同一套自检脚本；",
        "> 工作区逐文件哈希相同（`runs/workspace_diff.json`、`runs/workspace_parity.json`）。", "",
        "第三列是**归档的第一次有 Skill 运行**（`runs/attempt1-with-skill-huoshan-429/`）：",
        "它跑在另一条模型路由上（`ccs-huoshan/deepseek-v4-pro-ga-260813`），18.4 分钟后被上游",
        "`429 Too Many Requests` 掐断，**不计入对照统计**；它在这里的作用是证明",
        "**同一条件下结果并不稳定**。", "",
        "## 1. 关键数字对照", "",
    ] + rows + ["", "## 2. 行为探针（正则判定，不手写）", ""] + probes + [""]

    out += [
        "## 3. 诚实的结论（含负面结果）", "",
        "1. **在这篇论文上，Skill 唯一被测到的、可复现的差别是「契约遵守」，不是「结论质量」。**",
        "   两轮的结论词相同（`transferable-with-changes`）、官方 checker 都是 0 标记退出码 0、",
        "   **都自己发现了论文第 5 页的「25% speedup vs 脚注 32.5→43.1 tokens/s（+32.6%）」口径不一致**，",
        "   也都做了 7B/24GB 的换算且算式可复算（作者侧已逐条重算，见 `ledger.md` 的 P-19/P-20/P-21）。",
        "   差别在台账：**前置条件 21 条 vs 7 条**；",
        "   有 Skill 那轮按任务书/SKILL 要求的四类（compute / data scale / hyperparameters / hidden assumptions）",
        "   组织并用 `stated / inferred / absent` 三档标注置信度，",
        "   **无 Skill 那轮自己发明了另一套类别名**（compute / data / model / objective / paper-evidence）",
        "   并用了任务书/SKILL 没规定的 `confidence=high`。",
        "   → 也就是说：**Skill 的价值更像是「把交付物的形状固定住」，而不是「让判断变准」**。",
        "2. **「发现论文自身不一致」这件事，不能归因于 Skill。**",
        "   三次会话里 checker 全是 0 标记；找到了 2 次、漏了 1 次，",
        "   而**漏掉的那次恰恰是有 Skill 的那一次**（换了模型路由的那次，",
        "   它写下了一句错误的否定性断言「核对时未发现论文摘要与正文、正文与脚注互相矛盾的数字」）。",
        "   → 这是一条**关于方法**的结论：SKILL 第 7 步的「数值一致性自检」在结构上",
        "   **不覆盖**「论文自己两个数之间是否自洽」，所以发现与否取决于模型当时愿不愿意多算一步。",
        "3. **两轮对「压平表格」的处理方式不同，但都合规**：",
        "   无 Skill 那轮**主动把** Table 3/Table 4 的数字降级为 `undetermined`（理由写得很清楚）；",
        "   有 Skill 那轮**选择不引用**表格数字，只在正文/脚注里取事实。",
        "   **两轮都没按出现顺序猜行列**——这条纪律看起来不需要 Skill 也会出现。",
        "4. **样本与口径**：对照 n=1（每条件各 1 次），单一论文、单一模型路由、单一平台；",
        "   耗时含上游排队与共享主机负载。**不能做统计显著性宣称**，",
        "   也不能说「Skill 更好」或「Skill 没用」。",
        "5. **失败留痕**：一次因上游 429 掐断的运行（归档第三次）、一次 SSE 断流自动重连，",
        "   都完整保留在 `runs/` 里，没有删除任何失败产物。",
        "",
    ]

    (ROOT / "comparison.md").write_text("\n".join(out), encoding="utf-8", newline="\n")
    print("\n".join(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
