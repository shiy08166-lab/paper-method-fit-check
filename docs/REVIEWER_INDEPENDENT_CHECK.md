# 供评审方独立复核的入口（案例 C）

本文所有断言都能在本包内逐条核对，不需要额外下载任何东西。

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

## 三、想自己跑一遍校验？

```powershell
python scripts/check_agreement.py `
  --claims runs/C-with-3/claims.csv `
  --preconditions runs/C-with-3/preconditions.csv `
  --source paper_materials/nanochat_README_table_corrupted.md `
  --tolerance 0.01 --report ./agreement_recheck.json
```

**注意两个参数**：`--source` 指向包内的损坏件 `paper_materials/nanochat_README_table_corrupted.md`
（该次运行时它的工作副本名为 `materials/source.txt`，与前者**逐字节相同**，SHA-256 同为 `64a46d32…`）；
`--report` **必填**，漏掉会得到 argparse 的 `exit 2`。

退出码 0 = 全部通过（预期 `检查 39 条结论，标记 0 项`）。**反向对照**：故意把一条引文里的关键串改掉，
应当退出码 1 —— 证明校验不是空转。完整的三条命令与判据见 `docs/REPRODUCE.md`。

## 四、想核对「我读过什么」？

`trace.md`（两次运行的逐条会话文本，附宿主原生记录来源 SHA-256）、
`runs/C-with-3/logs/run_log.md`（运行留痕：失败与重试、2 次环境策略拦截、1 项刻意不做的动作）。

## 五、已经做了什么 / 没做什么 / 不能做什么

- **已做**：两次完整运行（第二次为严格对称复测）、官方 checker 0 标记、验收自检全过、
  非表格段落 211 行逐行比对上游快照、受损表格的整表不作出处处理。
- **刻意没做**：**从未读取、打印或落盘上游快照的 leaderboard 表格的任何单元格** —— 所以受损值不可能是抄回来的。
- **不能做**：A100 相对 H100 的倍率、下载体积与耗时、榜单 `time` 列计时口径——材料里没有，
  只能由读者在自己的云卡上标定（见 README §3.3 的"去哪找"）。
