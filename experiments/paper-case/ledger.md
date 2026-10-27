# 作者侧独立重算账本：LoRA（arXiv 2106.09685v2）这篇论文的每个数字都能回算

> **为什么要有这一层**：方法侧的检查（引文命中、数值一致）只能证明**没有自相矛盾**；
> 这一层证明的是**每个数字是怎么来的**，以及**报告引用的数字和论文自己给的数据对不对得上**。
> 一键复算：
>
> ```bash
> cd experiments/paper-case && python scripts/verify_paper_results.py
> ```
>
> 预期结尾：`status: passed（97 条检查，0 条不符，0 条已知缺口）`；任一条**不符** → 退出码 1。
> 只依赖标准库。

**账本里混着两类东西，本文档严格分开标注：**

| 标记 | 含义 |
|---|---|
| **【作者重算】** | 作者侧从论文原文重新算出来的数，与被测会话的输出无关 |
| **【会话引用】** | 被测会话报告里引用的数，作者回头去论文原文（或报告自身）核对 |
| **【反例】** | 归档的第一次有 Skill 运行（`runs/attempt1-with-skill-huoshan-429/`）里的**漏检实例** |

---

## 一、最重要的发现：「机械检查全绿，但语义不成立」

案例 C 里，这类错误是**我们自己**的假设把受损表的一列搞错了。这一次，它出现在**论文自己身上**——
而且是 `check_agreement.py` 这类工具**结构上抓不到**的那种。

### 论文第 5 页的「25% speedup」与它自己第 5 页脚注 5 的数字对不上

- **原文（正文，第 5 页）**：

  > `We also observe a 25% speedup`⏎`during training on GPT-3 175B compared to full fine-tuning5 as we do not need to calculate the`⏎`gradient for the vast majority of the parameters.`

- **原文（同页脚注 5）**：

  > `5For GPT-3 175B, the training throughput for full fine-tuning is 32.5 tokens/s per V100 GPU; with the same`⏎`number of weight shards for model parallelism, the throughput is 43.1 tokens/s per V100 GPU for LoRA.`

- **【作者重算】**：按吞吐提升的常规读法，`43.1 / 32.5 − 1 = +32.615%`，**不是 25%**。
- **【作者重算】**：只有把 25% 读成「**每 token 时间下降**」才凑得上：`1 − 32.5/43.1 = 24.594% ≈ 25%`。
- **判定**：**口径不一致**。同一个「speedup」有两种读法，论文没说是哪一种；而正文那句是全文里
  唯一给出吞吐收益数字的地方，摘要只说「a higher training throughput」。

**为什么机械检查抓不到**：

| 机械检查 | 结果 |
|---|---|
| 引文逐字命中原文？ | ✅ 命中，唯一 |
| `numeric_value=25` 与引文里的 25 一致（1% 内）？ | ✅ 一致 |
| `check_agreement.py` 标记数 | ✅ 0（**三次会话全部 0 标记**） |
| **报告结论「LoRA 训练快 25%」成立吗？** | ❌ **不成立**（按论文自己的脚注数据是 +32.6%） |

`check_agreement.py` 验的是「**引文里的数 == 你写的数**」，它**从不验**「**这个数是不是从论文
自己的别的数推出来的**」。只要报告照抄了正文的 25，整条流水线就是全绿的。

### 这次跑了三次会话，谁发现了它？（**结果不稳定**）

| 会话 | 模型路由 | 有 SKILL.md | 算出 32.6 | 指出不一致 | 官方 checker |
|---|---|---|---|---|---|
| `runs/with-skill/` | `ccs-deepseek/deepseek-v4-pro` | ✅ | ✅ | ✅ | 0 标记 |
| `runs/without-skill/` | `ccs-deepseek/deepseek-v4-pro` | ❌ | ✅ | ✅ | 0 标记 |
| `runs/attempt1-with-skill-huoshan-429/` | `ccs-huoshan/deepseek-v4-pro-ga-260813` | ✅ | ❌ | ❌ | 0 标记 |

