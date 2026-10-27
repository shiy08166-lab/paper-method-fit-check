# 运行日志（失败与重试）

## 环境自检

- 命令：`python -c "import hashlib,pathlib; ..."`（只读）。
- 结果：`materials/source.txt` 的 SHA-256 = `a8f387d278213370e3b7705539545292188a7c44ba185875f83c373a36b5984d`，82806 字节，与任务要求一致。未改动材料。

## 失败 / 重试记录

1. 步骤：首次读取 `cases/task-paper.md` 与 `materials/source_manifest.json`。
   现象：PowerShell 默认编码把 UTF-8 文件按 GBK 解码，中文变成乱码（例如「案例」显示为「妗堜緥」）。
   重试 1 次：改用 `Get-Content -Raw -Encoding UTF8` 重新读取，内容恢复正常。
   影响：仅影响阅读，不改任何材料。

2. 步骤：交付物生成。
   做法：先写 `scripts/build_deliverables.py`，让它在写文件前把 16 条 paper-fact 引文逐条做 `quote in source_text` 子串校验。
   结果：16/16 一次通过（无需重试、无需人工修正）。若未来重新生成，引文与材料不一致会在写盘前直接报错退出。

3. 步骤：数值一致性自检。
   命令：`python scripts/check_agreement.py --claims claims.csv --preconditions preconditions.csv --source materials/source.txt --tolerance 0.01 --report logs/agreement.json`
   结果：退出码 0，24 条结论、0 条标记，`all_passed=true`。无失败、无降级式二次处理。

## 备注

- 控制台打印中文时出现一次编码乱码（GBK 控制台），但不影响 `logs/agreement.json` 的 UTF-8 内容，已用 UTF-8 重读确认。


---

## 作者侧处置（会话结束后补记；agent 自己写的内容以上未改动）

**会话结束时的状态**：会话自己已经跑过一次官方 checker（`logs/agreement.json` 存在）；作者又用同一命令复跑了一遍以留下可核对的 stdout。

作者的处置（按 Skill 第 7 步「不许写一个没跑过的检查的通过结论」）：
1. 作者用**逐字相同**的命令在**同一工作目录、同一份交付物**上补跑了官方脚本：

   ```bash
   python scripts/check_agreement.py --claims claims.csv --preconditions preconditions.csv \
       --source materials/source.txt --tolerance 0.01 --report logs/agreement.json
   ```

   结果：**退出码 0，24 条结论，标记 0 项**
   （stdout 见 `logs/check_agreement_stdout.txt`，报告见 `logs/agreement.json`）。
   **没有改动任何一行 claims.csv / preconditions.csv。**
2. 因此本轮满足「官方 checker 退出码 0」这一条，但**它是不是会话自己跑的那一次**，
   如实标注在 `comparison.md` 与 `ledger.md` 里。
3. 会话的失败痕迹**全部保留**：本文件、`logs/codex_events_raw.jsonl`、
   `logs/codex_stderr*.txt`、`logs/session_summary.json`，
   以及会话自己写的产出脚本（如有）。
