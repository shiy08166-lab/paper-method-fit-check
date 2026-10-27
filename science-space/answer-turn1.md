环境准备已按要求装配完毕，`materials/source.txt` 的 SHA-256 = `64a46d328926d45842d9e8ad0a1817b01d176ad915e55ba92609119ca571917c`、17623 字节，与期望一致，材料未被改动，全程按只读处理。

## 交付物（工作目录 `/bohr-workspace`）

| 文件 | 内容 |
|---|---|
| [preconditions.csv](preconditions.csv) | 14 条，四类齐全（compute 4 / data scale 2 / hyperparameters 4 / hidden assumptions 4），其中 3 条 `confidence=absent`（PC-04、PC-06、PC-13） |
| [claims.csv](claims.csv) | 22 条：`paper-fact` 12 / `inference` 5 / `undetermined` 5；额外带 `reasoning` 列 |
| [evidence_index.json](evidence_index.json) | 12 条逐字引文，每条带材料 SHA-256 |
| [verdict.md](verdict.md) | 四段 + 第 5 节「异常处理对照」+ 第 6 节失败与重试 |
| [logs/agreement.json](logs/agreement.json) | 脚本输出（0 项标记、`all_passed: true`）+ 追加的 `dispositions` |

## 结论词

`transferable-with-changes`：机制（`--depth` 单旋钮派生全部超参、8 卡参考配置、80GB 显存前提、A100 默认 bf16）在 8×A100 上成立且作者明说 A100 可跑；变的是时间——4 小时预算能否闭合取决于 A100 相对 H100 的墙钟倍率，材料只给「a bit slower」，无数字。

## 实测与声明的差异（按硬要求 3 以实测为准）

- **第 1 点半成立**：行序确实被打乱（`#` 序列 6,1,4,0,3,2,5），但 `#` 与 `time` 严格单调，编号并未指向别人的数据。
- **第 2 点说反了**：表头 7 格、数据行 7 格（L39 例外 9 格）二者一致；真正的列数冲突在**分隔行 8 组** vs 表头 7 格。「数据行仍按 8 列填写」不成立。
- **第 3 点仅按 `#` 值读成立**：截断在 `#`=4 的行（L35），但它是第 3 个数据行、文件第 35 行；第 4 个数据行是 #0（`168 hours`，完整）。
- **第 4 点不成立**：多分隔符的是第 7 个数据行 `#`=5（L39），且多出 2 个单元格（`broken`、`extra`），不是「多了一个分隔符」。

## 数值自检与失败留痕

`check_agreement.py` 共跑 3 次：第 1 次退出码 1（`numeric_mismatch` CF-01、`numeric_on_non_fact` IN-01），第 2 次仍剩 1 项（`3.2` 写在公共行、清空未生效），第 3 次退出码 0、`检查 22 条结论，标记 0 项`。第一版草稿与其报告未删除，留在 `logs/claims_v1_draft.csv`、`logs/agreement_v1.json`。另外该脚本查不出「引文在原文出现多次」，第一版 `"$48"` 就是这样混过去的，因此另加了一道「命中恰好 1 次」的自检（`logs/quote_check_v2.json`）。

## 完成时摘要

三分类 12/5/5，降级 8 处（5 条结论→`undetermined`，3 条前置条件→`absent`），5 条预期行为 5/5 做到，实际耗时约 5 分钟。最不确定的一点：A100 相对 H100 的墙钟倍率——IN-01 的 3–3.6 小时完全建立在「A100≈H100 的 50% 吞吐」这一材料未给出的假设上，倍率到 2.4 倍即超预算。

未跑训练、未下载数据集、未联网（除上一轮已获授权的探针与本轮装配命令）。