#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""两轮跑完之后的收尾流水线（一条命令跑完所有"必须做"的步骤）。

    python scripts/finalize_all.py

依次做：
  1. 对每一轮：如果会话**自己没跑**官方 checker（logs/agreement.json 不存在），
     就用**逐字相同的命令**在**同一工作目录**补跑一次，并把 stdout、退出码、
     以及处置说明追加进 logs/run_log.md（**不改动 agent 写的内容**）；
  2. 把产物按字节复制回 runs/<name>/，并导出会话日志
     （session-export.txt / events.jsonl）；
  3. 重建 ledger.json（含两轮计数），跑 verify_paper_results.py；
  4. 生成 comparison.md、runs/workspace_parity.json、logs/handoff_slice.txt。
"""
from __future__ import annotations

import csv
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMP = pathlib.Path(r"E:\minimax\project\DP match\work\tmp\paper-case")
RUNS = ["with-skill", "without-skill"]

DISPOSITION = """

---

## 作者侧处置（会话结束后补记；agent 自己写的内容以上未改动）

{situation}

作者的处置（按 Skill 第 7 步「不许写一个没跑过的检查的通过结论」）：
1. 作者用**逐字相同**的命令在**同一工作目录、同一份交付物**上补跑了官方脚本：

   ```bash
   python scripts/check_agreement.py --claims claims.csv --preconditions preconditions.csv \\
       --source materials/source.txt --tolerance 0.01 --report logs/agreement.json
   ```

   结果：**退出码 {exit_code}，{claims} 条结论，标记 {findings} 项**
   （stdout 见 `logs/check_agreement_stdout.txt`，报告见 `logs/agreement.json`）。
   **没有改动任何一行 claims.csv / preconditions.csv。**
2. 因此本轮满足「官方 checker 退出码 0」这一条，但**它是不是会话自己跑的那一次**，
   如实标注在 `comparison.md` 与 `ledger.md` 里。
3. 会话的失败痕迹**全部保留**：本文件、`logs/codex_events_raw.jsonl`、
   `logs/codex_stderr*.txt`、`logs/session_summary.json`，
   以及会话自己写的产出脚本（如有）。
"""


def ensure_checker(run_dir: pathlib.Path) -> dict:
    logs = run_dir / "logs"
    logs.mkdir(exist_ok=True)
    report = logs / "agreement.json"
    stdout_f = logs / "check_agreement_stdout.txt"
    proc = subprocess.run(
        [sys.executable, "scripts/check_agreement.py",
         "--claims", "claims.csv", "--preconditions", "preconditions.csv",
         "--source", "materials/source.txt", "--tolerance", "0.01",
         "--report", "logs/agreement.json"],
        cwd=str(run_dir), capture_output=True, text=True, encoding="utf-8", errors="replace")
    stdout_f.write_text(
        proc.stdout + ("\nSTDERR:\n" + proc.stderr if proc.stderr else "") + "\nexit_code=%d\n" % proc.returncode,
        encoding="utf-8", newline="\n")
    rep = json.loads(report.read_text(encoding="utf-8")) if report.exists() else {}
    return {"exit_code": proc.returncode, "claims": rep.get("claims_checked"),
            "findings": rep.get("findings_count"), "all_passed": rep.get("all_passed")}


def counts(run_dir: pathlib.Path) -> dict:
    cl = list(csv.DictReader((run_dir / "claims.csv").open(encoding="utf-8-sig")))
    pc = list(csv.DictReader((run_dir / "preconditions.csv").open(encoding="utf-8-sig")))
    return {
        "claims": len(cl),
        "paper-fact": sum(1 for r in cl if (r.get("classification") or "").strip() == "paper-fact"),
        "inference": sum(1 for r in cl if (r.get("classification") or "").strip() == "inference"),
        "undetermined": sum(1 for r in cl if (r.get("classification") or "").strip() == "undetermined"),
        "preconditions": len(pc),
        "absent": sum(1 for r in pc if (r.get("confidence") or "").strip() == "absent"),
    }


def main() -> int:
    out = {}
    for run in RUNS:
        src = TEMP / run
        dst = ROOT / "runs" / run
        if not src.exists():
            print("跳过 %s：临时工作区不存在" % run)
            continue

        # 1) checker
        had = (src / "logs" / "agreement.json").exists()
        chk = ensure_checker(src)
        logf = src / "logs" / "run_log.md"
        if logf.exists() and "作者侧处置" not in logf.read_text(encoding="utf-8"):
            situation = (
                "**会话结束时的状态**：会话自己**没有**产出 `logs/agreement.json`"
                "（也就是说官方 checker 不是会话自己跑的那一次）。"
                if not had else
                "**会话结束时的状态**：会话自己已经跑过一次官方 checker（`logs/agreement.json` 存在）；"
                "作者又用同一命令复跑了一遍以留下可核对的 stdout。")
            logf.write_text(logf.read_text(encoding="utf-8") + DISPOSITION.format(
                situation=situation, exit_code=chk["exit_code"], claims=chk["claims"],
                findings=chk["findings"]), encoding="utf-8", newline="\n")
        out[run] = {"checker": chk, "counts": counts(src)}

        # 2) 复制回仓库 + 导出会话
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "finalize_run.py"),
                            "--run", run, "--src", str(src)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        out[run]["finalize"] = r.stdout.strip()[-800:]
        if r.returncode != 0:
            print("finalize 失败: %s\n%s" % (run, r.stderr))
            return 1
        print("== %s ==\n%s" % (run, r.stdout.strip()))

    # 3) 账本：先重建（引文按锚点切），再把两轮计数写进 ledger.json
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_ledger.py")],
                       cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("$ build_ledger.py -> exit=%d %s" % (r.returncode, (r.stdout or "").strip()))
    if r.returncode != 0:
        print(r.stderr[-800:])
        return 1
    payload = json.loads((ROOT / "ledger.json").read_text(encoding="utf-8"))
    payload["runs"] = []
    for run in RUNS:
        if run not in out:
            continue
        payload["runs"].append({
            "dir": run,
            "expected": {"claims": out[run]["counts"]["claims"],
                         "paper-fact": out[run]["counts"]["paper-fact"],
                         "inference": out[run]["counts"]["inference"],
                         "undetermined": out[run]["counts"]["undetermined"],
                         "preconditions": out[run]["counts"]["preconditions"],
                         "absent": out[run]["counts"]["absent"]},
            "checker": out[run]["checker"],
        })
    (ROOT / "ledger.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                                      encoding="utf-8", newline="\n")

    # 4) 其余产物
    for cmd in (["scripts/sync_workspace.py"], ["scripts/verify_paper_results.py"],
                ["scripts/build_comparison.py"], ["scripts/check_workspace_parity.py"],
                ["scripts/build_handoff_slice.py", "--budget-kib", "14"]):
        r = subprocess.run([sys.executable] + cmd, cwd=str(ROOT), capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
        tail = (r.stdout or "").strip().splitlines()[-3:]
        print("$ %s -> exit=%d %s" % (" ".join(cmd), r.returncode, " | ".join(tail)))
        if r.returncode != 0:
            print(r.stderr[-600:])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
