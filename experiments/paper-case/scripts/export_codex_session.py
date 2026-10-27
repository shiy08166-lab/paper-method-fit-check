#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 Codex CLI 的会话 rollout（JSONL）导成两份可复核的产物：

  session-export.txt  —— 会话可见内容的纯文本（人读）
  events.jsonl       —— 一行一个 JSON 事件，步骤类型归一到 Skill 第 8 步要求的
                        thought / tool_call / tool_result / artifact / decision / error / observation

用法：
    python scripts/export_codex_session.py \
        --rollout <~/.codex/sessions/.../rollout-*.jsonl> \
        --out-dir runs/with-skill

说明：rollout 是 Codex 自己写的会话日志（原始证据），本脚本只做**只读**转换，
不修改它。转换规则写在每个事件的 `step` / `kind` 字段里，便于核对。
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

TEXT_KEYS = ("text", "output_text", "message")


def _text_of(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for c in content:
            if isinstance(c, dict):
                if c.get("type") in ("output_text", "input_text", "text"):
                    parts.append(c.get("text") or "")
                elif c.get("type") == "reasoning":
                    for s in c.get("summary") or []:
                        if isinstance(s, dict) and s.get("text"):
                            parts.append(s.get("text"))
            elif isinstance(c, str):
                parts.append(c)
        return "\n".join(p for p in parts if p)
    return ""


def convert(rollout: pathlib.Path):
    events = []
    transcript = []
    session_id = None
    model = None
    usage = None
    started = None
    ended = None
    n = 0

    for line in rollout.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        t = obj.get("type")
        p = obj.get("payload") or {}
        n += 1
        base = {"i": n, "ts": obj.get("timestamp")}

        if t == "session_meta":
            session_id = p.get("session_id")
            model = p.get("model") or p.get("model_provider")
            transcript.append("### session_meta\nsession_id=%s cwd=%s cli=%s originator=%s\n"
                              % (p.get("session_id"), p.get("cwd"), p.get("cli_version"),
                                 p.get("originator")))
            continue

        if t == "event_msg":
            et = p.get("type")
            if et == "task_started":
                started = p.get("started_at")
                transcript.append("### task_started\n")
            elif et == "task_complete":
                ended = p.get("completed_at") or p.get("last_agent_message")
                transcript.append("### task_complete\n")
            elif et == "agent_message":
                msg = p.get("message") or ""
                events.append(dict(base, step="observation", kind="agent_message", text=msg))
            elif et in ("error", "stream_error"):
                events.append(dict(base, step="error", kind=et, detail=p.get("message") or p.get("text") or ""))
            continue

        if t == "response_item":
            it = p.get("type")
            if it == "reasoning":
                s = _text_of(p.get("summary") or [])
                if s:
                    events.append(dict(base, step="thought", kind="reasoning", text=s))
            elif it == "message":
                role = p.get("role")
                txt = _text_of(p.get("content"))
                if role == "assistant" and txt:
                    events.append(dict(base, step="observation", kind="assistant_message", text=txt))
                    transcript.append("### assistant\n%s\n" % txt)
                elif role in ("user", "developer", "system"):
                    transcript.append("### %s\n%s\n" % (role, txt[:4000]))
            elif it in ("function_call", "custom_tool_call", "local_shell_call"):
                events.append(dict(base, step="tool_call", kind=it, name=p.get("name"),
                                   arguments=p.get("arguments") or p.get("input") or p.get("action")))
            elif it in ("function_call_output", "custom_tool_call_output", "local_shell_call_output"):
                out = p.get("output")
                if isinstance(out, dict):
                    out = out.get("content") or json.dumps(out, ensure_ascii=False)
                events.append(dict(base, step="tool_result", kind=it, output=out))
            continue

        if t == "token_usage_record":
            usage = p.get("usage")
            continue

    return {
        "session_id": session_id,
        "model": model,
        "started_at": started,
        "ended_at": ended,
        "usage": usage,
        "events": events,
        "transcript": transcript,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rollout", required=True, type=pathlib.Path)
    ap.add_argument("--out-dir", required=True, type=pathlib.Path)
    args = ap.parse_args()

    if not args.rollout.exists():
        print("缺少 rollout: %s" % args.rollout, file=sys.stderr)
        return 2

    r = convert(args.rollout)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    header = [
        "=== Codex 会话导出 ===",
        "rollout      : %s" % args.rollout,
        "session_id   : %s" % r["session_id"],
        "model        : %s" % r["model"],
        "started_at   : %s" % r["started_at"],
        "ended_at     : %s" % r["ended_at"],
        "token_usage  : %s" % json.dumps(r["usage"], ensure_ascii=False),
        "events_count : %d" % len(r["events"]),
        "step kinds   : thought / tool_call / tool_result / artifact / decision / error / observation",
        "",
    ]
    (args.out_dir / "session-export.txt").write_text(
        "\n".join(header) + "\n".join(r["transcript"]), encoding="utf-8", newline="\n")

    with (args.out_dir / "events.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
        for e in r["events"]:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")

    print("session_id=%s events=%d usage=%s"
          % (r["session_id"], len(r["events"]),
             (r["usage"] or {}).get("total_tokens")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
