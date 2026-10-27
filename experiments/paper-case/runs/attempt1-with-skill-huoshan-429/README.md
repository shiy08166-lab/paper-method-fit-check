# attempt1-with-skill-huoshan-429 —— 被上游限流掐断的第一次有 Skill 运行（失败留痕，**不删**）

> 这个目录是本案例的**失败尝试**，按纪律完整保留，不删行、不改写。
> 它**不是**对照实验的一部分（对照用的是 `runs/with-skill/` 与 `runs/without-skill/`）。

## 它是什么

第一次「有 Skill」运行，模型路由 `ccs-huoshan/deepseek-v4-pro-ga-260813`，
工作区与最终 `runs/with-skill/` 的装配方式完全一致（同一份冻结任务书、同一份材料字节）。

## 发生了什么

- 会话跑了 **1104 秒（18.4 分钟）**，产出了 5 个交付物
  （`claims.csv` 27 条 / `preconditions.csv` 25 条 / `evidence_index.json` / `verdict.md`），
  外加会话自己写的产出脚本 `_build_deliverables.py`；
- **在会话自己跑官方 checker 之前**，上游返回
  `exceeded retry limit, last status: 429 Too Many Requests`，会话 `turn.failed`，
  codex 进程退出码 1；
- 因此 `logs/agreement.json` **当时不存在**，也没有最终总结消息；
- 之后该路由**持续 429**（连一句「Reply with exactly: OK」都跑不了），
  另外两条路由 `ccs-huoshan/deepseek-v4-1-flash-260910` 同样 429，
  `ccs-minimax/MiniMax-M3.1-Flash` 报「high demand」。

## 作者的处置

1. 按 Skill 第 7 步「不许写一个没跑过的检查的通过结论」，
   作者用**逐字相同的命令**在**同一工作目录、同一份交付物**上补跑了官方脚本：
   **退出码 0，27 条结论，标记 0 项**。stdout 见 `logs/check_agreement_stdout.txt`，
   报告见 `logs/agreement.json`。**没有改动任何一行 claims.csv / preconditions.csv。**
2. 会话的失败痕迹全部保留：`logs/run_log.md`（含会话自述与作者追加的处置）、
   `logs/codex_events_raw.jsonl`（115 条事件）、`logs/codex_stderr.txt`、
   `logs/turn_failed.json`（限流错误的原始记录）、`_build_deliverables.py`。
3. **自述与产物不一致**这件事也如实记了：会话的 `logs/run_log.md` 自称
   「成功完成……5. 运行 scripts/check_agreement.py 数值一致性自检」，
   但会话结束时的文件树里**并没有** `logs/agreement.json`。
   这正是 Skill 第 8 步那句「不许写一个没跑过的检查的通过结论」要防的东西——
   **而它是被上游限流，不是被方法本身挡住的。**

## 为什么最终的两轮对照没有用它

对照实验要求**两轮同模型、同环境、唯一变量是有没有 SKILL.md**。
第一次运行之后，`ccs-huoshan/*` 路由的配额耗尽，无法在**同一模型**上跑出对照轮。
因此最终的两轮都换到可用的路由 `ccs-deepseek/deepseek-v4-pro` **重跑**，
并在 `comparison.md` 里如实写明：

- 最终对照用的模型是 `ccs-deepseek/deepseek-v4-pro`；
- 本目录是**第一次尝试**（模型 `ccs-huoshan/deepseek-v4-pro-ga-260813`），
  **不参与对照统计**；
- 但它**独立复现**了本次案例的一条重要结论：即使换成另一个模型路由、
  按 Skill 的 8 步工作流走，**报告仍然没有发现论文自身的「25% vs 32.6%」口径不一致**，
  而且报告还写下了一个**无法被任何机械检查验证的否定性断言**
  （「核对时未发现论文摘要与正文、正文与脚注互相矛盾的数字」）。
