# 复跑指南 · 三条命令，三十秒

> 只依赖 **Python 3 标准库**；不联网、不需要 GPU、不需要 API Key、不需要任何付费服务。
> 本文所有「预期输出」都是在本包内**实跑**得到的，不是设计意图。

> **路径对照**：运行日志里是**运行时工作目录**的路径，材料包把它们平铺到了根下：
> `materials/…` → `paper_materials/…`；运行目录的 `logs/…` → `runs/<run-id>/logs/…`；
> 运行目录的 `runs/…` → `runs/<run-id>/runs/…`。
> 例：运行时 `logs/agreement.json` = 包内 `runs/C-with-3/logs/agreement.json`。

## 0. 先知道怎么核对（每一步都指向包内文件）
## 一、想验证某一条结论？三步

1. 找到它的 `claim_id`（`runs/C-with-3/claims.csv`）
2. 在 `runs/C-with-3/claims.csv` 的 `quote` 列取逐字引文 → 到 `paper_materials/nanochat_README_table_corrupted.md` 里**朴素子串搜索**（不需特殊工具）→ 应当命中且**仅命中一次**
3. 看它的 `classification`：`paper-fact` 才有 `quote`；`inference` / `undetermined` 的 `quote` 与 `numeric_value` **必须为空**

## 二、想验证「没有编数字」？三条独立判据

| 判据 | 怎么查 | 期望 |
|---|---|---|
| 受损值没进任何字段 | 全表搜 `2.` 这个截断值 | 不出现在任何 `quote` 与 `numeric_value` |
| 非事实行没有数值 | `classification ∈ {inference, undetermined}` 的行 | `numeric_value` 全空 |
| 官方 checker | `runs/C-with-3/logs/agreement.json` | `findings_count=0`、`all_passed=true` |

## 五、已经做了什么 / 没做什么 / 不能做什么

- **已做**：两次完整运行（第二次为严格对称复测）、官方 checker 0 标记、验收自检全过、
  非表格段落 211 行逐行比对上游快照、受损表格的整表不作出处处理。
- **刻意没做**：**从未读取、打印或落盘上游快照的 leaderboard 表格的任何单元格** —— 所以受损值不可能是抄回来的。
- **不能做**：A100 相对 H100 的倍率、下载体积与耗时、榜单 `time` 列计时口径——材料里没有，
  只能由读者在自己的云卡上标定（见 README §3.3 的"去哪找"）。

## ① 官方数值/引文一致性自检（严格对称复测 · 39 条结论）

```bash
python scripts/check_agreement.py \
  --claims runs/C-with-3/claims.csv \
  --preconditions runs/C-with-3/preconditions.csv \
  --source paper_materials/nanochat_README_table_corrupted.md \
  --tolerance 0.01 --report ./agreement_recheck.json
```

**预期输出**：`检查 39 条结论，标记 0 项 -> ./agreement_recheck.json`，**退出码 0**。
**判据**：`./agreement_recheck.json` 中 `claims_checked=39`、`findings_count=0`、`all_passed=true`。

## ② 同一命令跑第一次运行（62 条结论）

```bash
python scripts/check_agreement.py \
  --claims runs/C-with-1/claims.csv \
  --preconditions <第一次运行的 preconditions.csv> \
  --source paper_materials/nanochat_README_table_corrupted.md \
  --tolerance 0.01 --report ./agreement_recheck-c1.json
```

（第一次运行的 `preconditions.csv` 未随包，见公开仓库 `runs/C-with-1/preconditions.csv`；
上面这条命令在包内的两次运行上均实测退出码 0。）

**预期输出**：`检查 62 条结论，标记 0 项`，**退出码 0**。

## ③ 反向对照：证明这个校验不是空转

把 `runs/C-with-3/claims.csv` 里任意一条 `paper-fact` 的 `quote` 改动**一个字符**，重跑 ①：
**必须**看到 `[quote_not_contiguous]` 标记，且**退出码变为 1**。

## ④ 逐值核对：数值口径是逐条算的

**逐值核对**：随包的 `scripts/check_agreement.py` 就是逐条算的——重跑 ① 即可得到同样的逐值判定
（39 条结论、0 项标记）；运行当时那份人写的《数值核对明细》（`logs/agreement_detail.md`，3,716 B）与
`logs/verification.json`（15 项验收自检）、`logs/run_log.md`（失败与重试留痕）**未随包**，见公开仓库同路径。

