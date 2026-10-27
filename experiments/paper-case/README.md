# 案例 paper：在**真实论文**上跑 paper-method-fit-check，并做作者侧独立重算

> 这是作品仓库 `shiy08166-lab/paper-method-fit-check` 的**第二个案例**。
> 案例 C（`runs/C-with-3/`）用的是一份**被破坏的合成 README**；
> 这个案例用一篇**真实公开发表的论文**（LoRA, arXiv 2106.09685v2），
> 并补上了案例 C 缺的那一层：**作者侧独立重算的账本**。

---

## 1. 这次实践回答什么问题

案例 C 回答的是「**输入损坏时，方法会不会乱编**」。
这个案例回答另外两个问题：

1. **方法在真实论文上还站得住吗？** —— 真实论文的表格、公式、脚注，比合成件复杂得多，
   引用一件真东西的成本更高（引文必须逐字、含换行）。
2. **我们自己的结论，数字经不经得起复算？** —— 案例 C 里我们自己就犯过一次
   「机械检查全绿、语义不成立」的错（把受损表的一列当成另一列）。
   这个案例把同一层检查**搬到真实论文上**，而且搬到了**论文自己**头上。

## 2. 论文选型

**LoRA: Low-Rank Adaptation of Large Language Models**（arXiv:2106.09685v2，2021-10-16，
作者单位 Microsoft）。选它的理由：

- **开放获取**：arXiv PDF 可直接下载，许可为 arXiv 默认的永久非独占发布许可
  （`licenses/nonexclusive-distrib/1.0/`），详见 `materials/source_manifest.json`；
- **有可重算的数字**：显存（1.2TB→350GB）、checkpoint 体积（350GB→35MB）、
  参数量（0.01% / 18M / 4.7M / 37.7M）、吞吐（脚注 5：32.5→43.1 tokens/s）、
  表 1 的六个相对延迟百分比（+2.2% … +30.3%）——**每一个都能用论文自己给的数重算**；
- **有真实的迁移问题**：读者约束是「1×24GB 显存 + 7B 模型 + ≤$200」，
  论文讲的却是 GPT-3 175B 级别，**换算必然要做**，也必然可能做错。

> **注意**：任务书里原本设想的「277GB vs 96MB」那组数**不在这篇论文里**
> （全文检索 `277` / `96MB` 均 0 命中）。论文自己的数是 `1.2TB → 350GB` 与 `350GB → 35MB`。
> 本案例以**论文原文**为准。

## 3. 输入是什么

`materials/`：

| 文件 | 说明 |
|---|---|
| `lora_2106.09685.pdf` | 原始 PDF（1,609,513 B，SHA-256 `e9a0d312…95a`），唯一权威副本 |
| `source.txt` | 逐页抽取文本（82,806 B，SHA-256 `a8f387d2…84d`），页与页之间用 `=== PAGE n ===` 标记行分隔 |
| `source_pages.json` | 同一份文本按页切分的机器可读版本 |
| `source_manifest.json` | 来源 URL、版本、许可、字节数、SHA-256、**抽取规则与已知限制** |

**材料性质**（任务书里如实声明）：论文是**真实发表**的，可以当作者事实引用；
但正文是 **PDF 抽取文本**，不是作者手写的 Markdown/LaTeX，
且**表格在抽取文本里被压平为单元格序列，行/列身份不保留**。

## 4. 跑了两遍，唯一变量是「给不给 SKILL.md」

| | 有 Skill | 无 Skill（对照） |
|---|---|---|
| 工作区 | `runs/with-skill/` | `runs/without-skill/` |
| 唯一差异 | 多一个 `skill/SKILL.md` | 无 |
| 提示词差异 | 多一句「再读 `skill/SKILL.md`，然后按它的工作流做」 | 无此句 |
| 其余 | **逐字节相同**（`runs/workspace_diff.json` 可查：所有共有文件 SHA-256 一致） | 同左 |

两次运行都在**隔离副本**里进行（`work/tmp/paper-case/<name>/`），产物再按字节复制回 `runs/`。
原因很实际：对照轮的会话如果直接开在作品仓库里，**往上两层就能翻到 `paper-method-fit-check/SKILL.md`**，
对照就被污染了。

