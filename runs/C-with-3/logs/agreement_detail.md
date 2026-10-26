# 数值核对明细（案例 C）

- 核对工具：Skill 自带 `scripts/check_agreement.py`（逐字复制，未改）
- 容差：0.01（相对误差）
- 检查结论：39 条结论，0 项标记，all_passed=True
- 处置原则：**超容差项必须修正、降级、或写进报告的遗留节**；本表列出每个被引用数值的转写来源与处置。

| claim | numeric_value | 转写来源（同一引文内命中） | 相对误差 | 处置 |
|---|---|---|---|---|
| C02 | 0.256525 | `claims.csv` 该行 quote | 0（引文内字面命中） | 一致，保留为 paper-fact |
| C03 | 3 | `claims.csv` 该行 quote | 0（引文内字面命中） | 一致，保留为 paper-fact |
| C04 | 24 | `claims.csv` 该行 quote | 0（引文内字面命中） | 一致，保留为 paper-fact |
| C05 | 48 | `claims.csv` 该行 quote | 0（引文内字面命中） | 一致，保留为 paper-fact |
| C06 | 43000 | `claims.csv` 该行 quote | 0（引文内字面命中） | 一致，保留为 paper-fact |
| C07 | 8 | `claims.csv` 该行 quote | 0（引文内字面命中） | 一致，保留为 paper-fact |
| C08 | 1.5 | `claims.csv` 该行 quote | 0（引文内字面命中） | 一致，保留为 paper-fact |
| C09 | 8 | `claims.csv` 该行 quote | 0（引文内字面命中） | 一致，保留为 paper-fact |
| C10 | 8 | `claims.csv` 该行 quote | 0（引文内字面命中） | 一致，保留为 paper-fact |
| C11 | 80 | `claims.csv` 该行 quote | 0（引文内字面命中） | 一致，保留为 paper-fact |
| C12 | 32 | `claims.csv` 该行 quote | 0（引文内字面命中） | 一致，保留为 paper-fact |
| C13 | 26 | `claims.csv` 该行 quote | 0（引文内字面命中） | 一致，保留为 paper-fact |
| C14 | 24 | `claims.csv` 该行 quote | 0（引文内字面命中） | 一致，保留为 paper-fact |
| C15 | 4e19 | `claims.csv` 该行 quote | 0（引文内字面命中） | 一致，保留为 paper-fact |
| C16 | 12 | `claims.csv` 该行 quote | 0（引文内字面命中） | 一致，保留为 paper-fact |
| C18 | 80 | `claims.csv` 该行 quote | 0（引文内字面命中） | 一致，保留为 paper-fact |
| C19 | 32 | `claims.csv` 该行 quote | 0（引文内字面命中） | 一致，保留为 paper-fact |
| C20 | 16 | `claims.csv` 该行 quote | 0（引文内字面命中） | 一致，保留为 paper-fact |
| C24 | 1.5 | `claims.csv` 该行 quote | 0（引文内字面命中） | 一致，保留为 paper-fact |
| C25 | 0.2565 | `claims.csv` 该行 quote | 0.0000 %（与正文 None 交叉核对） | 一致（表格取整），保留；该行另有"表格整体受损、未做上游核验"的标注 |
| C26 | 3.04 | `claims.csv` 该行 quote | 0（引文内字面命中） | 一致，保留为 paper-fact |
| C27 | 1.65 | `claims.csv` 该行 quote | 0（引文内字面命中） | 一致，保留为 paper-fact |

## 未参与数值核对的条目（按设计）

| 条目 | 处理 | 原因 |
|---|---|---|
| # 4 行 time 单元格（被截断） | `numeric_value` 留空，分类 `undetermined`（C33） | 受损值不可确定；不给点估计也不给区间 |
| 缺失列（原表 8 列中的第 8 列） | 分类 `undetermined`（C34） | 该列在本文件中无法复原，不重建 |
| 全部 `inference` 行 | `numeric_value` 留空 | 推断值不得混进「原文数值」通道 |

## 派生数字（仅出现在报告正文，非原文数值）

| 派生量 | 算式 | 口径 |
|---|---|---|
| $96 | 8 卡 × 4 h × $3/GPU·h | 材料自身单价下的最坏情况估计（材料未给 A100 报价） |
| 0.0098 % | \|0.2565 − 0.256525\| / 0.256525 | 表格 CORE 与正文 CORE 的跨来源核对 |