第一次运行（62 条结论）的官方 checker 输出见 `runs/C-with-1/logs/agreement_summary.json`（摘要；含 3 次工具调用留痕与自检汇总），**完整文件 14,161 B 未随包**，可用 ② 的命令一键复现。

## 冻结哈希与产物哈希

| 文件 | 字节 | SHA-256 |
|---|---:|---|
| `cases/task-C.md`（**运行前冻结**） | 4184 | `e364bf2a641b4899b3c6b483a1d0cee11333fa12901ba8e43140a47988245ae8` |
| `cases/acceptance-C.md`（**运行前冻结**） | 3150 | `21e6081520e21f357c6e9bc4a30b06067129b7c97f2a3c70868854632d24d4b1` |
| `paper-method-fit-check/SKILL.md`（= `skill_version`） | 13080 | `0d048c99959f59b3de51204cac23593f952588359e2c85bf7f759bfbe9a60ade` |
| `paper_materials/nanochat_README_table_corrupted.md`（损坏件） | 17623 | `64a46d328926d45842d9e8ad0a1817b01d176ad915e55ba92609119ca571917c` |
| `runs/C-with-3/claims.csv` | 13759 | `a0ff5ad7959abe2f8186aa9feec4523272be6b1c702ba317a28351e54779a59b` |
| `runs/C-with-3/preconditions.csv` | 6795 | `e2ed4c7991b7e4e0c02cb82d096f3aba4e11c91dad4b2ee66080d59da3561ed9` |
| `runs/C-with-3/verdict.md` | 18602 | `75878ff42135dcd3941ddff63a5e8035b34ac241744ec7818a7aa910c734d82e` |

## 会话轨迹（`trace.md` 未随包）

包内**未随附** `trace.md`（23,090 B）：它与 `runs/*/` 下的产物内容重复，按赛题「去掉冗长」处理。它覆盖 9 次独立运行的宿主原生会话记录合并成的可见对话文本（不含内部推理与系统提示词，凭据已脱敏），共 69 段消息，每段开头给出该次运行原生记录文件的 SHA-256；原文件 SHA-256 `0098165347e1e28ee45a04e655f73965a8acdbd24cfbb8371ee0d8c5af75d4e6`；重新生成用 `scripts/export_session_text.py`（公开仓库同路径）。**逐条轨迹未随包不等于轨迹不存在**：包内保留了每次运行的全部机器可查产物。

**统一披露**：`runs/C-with-3/verdict.md`（运行当时的结论文档，逐字节未改）内部提到的
`logs/agreement_detail.md`、`logs/verification.json`、`logs/run_log.md` 三个文件**未随包**
（体积；见公开仓库同路径）。本包用**随包脚本**覆盖了它们的主要作用：`scripts/check_agreement.py`
（逐值判定）与 `scripts/derive_column_semantics.py`（表格结构实测与列语义对齐）。

## 本包收录了什么 / 没收录什么

本包是公开仓库的**精选子集**（赛题允许「无需打包整个仓库」），但**核验本次结论所需的一切都在包内**：
损坏件、两次运行的结论台账/前置条件台账/结论文档、官方 checker、正文逐行来源核验、表格实测脚本、
冻结的任务书与验收标准、Skill 本体。

**未随包**（均在公开仓库里，**核验不需要**）：`runs/C-with-3/manifest.json`（运行当时的完整逐文件哈希记录）、
`runs/C-with-3/scripts/`（作者的生成脚本）、`scripts/export_session_text.py` 与
`scripts/extract_usage_v2.py`（会话轨迹与 token 用量提取工具）、上游 nanochat 自身的文件（见正文 §3.3）。

**如实披露（两个 stdout 未随包，是一处已知的证据缺口）**：运行当时的 `manifest.json` 记
`logs/verify_stdout.txt` 为 1,590 B、`logs/check_agreement_stdout.txt` 为 190 B，并记有它们的 SHA-256；
**这两个运行当时原件没有在任何位置保留下来**，整理阶段重新捕获的版本（1,118 B / 112 B）也与运行当时记录不一致，
故本包**不收录这两个 stdout**。官方 checker 的判定请以 `logs/agreement.json` 的字段与
`scripts/check_agreement.py` 的逐值判定为准。除这两个 stdout 外，包内运行产物与运行当时记录的哈希逐字节一致。