**会话是真的**：Codex CLI（非交互 `codex exec`），模型 `ccs-deepseek/deepseek-v4-pro`
（本地 CC Switch 路由）。会话原始日志在 `~/.codex/sessions/`，
导出的 `session-export.txt`（人读）与 `events.jsonl`（Skill 第 8 步要求的步骤类型）都在 `runs/<name>/`。
**成本：0（本地会话，无 API 费用）。**

> **为什么不是 gpt-6-astra**：本地桥接的 "OpenAI Official" 上游从这台机器**连不通**
> （`os error 10060` 连接超时），换路由后 23 秒就能跑完一个写文件任务。
> 这是环境事实，如实记录。
>
> **还有一次失败尝试被保留**：`runs/attempt1-with-skill-huoshan-429/`
> —— 第一次「有 Skill」运行跑在 `ccs-huoshan/deepseek-v4-pro-ga-260813` 路由上，
> 18.4 分钟后被上游 `429 Too Many Requests` 掐断（写完 5 个交付物、**在跑官方 checker 之前**）。
> 该路由随后持续 429，无法在**同一模型**上跑对照轮，所以最终两轮都换到 `ccs-deepseek/deepseek-v4-pro`
> **重跑**；第一次尝试按纪律**完整留痕、不删**。
> 它还独立复现了本案例的一条结论：换一个模型路由、按 Skill 的 8 步走，
> 报告**仍然没有发现论文自身的「25% vs 32.6%」口径不一致**（详见 `ledger.md`）。

**关键数字对照见 [`comparison.md`](comparison.md)**（由 `scripts/build_comparison.py`
从两次运行的产物里自动统计，不手写数字）。

## 5. 作者侧独立重算（本案例最值钱的一层）

`ledger.md`（人读）+ `ledger.json`（机器可读）+ `scripts/verify_paper_results.py`（一键复算）：

```bash
cd experiments/paper-case && python scripts/verify_paper_results.py
# -> status: passed（62 条检查，0 条不符，0 条已知缺口），退出码 0
```

账本分三层：

1. **论文自身的数字**（15 条）：每个比率/降幅都拿论文自己给的基线数重算一遍；
2. **语义层检查**（3 条）：表格数字的**行列身份**、相对降幅的**绝对量闭合**；
3. **两轮报告引用的数字**：回到原文页逐条核对（引文唯一命中 + 页码 + 数值 + 行列身份）。

### 找到的真问题

**「机械检查全绿，但语义不成立」——这次出在论文自己身上。**

论文第 5 页正文写 `We also observe a 25% speedup`，而**同一页的脚注 5** 写
`32.5 tokens/s per V100 GPU`（full fine-tuning）对 `43.1 tokens/s per V100 GPU`（LoRA）。
按吞吐提升的常规读法是 **+32.6%**，不是 25%；只有把 25% 读成「每 token 时间下降」（24.59%）才凑得上。

- 引文逐字命中 ✅
- `numeric_value=25` 与引文里的 25 一致 ✅
- `check_agreement.py` 标记数 0 ✅
- **结论成立吗？** ❌ 不成立

`check_agreement.py` 验的是「**引文里的数 == 你写的数**」，**从不验**「这个数是不是从论文自己的别的数推出来的」。
同一段还有第二处：论文说「VRAM 降 2/3」「GPU memory requirement by 3 times」，
而它自己的例子 `1.2TB → 350GB` 是 **3.43× / 70.83%**。

**而且「谁发现了它」这件事本身不稳定**：本次一共跑了三次会话
（最终对照的有 / 无 Skill 两轮 + 归档的第一次有 Skill 运行）——
**有 Skill、无 Skill 都发现了；漏掉的那次恰恰是有 Skill 的那一次**，
它还写下了一句**为假的否定性断言**（「核对时未发现论文摘要与正文、正文与脚注互相矛盾的数字」）。
→ **这处发现不能归因于 Skill**；能归因的是**方法缺了一步**：
SKILL 里既没有「复算论文自己的算术」，也没有任何针对**否定性断言**的检查位。

