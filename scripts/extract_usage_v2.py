#!/usr/bin/env python3
"""从 MiniMax Code 原生会话记录里抽取客观用量指标（口径 v2）。

与 extract_session_usage.py 的区别：后者按旧字段名（total_tokens / rec['usage']）
取值，在当前运行时写的 messages.jsonl 上取不到值；本脚本按实际结构
（``rec['message']['usage']`` 的 ``totalTokens`` / ``input`` / ``output`` /
``cacheRead``，以及 ``rec['message']['timestamp']``）统计。

口径（已用 A 组两次运行的已知值校准）：
- ``total_tokens``  = 所有 assistant 消息 usage.totalTokens 的**累加**
- ``input_tokens``  = 累加 usage.input
- ``output_tokens`` = 累加 usage.output
- ``cache_read``    = 累加 usage.cacheRead
- ``wall_clock_seconds`` = 首末消息 timestamp 之差（毫秒 → 秒）

用法：
    python3 scripts/extract_usage_v2.py --session <messages.jsonl> --label A-with-1
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="抽取 MiniMax Code 会话用量 (v2)")
    parser.add_argument("--session", required=True, type=Path)
    parser.add_argument("--label", default="")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    n_records = 0
    n_assistant = 0
    first_ts = None
    last_ts = None
    acc = {"total_tokens": 0, "input_tokens": 0, "output_tokens": 0, "cache_read": 0}
    per_call = []
    models = set()
    ctx_components = {}

    with args.session.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(rec, dict):
                continue
            n_records += 1
            message = rec.get("message")
            if not isinstance(message, dict):
                continue
            role = str(message.get("role") or "").lower()
            ts = message.get("timestamp")
            if isinstance(ts, (int, float)):
                first_ts = ts if first_ts is None else min(first_ts, ts)
                last_ts = ts if last_ts is None else max(last_ts, ts)
            if role != "assistant":
                continue
            n_assistant += 1
            model = message.get("model")
            if isinstance(model, str) and model.strip():
                models.add(model.strip())
            usage = message.get("usage")
            if isinstance(usage, dict):
                acc["total_tokens"] += int(usage.get("totalTokens") or 0)
                acc["input_tokens"] += int(usage.get("input") or 0)
                acc["output_tokens"] += int(usage.get("output") or 0)
                acc["cache_read"] += int(usage.get("cacheRead") or 0)
                per_call.append(int(usage.get("totalTokens") or 0))
            cu = message.get("context_usage")
            if isinstance(cu, dict):
                comps = cu.get("components")
                if isinstance(comps, dict):
                    for k, v in comps.items():
                        if isinstance(v, dict):
                            t = v.get("tokens")
                            if isinstance(t, int):
                                ctx_components[k] = ctx_components.get(k, 0) + t

    out = {
        "label": args.label,
        "session_file": str(args.session),
        "records": n_records,
        "assistant_messages": n_assistant,
        "model": sorted(models)[0] if models else None,
        "wall_clock_seconds": round((last_ts - first_ts) / 1000, 1) if first_ts and last_ts else None,
        "usage": {
            "total_tokens": acc["total_tokens"],
            "input_tokens": acc["input_tokens"],
            "output_tokens": acc["output_tokens"],
            "cache_read": acc["cache_read"],
        },
        "context_components": ctx_components,
        "per_call_total_tokens": per_call,
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "per_call_total_tokens"},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