**结论很硬**：**这处发现不能归因于 Skill**——
最终对照的两轮（有 / 无 Skill）**都**发现了它；
而**漏掉它的那次恰恰是有 Skill 的那一次**（换了模型路由的那次），
它还写下了一句**错误的否定性断言**：

> `核对时未发现论文摘要与正文、正文与脚注互相矛盾的数字（见日志；如后续核对有出入会写入本节）。部分满足（未发现不一致）。`
> —— `runs/attempt1-with-skill-huoshan-429/verdict.md`「预期行为对照 ②」

**「否定性断言在整个流程里没有任何机械检查位」**：模型说它查过了，
机械层面拿不出**任何**证据证明它真查过。这是本案例对方法本身最硬的一条批评。

### 同一段还有第二处口径问题：「up to 2/3」与「3 times」

- **原文（第 5 页）**：

  > `For a large Transformer trained with Adam, we reduce that VRAM`⏎`usage by up to 2/3 if r (cid:28) dmodel as we do not need to store the optimizer states for the frozen`⏎`parameters. On GPT-3 175B, we reduce the VRAM consumption during training from 1.2TB to`⏎`350GB.`

- **原文（第 1 页摘要）**：

  > `Compared to GPT-3 175B fine-tuned with Adam,`⏎`LoRA can reduce the number of trainable parameters by 10,000 times and the`⏎`GPU memory requirement by 3 times.`

- **【作者重算】**：`1.2TB → 350GB` 的降幅是 `1 − 350/1200 = 70.83%`，
  倍数是 `1200/350 = 3.43×`。
- **判定**：**不符**（论文的自述比它自己的例子保守）。
  「至多 2/3」（66.67%）被它紧挨着的例子（70.83%）**超过**；
  摘要的「3 times」实为 3.43×。
  两种方向的偏差都存在：说「25% speedup」是**低估**收益（实际 32.6%），
  说「2/3 / 3 times」是**高估**自己的保守表述（实际 70.8% / 3.43×）。
  论文一处也没说明口径。

- **【反例】同一份报告把两者并列而不调和**：归档那次运行的 `PF2` 写「GPU memory 3x」、
  `PF8` 写「1.2TB→350GB」，两条都是 `paper-fact`、checker 0 标记，
  **但报告没有把 `1200/350 = 3.43×` 和「3×」对上**（账本 P-30）。

---

## 二、论文自身数字的逐条重算（18 条，脚本实时复算）

