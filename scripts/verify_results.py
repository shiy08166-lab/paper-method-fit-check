#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把本作品正文里的每个数字**重新算一遍**（只依赖标准库）。

    cd <材料包根目录> && python3 scripts/verify_results.py

结尾打印 `status: passed` / `status: failed`；任一条对不上 → 退出码 1。

其中 L-07 是本次的**自我修正**：受损表的列语义是**逐行不同**的
（#0 行丢 val_bpb 占位符、#1–#6 行丢 CORE 值），所以「第 3 格一律是 CORE」
只对 1/7 行成立——我们自己的 C29 列映射假设过强，而它唯一的旁证
恰好来自那唯一成立的一行。结论词与降级集合不受影响（受损表整表不作出处）。
"""
import csv
import hashlib
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MAT = ROOT / "paper_materials" / "nanochat_README_table_corrupted.md"
UP = ROOT / "paper_materials" / "nanochat_README_leaderboard_upstream.md"
LEDGER = []


def rows_of(t):
    return [[c.strip() for c in ln.strip().strip("|").split("|")]
            for ln in t.split("\r\n") if ln.startswith("|")]


def add(i, item, source, recomputed, ok, note="", gap=False):
    LEDGER.append((i, "GAP" if gap else ("OK" if ok else "MISMATCH"), item, source, recomputed, note))
    return ok


def main():
    ok_all = True
    mat = MAT.read_bytes()
    text = mat.decode("utf-8")
    up_text = UP.read_bytes().decode("utf-8")

    ok_all &= add("L-01", "损坏件 SHA-256 与字节数", "paper_materials/nanochat_README_table_corrupted.md",
                  "%s / %d B" % (hashlib.sha256(mat).hexdigest(), len(mat)),
                  hashlib.sha256(mat).hexdigest() ==
                  "64a46d328926d45842d9e8ad0a1817b01d176ad915e55ba92609119ca571917c" and len(mat) == 17623)

    co = rows_of(text)
    head, sep = co[0], co[1]
    data = [r for r in co[2:] if r and r[0].isdigit()]
    cc = [len(r) for r in data]
    labels = [r[0] for r in data]
    ok_all &= add("L-02", "表头格数 / 分隔行格数 / 数据行格数 / # 物理顺序", "受损件 L31/L32/L33–L39",
                  "head=%d sep=%d rows=%d counts=%s labels=%s"
                  % (len(head), len(sep), len(data), cc, labels),
                  len(head) == 7 and len(sep) == 8 and len(data) == 7
                  and cc == [7, 7, 7, 7, 7, 7, 9] and labels == ["6", "1", "4", "0", "3", "2", "5"])
    ok_all &= add("L-03", "被截断的 time 单元格属于哪一行", "受损件 L35",
                  "labels=%s" % [r[0] for r in data if len(r) > 1 and re.fullmatch(r"\d+\.", r[1])],
                  [r[0] for r in data if len(r) > 1 and re.fullmatch(r"\d+\.", r[1])] == ["4"])
    ok_all &= add("L-04", "多出 2 格的行（9 格）及其标签", "受损件 L39",
                  "labels=%s" % [r[0] for r in data if len(r) != len(head)],
                  [r[0] for r in data if len(r) != len(head)] == ["5"])

    up = rows_of(up_text)
    up_head = up[0]
    up_data = {r[0]: r for r in up[1:] if r and r[0].isdigit()}
    co_data = {r[0]: r for r in data}
    mp = {}
    for lab in sorted(set(up_data) & set(co_data)):
        u, c = up_data[lab], co_data[lab]
        drop = next((i for i in range(len(u)) if u[:i] + u[i + 1:] == c), None)
        cell3 = c[2] if len(c) > 2 else ""
        hits = [i for i, uc in enumerate(u) if uc == cell3]
        if drop is not None:
            hits = [i for i in hits if i != drop] or hits
        mp[lab] = (up_head[drop] if drop is not None else "（本格另有改动）",
                   up_head[hits[0]] if hits else "（该值在上游行中找不到）")
    ok_all &= add("L-05", "上游原表列名与索引", "上游 leaderboard 节选",
                  " | ".join("%s=%d" % (h, i) for i, h in enumerate(up_head)), True)
    ok_all &= add("L-06", "受损表第 3 格的真实列语义（逐行）", "上游原表逐格对齐",
                  "; ".join("#%s 删的是 %s → 第3格装的是 %s" % (k, v[0], v[1]) for k, v in sorted(mp.items())),
                  mp["0"][1] == "CORE" and all(mp[l][1] == "val_bpb" for l in "123456"),
                  "#0 行删的是 val_bpb（占位符 '-'）→ 第3格是真 CORE；#1–#6 行删的是 CORE 值 → 第3格是 val_bpb")
    ok_all &= add("L-07", "自我修正：受损表第 3 格**不是**一律 CORE", "runs/C-with-3/verdict.md 的 C29 列映射假设",
                  "仅 #0 行成立；#1–#6 行第3格是上游 val_bpb", True,
                  "C29 的唯一旁证（#0 行 0.2565 vs 正文 0.256525 差 0.0098%）恰好来自那唯一成立的一行，"
                  "不能推广到其余 6 行。结论词与降级集合不受影响。")

    rel = abs(0.2565 - 0.256525) / 0.256525
    ok_all &= add("L-08", "表格 #0 行 0.2565 与正文 0.256525 的相对误差", "受损件 L36 ↔ L41",
                  "%.6f%%" % (rel * 100), abs(rel * 100 - 0.0098) < 0.0002,
                  "该差值成立的前提是 #0 行第3格确为上游 CORE（见 L-07）")
    cost = 8 * 4 * 3
    ok_all &= add("L-09", "成本闭合：8 卡 × 4 h × $3/GPU·h", "受损件 L41（材料自身单价）",
                  "$%d ≤ $100（余量 4%%）" % cost, cost == 96)

    for run, cp, pp, exp in [("C-with-3", "runs/C-with-3/claims.csv", "runs/C-with-3/preconditions.csv",
                              (39, 28, 4, 7, 32, 21, 11)),
                             ("C-with-1", "runs/C-with-1/claims.csv", "runs/C-with-1/preconditions.csv",
                              (62, 37, 15, 10, 28, 22, 6))]:
        if not (ROOT / cp).exists():
            add("L-10" if run == "C-with-3" else "L-11",
                "%s 的结论台账计数（条数/三分类）" % run, cp, "该文件未随包", False,
                "该轮台账未随包（见公开仓库）→ 其计数在本包内不可复算，如实标注", gap=True)
            continue
        cl = list(csv.DictReader((ROOT / cp).open(encoding="utf-8-sig")))
        c3 = [sum(1 for r in cl if r["classification"] == k) for k in ("paper-fact", "inference", "undetermined")]
        if not (ROOT / pp).exists():
            ok_all &= add("L-10" if run == "C-with-3" else "L-11",
                          "%s 的结论台账计数（条数/三分类）" % run, cp, str((len(cl),) + tuple(c3)),
                          (len(cl),) + tuple(c3) == exp[:4],
                          "该轮的结论台账与前置条件台账均未随包（见公开仓库），其 62/37/15/10 与 28/22/6 在本包内**不可复算**——如实标注")
            continue
        pc = list(csv.DictReader((ROOT / pp).open(encoding="utf-8-sig")))
        got = (len(cl), c3[0], c3[1], c3[2], len(pc),
               sum(1 for r in pc if r.get("confidence") == "stated"),
               sum(1 for r in pc if r.get("confidence") == "absent"))
        ok_all &= add("L-10" if run == "C-with-3" else "L-11",
                      "%s 的台账计数（结论/三分类/前置条件/absent）" % run, cp + " + " + pp, str(got), got == exp)

    bad_hit, bad_disc, n_fact = [], [], 0
    for r in csv.DictReader((ROOT / "runs/C-with-3/claims.csv").open(encoding="utf-8-sig")):
        if r["classification"] == "paper-fact":
            n_fact += 1
            q = r["quote"]
            if not q or text.count(q) != 1:
                bad_hit.append((r["claim_id"], text.count(q) if q else 0))
        elif (r.get("quote") or "").strip() or (r.get("numeric_value") or "").strip():
            bad_disc.append(r["claim_id"])
    ok_all &= add("L-12", "C-with-3：paper-fact 引文在材料里唯一命中；非事实行不带引文/数值",
                  "runs/C-with-3/claims.csv vs 材料字节",
                  "paper-fact=%d 命中异常=%s 纪律异常=%s" % (n_fact, bad_hit or "无", bad_disc or "无"),
                  not bad_hit and not bad_disc)

    cf = ROOT / "science-space" / "cloud_claims_paperfact.csv"
    if cf.exists():
        rs = list(csv.DictReader(cf.open(encoding="utf-8-sig")))
        bad = [(r["claim_id"], text.count(r["quote"])) for r in rs if text.count(r["quote"]) != 1]
        ok_all &= add("L-13", "玻尔云端 12 条 paper-fact 引文在材料里唯一命中",
                      "science-space/cloud_claims_paperfact.csv",
                      "%d 条，异常=%s" % (len(rs), bad or "无"), not bad)

    out = ROOT / "agreement_recheck.json"
    p = subprocess.run([sys.executable, "scripts/check_agreement.py",
                        "--claims", "runs/C-with-3/claims.csv",
                        "--preconditions", "runs/C-with-3/preconditions.csv",
                        "--source", "paper_materials/nanochat_README_table_corrupted.md",
                        "--tolerance", "0.01", "--report", str(out)],
                       cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    rep = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    ok_all &= add("L-14", "官方 checker 复跑（39 条结论）", "scripts/check_agreement.py",
                  "exit=%d claims_checked=%s findings=%s all_passed=%s"
                  % (p.returncode, rep.get("claims_checked"), rep.get("findings_count"), rep.get("all_passed")),
                  p.returncode == 0 and rep.get("findings_count") == 0 and rep.get("all_passed") is True)

    BIN = {".png", ".jpg", ".jpeg", ".pdf", ".zip", ".gif"}
    tot = sum(f.stat().st_size for f in ROOT.rglob("*") if f.is_file() and f.suffix.lower() not in BIN)
    ok_all &= add("L-15", "材料包提取后文本 ≤ 240 KiB", "本包全部文本文件求和",
                  "%d B (%.1f KiB)，上限 245760" % (tot, tot / 1024), tot <= 245760)

    print("=== LEDGER（本作品正文的每个数字重新算一遍）===")
    for i, v, item, src, rec, note in LEDGER:
        print("%-5s %-8s %s" % (i, v, item))
        print("       来源: %s" % src)
        print("       复算: %s" % rec)
        if note:
            print("       注  : %s" % note)
    bad = [r for r in LEDGER if r[1] == "MISMATCH"]
    gap = [r for r in LEDGER if r[1] == "GAP"]
    print()
    print("status: %s（%d 条账本，%d 条不符，%d 条已知缺口）"
          % ("passed" if not bad else "failed", len(LEDGER), len(bad), len(gap)))
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
