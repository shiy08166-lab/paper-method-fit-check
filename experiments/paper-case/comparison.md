# 有 / 无 Skill：同一篇真实论文上的同条件对照

> 唯一变量 = 给不给 `SKILL.md`。同一篇论文、同一份冻结任务书、同一套交付物契约、
> 同一套材料字节、**同一模型**（`ccs-deepseek/deepseek-v4-pro`）、同一套自检脚本；
> 工作区逐文件哈希相同（`runs/workspace_diff.json`、`runs/workspace_parity.json`）。

第三列是**归档的第一次有 Skill 运行**（`runs/attempt1-with-skill-huoshan-429/`）：
它跑在另一条模型路由上（`ccs-huoshan/deepseek-v4-pro-ga-260813`），18.4 分钟后被上游
`429 Too Many Requests` 掐断，**不计入对照统计**；它在这里的作用是证明
**同一条件下结果并不稳定**。

## 1. 关键数字对照

| 项 | 有 Skill | 无 Skill（对照） | 归档的第一次有 Skill 运行 |
|---|---|---|---|
| 结论条数 | 33 | 24 | 27 |
| 三分类 paper-fact / inference / undetermined | 23 / 5 / 5 | 16 / 4 / 4 | 19 / 4 / 4 |
| 前置条件条数 / 其中 absent | 21 / 3 | 7 / 3 | 25 / 2 |
| 前置条件是否按任务书要求的**四类**组织 | 是 | 否 | 是 |
| 实际用到的 category 取值 | compute、data scale、hidden assumptions、hyperparameters | compute、data、model、objective、paper-evidence | compute、data scale、hidden assumptions、hyperparameters |
| confidence 取值是否在 {stated, inferred, absent} 内 | 是 | 否（absent、high） | 是 |
| paper-fact 带齐 locator+quote | 23 / 23 | 16 / 16 | 19 / 19 |
| 官方 checker（作者复跑） | exit=0，标记 0 | exit=0，标记 0 | exit=0，标记 0 |
| 会话耗时 | 22.6 分钟 | 18.2 分钟 | 18.4 分钟 |
| 会话事件数 | 61 | 91 | 87 |

## 2. 行为探针（正则判定，不手写）

| 行为探针 | 有 Skill | 无 Skill | 归档第一次 |
|---|---|---|---|
| 引到脚注 5 的 32.5 / 43.1（tokens/s） | 是 | 是 | 是 |
| 算出/写出 32.6（吞吐提升的真实值） | 是 | 是 | 否 |
| **指出**了论文自身的口径不一致（非否定性断言） | 是 | 是 | 否 |
| 写下「未发现……不一致」这种否定性断言 | 否 | 否 | 是 |
| 把表格数字**降级**成 undetermined（claims.csv 判定） | 是 | 是 | 否 |
| 明说「不按出现顺序猜」 | 是 | 是 | 否 |

## 3. 诚实的结论（含负面结果）

1. **在这篇论文上，Skill 唯一被测到的、可复现的差别是「契约遵守」，不是「结论质量」。**
   两轮的结论词相同（`transferable-with-changes`）、官方 checker 都是 0 标记退出码 0、
   **都自己发现了论文第 5 页的「25% speedup vs 脚注 32.5→43.1 tokens/s（+32.6%）」口径不一致**，
   也都做了 7B/24GB 的换算且算式可复算（作者侧已逐条重算，见 `ledger.md` 的 P-19/P-20/P-21）。
   差别在台账：**前置条件 21 条 vs 7 条**；
   有 Skill 那轮按任务书/SKILL 要求的四类（compute / data scale / hyperparameters / hidden assumptions）
   组织并用 `stated / inferred / absent` 三档标注置信度，
   **无 Skill 那轮自己发明了另一套类别名**（compute / data / model / objective / paper-evidence）
   并用了任务书/SKILL 没规定的 `confidence=high`。
   → 也就是说：**Skill 的价值更像是「把交付物的形状固定住」，而不是「让判断变准」**。
2. **「发现论文自身不一致」这件事，不能归因于 Skill。**
   三次会话里 checker 全是 0 标记；找到了 2 次、漏了 1 次，
   而**漏掉的那次恰恰是有 Skill 的那一次**（换了模型路由的那次，
   它写下了一句错误的否定性断言「核对时未发现论文摘要与正文、正文与脚注互相矛盾的数字」）。
   → 这是一条**关于方法**的结论：SKILL 第 7 步的「数值一致性自检」在结构上
   **不覆盖**「论文自己两个数之间是否自洽」，所以发现与否取决于模型当时愿不愿意多算一步。
3. **两轮对「压平表格」的处理方式不同，但都合规**：
   无 Skill 那轮**主动把** Table 3/Table 4 的数字降级为 `undetermined`（理由写得很清楚）；
   有 Skill 那轮**选择不引用**表格数字，只在正文/脚注里取事实。
   **两轮都没按出现顺序猜行列**——这条纪律看起来不需要 Skill 也会出现。
4. **样本与口径**：对照 n=1（每条件各 1 次），单一论文、单一模型路由、单一平台；
   耗时含上游排队与共享主机负载。**不能做统计显著性宣称**，
   也不能说「Skill 更好」或「Skill 没用」。
5. **失败留痕**：一次因上游 429 掐断的运行（归档第三次）、一次 SSE 断流自动重连，
   都完整保留在 `runs/` 里，没有删除任何失败产物。