| id | 数字 / 断言 | 原文定位 | 算式 | 复算结果 | 判定 |
|---|---|---|---|---|---|
| P-01 | 「VRAM 降 2/3」vs 自己的 1.2TB→350GB | p.5 §4.2 | `(1-350/1200)*100` | 70.83% | **不符**（自述 66.67%） |
| P-02 | 摘要「GPU memory requirement by 3 times」 | p.1 摘要 | `1200/350` | 3.43× | **不符**（自述 3×） |
| P-03 | 正文「25% speedup」 | p.5 + 脚注 5 | `(43.1/32.5-1)*100` | 32.62% | **不符**（自述 25%） |
| P-04 | 脚注 5 的另一种口径 | p.5 脚注 5 | `(1-32.5/43.1)*100` | 24.59% | 符（解释 P-03） |
| P-05 | checkpoint 350GB→35MB 的「10,000×」 | p.5 §4.2 | `350*1000/35` | 10,000 | 符 |
| P-06 | 「18M 参数 ≈ 35MB(FP16)」 | p.10 §7.1 | `18000000*2/1048576` | 34.33 MiB | 符（差 1.91%，"roughly"） |
| P-07 | 「\|Θ\| 可小到 \|Φ0\| 的 0.01%」vs 18M | p.3 §2 | `175e9*0.0001/1e6` | 17.5M | 符（差 2.86%，同一处舍入） |
| P-08 | 脚注 4：350GB + 35MB×100 ≈ 354GB | p.5 脚注 4 | `350+35*100/1000` | 353.5 | 符（论文向上取整） |
| P-09 | 脚注 4：100×350GB ≈ 35TB | p.5 脚注 4 | `100*350/1000` | 35 | 符 |
| P-16 | 论文公式推出的 \|Θ\| vs p.10 的「18M」 | p.6 公式 + p.2 + p.10 | `2*192*12288*4` | 18,874,368 | 符（差 4.7%，舍入） |
| P-17 | LoRA 检查点精确字节数 vs「35MB」 | p.10 + P-16 | `2*192*12288*4*2/1048576` | 37.75 MiB | 符（差 7.9%，舍入） |
| P-18 | 「缩小 10,000×」在精确 \|Θ\| 下 | p.5 + P-16/17 | `350*1000/37.75` | 9,282× | 符（差 7.2%，舍入） |
| P-22 | 表 1：AdapterL @ batch 32 = +2.2% | p.4 Table 1 | `(1482.0-1449.4)/1449.4*100` | 2.249% | 符 |
| P-23 | 表 1：AdapterH @ batch 32 = +3.0% | p.4 Table 1 | `(1492.2-1449.4)/1449.4*100` | 2.953% | 符 |
| P-24 | 表 1：AdapterL @ batch 16 = +5.0% | p.4 Table 1 | `(354.8-338.0)/338.0*100` | 4.970% | 符 |
| P-25 | 表 1：AdapterH @ batch 16 = +8.4% | p.4 Table 1 | `(366.3-338.0)/338.0*100` | 8.373% | 符 |
| P-26 | 表 1：AdapterL @ batch 1 = +20.7% | p.4 Table 1 | `(23.9-19.8)/19.8*100` | 20.707% | 符 |
| P-27 | 表 1：AdapterH @ batch 1 = +30.3% | p.4 Table 1 | `(25.8-19.8)/19.8*100` | 30.303% | 符 |

> P-22…P-27 的**行列身份**不是从抽取文本读的——抽取文本把表压平了。
> 作者侧用 PDF 的**几何坐标**重建了表 1（`logs/author_table1_geom.txt`，
> 由 `scripts/extract_tables_geom.py` 生成），确认：
> 行 = `Batch Size / Sequence Length / |Θ| / Fine-Tune/LoRA / AdapterL / AdapterH`，
> 列 = `batch 32(seq 512) / batch 16(seq 256) / batch 1(seq 128)`。

---

## 三、语义层检查（机械检查抓不到的那一层，4 条）

### S-01：表 1 的 `|Θ|` 行是 **adapter 层**的参数量，不是 LoRA 的

- **原文（p.4 表注）**：

  > `Table 1: Infernece latency of a single forward pass in GPT-2 medium measured in milliseconds, av-`⏎`eraged over 100 trials. We use an NVIDIA Quadro RTX8000. “|Θ|” denotes the number of trainable`⏎`parameters in adapter layers.`

- **抽取文本里的样子**：`Batch Size` → `Sequence Length` → `|Θ|` → `0.5M` → `11M` → `11M` …
  **`|Θ|` 那一行紧跟在 `Sequence Length` 后面**，读起来非常像「LoRA 的可训练参数量」。
- **真值（几何重建）**：`|Θ| = 0.5M / 11M / 11M`，是 **adapter 层**的可训练参数量；
  LoRA 自己的 `|Θ|` 是另一个量级（GPT-3 175B 上 4.7M / 37.7M，见 p.8 Table 4）。
- **判定**：**语义高危点**。任何把 `0.5M` 当成「LoRA 只需 0.5M 可训练参数」的引用都是错的。

### S-02：表 12（p.21）的**行身份**在抽取文本里直接丢了

- **抽取文本的顺序**：5 个行标签 `Optimizer / Batch Size / # Epoch / Warmup Tokens / LR Schedule`
  **先连着出现**，**然后**才是它们的值 `AdamW / 128 / 2 / 250,000 / Linear`。
  按位置读，会把「128」当成 Optimizer 的值。
