#!/usr/bin/env python3
"""把 MiniMax Code 的原生会话记录导出成「按时间顺序的可见对话」UTF-8 文本。

为什么需要它
------------
Playground CLI 的 `trace validate` 无法解析 MiniMax Code 的 `messages.jsonl`
（实测：jsonl_events=486, usable_events=0, valid=false）。按 RECORDS.md，
"平台 CLI 能否解析以本地打包结果为准；不能解析时保留原文件，并使用文本导出方式"，
所以这里把原生记录转成可核验的文本导出，配合 `submit.py --trace-kind export` 提交。

原则
----
1. 只导出**可见内容**：用户输入 + 助手消息 + 工具调用/结果的用户可见摘要。
2. **不导出** 内部推理、系统提示词、凭据、环境变量值。
3. 逐条标注来源行号与原始 message_id，便于评审核对原文。
4. 不做任何改写、润色或补写；原文是什么样就是什么样。
5. 产出文件带来源 SHA-256，提交脚本会把该哈希写进 evidence/provenance.json。

用法
----
    python3 scripts/export_session_text.py \
        --session "E:/.../v2/sessions/2026/10/23/04-00-59-111-session_xxx/messages.jsonl" \
        --out runs/A-with/session-export.txt
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

# 这些系统注入的提醒段不属于「用户自己写的话」，导出时跳过，避免污染对照。
INJECTED_PREFIXES = (
    "<system-reminder>",
    "<proactive-memory>",
    "<memory-skill-reminder>",
    "<media-output-reminder>",
    "<async-audit>",
    "<mcode-tools-master-reminder>",
    "<in-app-browser-context",
    "<agent-context>",
)

SECRET_PATTERNS = [
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "[REDACTED_KEY]"),
    (re.compile(r"\bark-[A-Za-z0-9-]{20,}\b"), "[REDACTED_KEY]"),
    (re.compile(r"\btrp_[A-Za-z0-9]{20,}\b"), "[REDACTED_KEY]"),
    (re.compile(r"\btsp_[A-Za-z0-9]{20,}\b"), "[REDACTED_KEY]"),
    (re.compile(r"(?i)(authorization:\s*bearer\s+)[A-Za-z0-9._-]{16,}"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(api[_-]?key\s*[=:]\s*)\S{12,}"), r"\1[REDACTED]"),
]


def redact(text: str) -> str:
    for pattern, replacement in SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def is_injected(text: str) -> bool:
    stripped = text.lstrip()
    return any(stripped.startswith(prefix) for prefix in INJECTED_PREFIXES)


def text_of(content) -> str:
    """把 message.content 里的 text 段拼起来；非文本段只留一个类型标记。"""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    chunks = []
    for part in content:
        if not isinstance(part, dict):
            continue
        kind = part.get("type")
        if kind == "text" and part.get("text"):
            chunks.append(part["text"])
        elif kind == "thinking":
            # 内部推理不导出为正文；只标注存在，避免看起来像漏内容。
            chunks.append("[internal reasoning omitted]")
        elif kind == "tool_use" or kind == "tool_call":
            name = part.get("name") or part.get("toolName") or "tool"
            chunks.append(f"[tool call: {name}]")
        elif kind == "tool_result" or kind == "toolResult":
            chunks.append("[tool result]")
        elif kind == "image":
            chunks.append("[image attachment]")
    return "\n".join(chunks)


def iter_messages(path: Path):
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for lineno, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(record, dict):
                continue
            message = record.get("message")
            if not isinstance(message, dict):
                continue
            yield lineno, record, message


def main() -> int:
    parser = argparse.ArgumentParser(description="MiniMax Code 会话记录 -> 可见对话文本导出")
    parser.add_argument("--session", required=True, type=Path,
                        help="MiniMax Code 的 messages.jsonl 路径")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--model-label", default="MiniMax-M3.1-Flash",
                        help="模型显示名称；无法取得时如实写'无法取得'")
    parser.add_argument("--harness-label", default="MiniMax Code",
                        help="宿主软件名称")
    args = parser.parse_args()

    if not args.session.exists():
        print(f"找不到会话文件: {args.session}", file=sys.stderr)
        return 2

    raw = args.session.read_bytes()
    source_sha = hashlib.sha256(raw).hexdigest()

    lines: list[str] = []
    lines.append("# 会话可见内容导出 (export)")
    lines.append("")
    lines.append(f"- 来源文件: {args.session.name}")
    lines.append(f"- 来源 SHA-256: {source_sha}")
    lines.append(f"- 宿主软件: {args.harness_label}")
    lines.append(f"- 模型显示名称: {args.model_label}")
    lines.append("- 导出方式: 从宿主原生会话记录按时间顺序抽取用户输入与助手可见输出；")
    lines.append("  未改写、未补写、未包含内部推理与系统提示词。")
    lines.append("")

    kept = 0
    skipped = 0
    for lineno, record, message in iter_messages(args.session):
        role = str(message.get("role") or "").lower()
        body = text_of(message.get("content"))
        if not body.strip():
            continue
        if role == "user" and is_injected(body):
            skipped += 1
            continue
        if role not in {"user", "assistant"}:
            continue

        body = redact(body).strip()
        if not body:
            continue

        label = "用户" if role == "user" else "助手"
        message_id = record.get("message_id") or message.get("message_id") or "-"
        lines.append(f"## [{label}] 行 {lineno} · {message_id}")
        lines.append("")
        lines.append(body)
        lines.append("")
        kept += 1

    lines.append("---")
    lines.append(f"共导出 {kept} 条可见消息；跳过 {skipped} 条系统注入的提醒段。")
    lines.append("")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({
        "status": "exported",
        "out": str(args.out),
        "messages_exported": kept,
        "system_reminders_skipped": skipped,
        "source_file": str(args.session),
        "source_sha256": source_sha,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