完整的发现、复算过程、以及**对方法本身的 6 条改进建议**见 [`ledger.md`](ledger.md) 第五节。

## 6. 局限（如实写）

- **n=1 对照组、单一论文、单一模型、单一平台**：只能说「这一次观察里有没有差别」，
  **不能做统计显著性宣称**，也不能说「Skill 更好」或「Skill 没用」。
- **表格的行列身份**在抽取文本里本来就丢失；作者侧靠 PDF 几何坐标重建
  （`scripts/extract_tables_geom.py`，需 PyMuPDF）才拿到真值。
  **这一步不在 Skill 里**——这正是改进建议之一。
- 论文的 PDF 抽取文本有已知噪声：小型大写标题、公式里的 `(cid:NN)` 私用区字形。
  账本里的算式只用**论文原文里的数**，不依赖抽取质量。
- `verify_paper_results.py` 只依赖标准库；`extract_tables_geom.py` / `extract_source.py`
  需要 PyMuPDF / pdfminer，**不在复算关键路径上**。

## 7. 复现命令

```bash
cd ai-github-work/repo/experiments/paper-case

# 0) 冻结件与材料的完整性
python scripts/verify_paper_results.py          # -> status: passed，退出码 0

# 1) 重新抽取（从 PDF 重建 source.txt / source_pages.json）
python scripts/extract_source.py \
    --pdf materials/lora_2106.09685.pdf \
    --txt materials/source.txt \
    --json materials/source_pages.json

# 2) 重建作者侧账本（引文按锚点从 source.txt 切出，逐字节一致）
python scripts/build_ledger.py

# 3) 作者侧几何重建表格（取真实行列身份）
python scripts/extract_tables_geom.py --pdf materials/lora_2106.09685.pdf --pages 4  --out logs/author_table1_geom.txt
python scripts/extract_tables_geom.py --pdf materials/lora_2106.09685.pdf --pages 21 --out logs/author_table12_geom.txt

# 4) 两轮运行的对照表（自动统计）
python scripts/build_comparison.py

# 5) 装配两次运行的同条件工作区并核对差异
python scripts/build_runs.py
python scripts/build_runs.py --dest-root <隔离目录>

# 6) 官方自检（原样跑）
cd runs/with-skill && python scripts/check_agreement.py \
    --claims claims.csv --preconditions preconditions.csv \
    --source materials/source.txt --tolerance 0.01 --report logs/agreement.json
```

## 8. 目录

```
experiments/paper-case/
├─ README.md                     ← 本文件
├─ HANDOFF.md                    ← 给作者的交接单（最小切片建议）
├─ ledger.md / ledger.json       ← 作者侧独立重算账本（人读 / 机器读）
├─ comparison.md                 ← 有/无 Skill 同条件对照
├─ cases/
│  ├─ task-paper.md              ← 冻结的任务书（运行前写定）
│  ├─ acceptance-paper.md        ← 冻结的验收标准（运行前写定）
│  └─ frozen_hashes.json         ← 两份冻结件 + SKILL.md 的 SHA-256
├─ materials/                    ← PDF + 抽取文本 + source_manifest.json
├─ logs/                         ← 作者侧几何重建的表格 + 会话复跑产物
├─ runs/
│  ├─ workspace_diff.json        ← 两次工作区逐文件哈希差异（只有 skill/SKILL.md + prompt.txt）
│  ├─ with-skill/                ← 5 个交付物 + prompt + session-export + events + logs
│  └─ without-skill/             ← 同上
└─ scripts/
   ├─ verify_paper_results.py    ← 一键复算（仅标准库）
   ├─ build_ledger.py            ← 账本数据层生成
   ├─ extract_source.py          ← PDF → 带页码锚点的文本
   ├─ extract_tables_geom.py     ← 按坐标重建表格（作者侧）
   ├─ build_runs.py              ← 装配同条件工作区
   ├─ build_comparison.py        ← 对照表自动统计
   ├─ export_codex_session.py    ← 会话日志 → session-export.txt + events.jsonl
   ├─ finalize_run.py            ← 产物按字节复制回 runs/
   └─ build_handoff_slice.py     ← 切片建议（按字节）
```