- **真值（几何重建，`logs/author_table12_geom.txt`）**：
  `Optimizer=AdamW`、`Batch Size=128`、`# Epoch=2`、`Warmup Tokens=250,000`、`LR Schedule=Linear`；
  `Learning Rate` 一行：`Fine-Tune=5.00E-06`、`PreEmbed=5.00E-04`、`PreLayer=1.00E-04`、
  `BitFit=1.6E-03`、`AdapterH=1.00E-04`、`LoRA=2.00E-04`。
- **判定**：**语义高危点**。这五行恰好是读者判断「我能不能照着跑」最需要的超参
  （batch size、warmup、学习率）。把它们安到错的行上，读者的结论会直接错。

### S-03：「LoRA 省显存 3×」是**相对降幅**，不能当成「24GB 单卡能跑 7B」

- **【作者重算】**：`350GB / 1200GB = 29.17%` 留在原地 —— 也就是说 **LoRA 之后那 350GB
  就是冻结权重本身**（175B × 2B）。
- **判定**：论文的 3.43× 是**同一个 175B 模型**上的降幅；
  搬到 7B / 24GB 上时，基线显存本身只有 14GB 量级，而 full fine-tune 的**优化器状态**才是大头。
- **推论**：**报告若只写「LoRA 省显存 3×，所以 24GB 够用」，就是拿相对降幅当绝对可行性**——
  引文逐字命中、数值 1% 内、checker 0 标记，**全绿**，但结论不成立。
  （对照轮自己就写了这条：「3 倍显存节省不能直接套用……须按上面公式重算」——
  **这条纪律不需要 Skill 也会出现**，但 SKILL 里也确实没有它。）

### S-04：论文自身「25% vs 32.6%」的口径差：**差异确实存在**（供复核）

复算值 `+32.6154%` 与论文正文的 `25%` 确实不同（差 7.6 个百分点）。
**这是本案例的「真问题」本体**：三次会话里 checker 都是 0 标记，
两次会话发现了它、一次没有——**发现与否不取决于有没有 SKILL.md**。

---

## 四、【会话引用】被测报告引用的数字，回原文逐条核对

| id | 报告里的数 | 报告 | 算式 | 复算 | 判定 |
|---|---|---|---|---|---|
| P-19 | 有 Skill 轮 INF-2：\|Θ\| = 2×64×4096×8 = 4.19M | `runs/with-skill/` | `2*(2*32)*4096*8` | 4,194,304 | 符 |
| P-20 | 有 Skill 轮 INF-2：全参微调 84GB / LoRA 基座 14GB | `runs/with-skill/` | `7e9*(2+2+4+4)/1e9` | 84 GB | 符 |
| P-21 | 无 Skill 轮 I2：\|Θ\| ≈ 4.2M、全参微调 84GB | `runs/without-skill/` | `7e9*(2+2+8)/1e9` | 84 GB | 符 |
| P-28 | 有 Skill 轮自己发现的两处论文口径不一致 | `runs/with-skill/` | `(43.1/32.5-1)*100` | 32.62% | **不符**（论文正文 25%） |
| P-29 | 无 Skill 轮也自己发现了「25% vs 32.6%」 | `runs/without-skill/` | `(43.1/32.5-1)*100` | 32.62% | **不符**（同上） |
| P-30 | **【反例】**归档那次：PF2「3x」与 PF8「1.2TB→350GB」并列未调和 | `runs/attempt1-…/` | `1200/350` | 3.43× | **不符** |
| P-31 | **【反例】**归档那次：「未发现……不一致」这个否定性断言 | `runs/attempt1-…/` | `(43.1/32.5-1)*100` | 32.62% | **不符**（断言为假） |

> P-21 里有一条值得单独说：对照轮自己加了一个锚点——
> 「用论文锚点 1.2 TB/175B ≈ 6.9 B/参数 也得 ≈48 GB，都 > 24 GB」。
> **这是用论文自己的数据给读者场景做绝对量闭合**，正是本节第五节建议加进 Skill 的那条纪律。

