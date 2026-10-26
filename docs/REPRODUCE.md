# 复跑指南 · 三条命令，三十秒

> 只依赖 **Python 3 标准库**；不联网、不需要 GPU、不需要 API Key、不需要任何付费服务。
> 本文所有「预期输出」都是在本包内**实跑**得到的，不是设计意图。

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
  --preconditions runs/C-with-1/preconditions.csv \
  --source paper_materials/nanochat_README_table_corrupted.md \
  --tolerance 0.01 --report ./agreement_recheck-c1.json
```

**预期输出**：`检查 62 条结论，标记 0 项`，**退出码 0**。

## ③ 反向对照：证明这个校验不是空转

把 `runs/C-with-3/claims.csv` 里任意一条 `paper-fact` 的 `quote` 改动**一个字符**，重跑 ①：
**必须**看到 `[quote_not_contiguous]` 标记，且**退出码变为 1**。

## ④ 逐值核对：数值口径是逐条算的

`runs/C-with-3/logs/agreement_detail.md` —— 39 条结论的逐值相对误差核对表与每条处置。

## 冻结哈希与产物哈希

| 文件 | 字节 | SHA-256 |
|---|---:|---|
| `cases/task-C.md`（**运行前冻结**） | 4184 | `e364bf2a641b4899b3c6b483a1d0cee11333fa12901ba8e43140a47988245ae8` |
| `cases/acceptance-C.md`（**运行前冻结**） | 3150 | `21e6081520e21f357c6e9bc4a30b06067129b7c97f2a3c70868854632d24d4b1` |
| `paper-method-fit-check/SKILL.md`（= `skill_version`） | 13080 | `0d048c99959f59b3de51204cac23593f952588359e2c85bf7f759bfbe9a60ade` |
| `paper_materials/nanochat_README_table_corrupted.md`（损坏件） | 17623 | `64a46d328926d45842d9e8ad0a1817b01d176ad915e55ba92609119ca571917c` |
| `runs/C-with-3/claims.csv` | 13759 | `a0ff5ad7959abe2f8186aa9feec4523272be6b1c702ba317a28351e54779a59b` |
| `runs/C-with-3/preconditions.csv` | 6795 | `e2ed4c7991b7e4e0c02cb82d096f3aba4e11c91dad4b2ee66080d59da3561ed9` |
| `runs/C-with-3/evidence_index.json` | 9774 | `bf32ff43e4cbec14bd0532ebe66c49ddb1065c4c67a37dc3d22b4ae7ec8f269b` |
| `runs/C-with-3/verdict.md` | 18602 | `75878ff42135dcd3941ddff63a5e8035b34ac241744ec7818a7aa910c734d82e` |
| `runs/C-with-3/logs/verification.json`（15 项验收） | 3830 | `0858d5298834cdb5e07e2f5a60cf04f64642e93e7526654d0392f05fa1bd3243` |
| `runs/C-with-3/logs/agreement_detail.md`（逐值核对） | 3716 | `90abcc1ff69c7d7b8ec5a8f8904d9958b7c19045df3eb36addf4e1f406f46510` |

## 本包收录了什么 / 没收录什么

本包是公开仓库的**精选子集**（赛题允许「无需打包整个仓库」），但**核验本次结论所需的一切都在包内**：
损坏件、两次运行的结论/前置条件/引文索引/结论文档、官方 checker、验收自检（15 项全 PASS）、
逐值核对表、运行留痕、冻结的任务书与验收标准、Skill 本体。

**未随包**（均在公开仓库里，**核验不需要**）：`runs/C-with-3/manifest.json`（运行当时的完整逐文件哈希记录）、
`runs/C-with-3/scripts/`（作者的生成脚本）、`scripts/export_session_text.py` 与
`scripts/extract_usage_v2.py`（会话轨迹与 token 用量提取工具）、上游 nanochat 自身的文件（见正文 §3.3）。

**如实披露**：运行当时记录的 `manifest.json` 记 `logs/verify_stdout.txt` 为 1,590 B、
`logs/check_agreement_stdout.txt` 为 190 B；这两个 stdout 在整理时以**不同的 `--report` 路径**重新捕获，
故当前字节（1,118 B / 112 B）与当时记录不同。**其余 21 项与运行当时记录的哈希逐字节一致。**
