#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跑一次 Codex CLI 会话（真实 agent 会话），并在被上游 429 限流掐断时**续跑**。

    python scripts/run_session.py --workspace <隔离工作区> --out <日志目录>

做的事：
  1. 用 `codex exec -` 把 prompt.txt 从 stdin 喂进去（非交互），--json 事件流落盘；
  2. 如果会话因为上游 429（Too Many Requests）失败，就用 `codex exec resume <thread_id>`
     **续跑同一个会话**（不新建会话、不重发整段上下文）；
  3. 每次尝试单独落一份原始事件流，另存一份合并流；
  4. 把每次尝试的退出码、耗时、错误原样写进 summary.json。

为什么需要它：本次案例的上游路由在长会话末段出现过 429 限流，
**失败必须留痕、也必须把活干完**——续跑比重开会话更接近真实工作流。
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time

EXE = r"C:\Users\30416\AppData\Local\OpenAI\Codex\bin\2993767bd1dfb009\codex.exe"

COMMON_CFG = [
    "-c", "features.apps=false",
    "-c", "features.memories=false",
    "-c", 'model_reasoning_effort="medium"',
    "-c", "mcp_servers.canva.enabled=false",
    "-c", "mcp_servers.consensus.enabled=false",
    "-c", "mcp_servers.context7.enabled=false",
    "-c", "mcp_servers.figma-remote-mcp.enabled=false",
    "-c", "mcp_servers.notion.enabled=false",
    "-c", "mcp_servers.node_repl.enabled=false",
    "-c", "mcp_servers.open-design.enabled=false",
    "-c", "mcp_servers.matlab.enabled=false",
    "-c", "mcp_servers.jev.enabled=false",
]

RESUME_PROMPT = ("继续完成本次任务：检查还缺哪些交付物"
                 "（preconditions.csv / claims.csv / evidence_index.json / verdict.md / logs/agreement.json），"
                 "补齐缺的，并按任务书要求跑官方 checker、写下 logs/run_log.md，"
                 "最后给出任务书「完成时」要求的简短总结。")


def parse_events(text: str) -> dict:
    thread_id = None
    last_err = None
    completed = False
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        if o.get("type") == "thread.started":
            thread_id = o.get("thread_id")
        if o.get("type") == "turn.completed":
            completed = True
        if o.get("type") in ("error", "turn.failed"):
            last_err = o.get("message") or (o.get("error") or {}).get("message")
    return {"thread_id": thread_id, "last_error": last_err, "completed": completed}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True, type=pathlib.Path)
    ap.add_argument("--out", required=True, type=pathlib.Path)
    ap.add_argument("--model", required=True)
    ap.add_argument("--max-attempts", type=int, default=3)
    ap.add_argument("--cooldown", type=int, default=150)
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "logs").mkdir(exist_ok=True)
    prompt = args.workspace / "prompt.txt"

    summary = {"workspace": str(args.workspace), "model": args.model, "attempts": []}
    thread_id = None
    merged = []

    for attempt in range(1, args.max_attempts + 1):
        if attempt > 1:
            time.sleep(args.cooldown)
        if attempt == 1:
            cmd = [EXE, "exec", "-", "-C", str(args.workspace), "--sandbox", "workspace-write",
                   "--skip-git-repo-check", "--json", "-m", args.model] + COMMON_CFG
            stdin_path = prompt
            extra = []
        else:
            if not thread_id:
                summary["attempts"].append({"attempt": attempt, "error": "没有 thread_id，无法续跑"})
                break
            cmd = [EXE, "exec", "resume", thread_id, RESUME_PROMPT, "-C", str(args.workspace),
                   "--sandbox", "workspace-write", "--skip-git-repo-check", "--json"] + COMMON_CFG
            stdin_path = None

        t0 = time.time()
        if stdin_path is not None:
            with stdin_path.open("r", encoding="utf-8") as fh:
                proc = subprocess.run(cmd, stdin=fh, capture_output=True, text=True,
                                      encoding="utf-8", errors="replace")
        else:
            proc = subprocess.run(cmd, input="", capture_output=True, text=True,
                                  encoding="utf-8", errors="replace")
        dt = time.time() - t0
        out_path = args.out / "logs" / ("codex_attempt%d.jsonl" % attempt)
        out_path.write_text(proc.stdout or "", encoding="utf-8", newline="\n")
        err_path = args.out / "logs" / ("codex_stderr_attempt%d.txt" % attempt)
        err_path.write_text(proc.stderr or "", encoding="utf-8", newline="\n")

        info = parse_events(proc.stdout or "")
        thread_id = info["thread_id"] or thread_id
        merged.append({"attempt": attempt, "file": out_path.name,
                       "stderr_file": err_path.name, "exit_code": proc.returncode,
                       "elapsed_s": round(dt, 1), "thread_id": info["thread_id"],
                       "last_error": info["last_error"], "completed": info["completed"]})
        summary["attempts"].append(merged[-1])
        print("[attempt %d] exit=%s %.1fs completed=%s err=%s"
              % (attempt, proc.returncode, dt, info["completed"], info["last_error"]))

        if info["completed"] and proc.returncode == 0:
            break
        if not info["last_error"] or "429" not in str(info["last_error"]):
            break

    # 合并事件流
    with (args.out / "logs" / "codex_events_raw.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
        for a in summary["attempts"]:
            fh.write(json.dumps({"type": "attempt.marker", "attempt": a["attempt"],
                                 "exit_code": a["exit_code"], "elapsed_s": a["elapsed_s"],
                                 "last_error": a["last_error"]}, ensure_ascii=False) + "\n")
            p = args.out / "logs" / a["file"]
            if p.exists():
                fh.write(p.read_text(encoding="utf-8", errors="replace"))
                if not p.read_text(encoding="utf-8", errors="replace").endswith("\n"):
                    fh.write("\n")
    summary["thread_id"] = thread_id
    (args.out / "logs" / "session_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2)[:1500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