---

## 五、这次发现对「方法适用性核查」这一方法本身的改进建议

| # | 建议 | 理由（来自本案例的具体证据） | 落点 |
|---|---|---|---|
| 1 | **给 SKILL 加第 7.5 步：「复算论文自己的算术」** —— 对论文里每一个比率/降幅/百分比，找出它依赖的**基线数**，用论文自己给的数重算一遍，对不上就写进第 ④ 节 | 论文的「25% speedup」与它自己脚注 5 的 32.5→43.1 tokens/s 对不上（+32.6% vs 25%）；「up to 2/3」与自己的 1.2TB→350GB 对不上（70.83% vs 66.67%）。`check_agreement.py` 结构上不可能发现这类错误。 | SKILL.md 第 7 步之后 |
| 2 | **否定性断言必须挂可核验的证据** —— 凡结论形如「论文没有给出 X」「未发现不一致」，必须在 `evidence_index.json` 里登记**查过哪些位置/关键词**，否则降级为 `undetermined` | 归档那次写下「未发现……互相矛盾的数字」这个**为假的否定性断言**，而**没有任何机械检查位**能发现它 | SKILL.md 第 4 步 |
| 3 | **相对降幅必须配绝对量** —— 凡是「省 X 倍 / 降 Y%」的迁移结论，必须同时给出基线的**绝对值与单位**，并算出落到读者场景后的绝对数 | 1.2TB→350GB 的 3.43× 被搬去回答「24GB 单卡能不能跑 7B」，结论直接不成立（S-03）。对照轮自发做了这条（用 1.2TB/175B ≈ 6.9 B/参数 推 ≈48 GB），但 SKILL 里没有 | SKILL.md 第 5 步 |
| 4 | **表格数字必须先确定行列身份，确定不了就降级**；并把「PDF 抽取文本会压平表格」写进 Failure modes | 表 1 的 `|Θ|` 行会被当成 LoRA 的参数量（S-01）；表 12 的行标签与值会错位配对（S-02） | SKILL.md 第 3 步 + 第 4 步 |
| 5 | **把「按 PDF 坐标重建表格」作为可选工具进包**（`scripts/extract_tables_geom.py` 的最小版），或在任务书里要求会话自己重建行列身份 | 本案例的作者侧复算正是靠坐标重建才拿到表 1/表 12 的真行列身份。**这一层工具目前不在 Skill 里** | SKILL.md 第 3 步 + `scripts/` |
| 6 | **对「前置条件的类别与置信度取值域」给出机器可查的约束**（四类固定、`confidence ∈ {stated, inferred, absent}`） | 对照轮自创了 `compute/data/model/objective/paper-evidence` 与 `confidence=high`，产物**不合契约**（`comparison.md` 第 1 节） | SKILL.md 第 2 步 + Validation |

---

## 六、复算脚本怎么跑

```bash
cd experiments/paper-case

# 1) 重建账本数据层（引文按锚点从源文件切出，逐字节一致）
python scripts/build_ledger.py

# 2) 重算一遍（只会重算，不改材料）
python scripts/verify_paper_results.py     # -> status: passed，退出码 0

# 3) 作者侧几何重建表（需要 PyMuPDF；仅用于取表格的真实行列身份）
python scripts/extract_tables_geom.py --pdf materials/lora_2106.09685.pdf --pages 4  --out logs/author_table1_geom.txt
python scripts/extract_tables_geom.py --pdf materials/lora_2106.09685.pdf --pages 21 --out logs/author_table12_geom.txt

# 4) 对照表与切片建议
python scripts/build_comparison.py
python scripts/build_handoff_slice.py --budget-kib 14
```

`verify_paper_results.py` 只依赖 Python 标准库；
第 3 步的 `extract_tables_geom.py` 需要 PyMuPDF（**它不在本次交付的复算关键路径上**：
账本的每一条算式都只用论文原文里的数，不依赖几何重建）。
