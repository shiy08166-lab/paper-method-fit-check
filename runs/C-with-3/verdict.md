# 案例 C · 评估结论（`paper-method-fit-check`）

| 项 | 值 |
|---|---|
| 评估对象 | `materials/nanochat_README_table_corrupted.md`（**合成/损坏件**，非作者原文） |
| 材料 SHA-256 | `64a46d328926d45842d9e8ad0a1817b01d176ad915e55ba92609119ca571917c`（17,623 B） |
| 上游原文快照 | `materials/A/nanochat_README.md`（SHA-256 `1ac00d0999b0bebb397f596f38dd2d6a218a60994775a488f9ef3cc93484cf00`） |
| 读者约束 | 8 × A100 80GB；训练 ≤4 h；云卡 ≤$100；数据可下载（磁盘 ≥100 GB，下载时间需单独说明）；只要方法机制、不要求复现数字 |
| Skill | `skill/SKILL.md`（未改动），`scripts/check_agreement.py` 取自仓库同名脚本，逐字复制 |
| 本次运行 | **全程离线**（未使用任何联网检索/抓取）；未训练、未下载数据集、未安装 PyTorch |

---

## ① Verdict

**`transferable-with-changes`** —— 方法机制（单一 `--depth` 旋钮 + 单文件 `runs/speedrun.sh` 流水线 + DCLM CORE 门限 + d12 快速标定循环）在 8×A100 80GB / ≤4 h / ≤$100 下**可以迁**，依据是这些输入全部位于**未受损且已逐行核对为上游原文**的正文段落（材料明说支持 8×A100，每卡 80 GB 恰好满足其 ≥80 GB 阈值，参考墙钟 1.5 h 在 4 h 预算内）。

但它**不是开箱即用**：A100 的减速倍率未量化（原文只有"a bit slower"）、数据下载时间与体积未给、完整超参与评测口径未随材料提供，且被破坏的 leaderboard 表格使"数字基线"不可引用——因此需要按下文第 ⑤ 节的改动清单先做标定与索取，而不是直接照表跑数。

> 本节只给结论词与两句理由；前置条件适配明细见第 ⑤ 节，异常处理逐条对照见第 ⑥ 节。

---

## ② What is established（已确证 · `paper-fact` 共 28 条）

来源一律为 `materials/nanochat_README_table_corrupted.md`（合成转载件）。**非表格段落**已逐行核对为上游原文（`logs/line_provenance.json`：211 行中除合成件自带的 `---` 分隔线外全部在上游快照中原样命中，上游无多余行）。表格内 4 条（C25–C28）另有标注：该章节**未做上游核验**（见第 ⑨ 节）。

**指标与成本口径（`§ Time-to-GPT-2 Leaderboard`，L41）**

- C01 主指标 = 在 8×H100 上把 GPT-2 (1.6B) 的 CORE 超过去所需的墙钟时间。
- C02 GPT-2 CORE 分数 = 0.256525；C06 2019 年训练成本约 $43,000。
- C03 单价 ~$3/GPU/hr；C04 8×H100 ≈ $24/hr；C05 2 小时 ≈ $48。

**机制本体（决定"能不能迁"的部分）**

- C07 全流程收敛在单文件 `runs/speedrun.sh`，为 8×H100 设计。
- C13 唯一复杂度旋钮 `--depth`（层数），其余超参自动计算，GPT-2 能力 ≈ depth 26；C14 当前代码落在 d24–d26。
- C15 speedrun 模型 = 4e19 FLOPs；C16 快速实验档位 = 12 层、约 5 分钟预训练（标定用）。
- C17 迭代监控 `val_bpb` / `core_metric` / VRAM / MFU / 吞吐。
- C21 优化器 AdamW + Muon；C22 CORE 评测在 `nanochat/core_eval.py`（DCLM 口径）；C24 目标是把 CORE 提到 0.256525 之上，当前约 1.5 h（此前 3 h）。
- C19 权重 fp32 存储、前向转 COMPUTE_DTYPE；C20 fp16 自动 GradScaler（SFT 支持，RL 不支持）。
- C23 语料来自 HuggingFace（fineweb、smoltalk）——**只说明来源，不等于默认配置**。

**与读者硬件直接相关的三条**

- C09 代码可在 8×A100 节点运行，原文只说"a bit slower"（**无量化倍率**）。
- C11 GPU 显存低于 80 GB 必须调超参，否则 OOM / 显存溢出。
- C10 单 GPU 可跑（去掉 `torchrun`，自动切梯度累积），结果 ~identical，代价是等待 ×8。
- C12 `--device-batch-size` 默认 32，可依次降到 16/8/4/2/1。

**受损表格中"单元格本身未被改动"的部分（C25–C28）**

- C25 存在一行 OpenAI 原始 GPT-2 检查点记录：168 hours、0.2565、2019、OpenAI。
- C26 存在一行 d24 baseline 记录：3.04、0.74833、Jan 29 2026、348fbb3。
- C27 存在一行 autoresearch round 2 记录：1.65、0.71800、Mar 14 2026、a825e63。
- C28 存在一行 Description 单元格自述"change dataset to NVIDIA ClimbMix"。

---

## ③ What I inferred（我的推断 · `inference` 共 4 条，均非原文陈述）

- **C29 列映射假设**：数据行的 7 格按位置对应表头的 #/time/CORE/Description/Date/Commit/Contributors。依据：(a) # 0 行里"168 hours"只可能是 time，"0.2565"与正文 0.256525 相对误差 0.0098 %（<1 %），该行其余单元格各自自洽；(b) 其余行的 Description/Date/Commit/Contributors 文本自洽；(c) 机械破坏通常对各行删除同一列。**这是我的推导**，只影响"各行 time 怎么读"，不影响受损单元格不可恢复。
- **C30 读榜方式**：已读出的行中 time 随 # 增大单调变小（# 6 行的 1.65 为最小），说明 # 更像名次而非序号；但文件物理行序已被打乱（# 出现顺序 6,1,4,0,3,2,5），**不能按出现顺序读榜**。该单调性同时是本任务明令禁止的猜补路径——**我据此拒绝给出受损单元格的任何区间或点估计**。
- **C31 迁移判定**（推导链见 `claims.csv`）：A100 被明确支持 → 每卡 80 GB 恰好达标 → 参考 1.5 h 落在 4 h 预算内但 A100 倍率未量化（stretch）→ 成本按材料自身口径 $3/GPU/hr 推算 8 卡 × 4 h = **$96 ≤ $100**（余量 4 %，材料未给 A100 报价故按同价保守计）→ 数据侧下载时间/体积缺失使预算无法闭合。目标只要机制、不要复现数字，所以被破坏的 leaderboard **不构成阻塞**。
- **C32 破坏的影响面**：被破坏的表格只影响"数字基线/名次"的可引用性，不影响"机制能否迁移"的判定——机制所需输入全部在未受损正文里，且这些段落已逐行核验为上游原文。

---

## ④ What remains open（遗留 · `undetermined` 7 条 + `absent` 11 条）

### 4.1 结论级遗留（`claims.csv` 中 `classification=undetermined`，`confidence=absent`）

| claim | 遗留内容 | **需要什么才能定** | 去哪找 |
|---|---|---|---|
| C33 | 榜单 # 4 行（Description = change dataset to NVIDIA ClimbMix）的墙钟时间——该单元格被截断，**不按行序/相邻行/CORE 接近性猜补**，`numeric_value` 留空 | 未损坏的同一行 | 上游 README 同一节 / `dev/LEADERBOARD.md` / 该 run 的作者日志（commit `324e69c`） |
| C34 | 原表存在一个**无法复原的列**（表头 7 列名 vs 分隔行 8 段 vs 数据行 7 格）：合成声明称其为 `val_bpb`，其任何取值都不可重建 | 未损坏的表头 + 数据行 | 同上；`val_bpb` 另可从 `nanochat/loss_eval.py` 或 wandb 曲线取 |
| C35 | 榜单官方名次/榜首（行序被打乱，且材料未声明 # 是否即名次） | 未损坏的榜单 | 上游 README 同一节 / `dev/LEADERBOARD.md` |
| C36 | 当前 speedrun 的预训练语料（混合/版本/token 量） | `dataset.py` 与 `speedrun.sh` 的数据参数 | 仓库源码 |
| C37 | 数据下载耗时与落盘体积（读者明确要求单独说明下载时间） | 下载清单 + 各文件体积，或一次实测下载（**不需要训练**） | `nanochat/dataset.py` / 实测 |
| C38 | A100 相对 H100 的时间倍率 | 一次 A100 标定：d12 档约 5 分钟（见 C16），或 d24 量级短跑 | 自己的云卡 |
| C39 | 榜单 `time` 列的计时口径（是否含评测/保存/数据加载） | 口径说明 / 提交规则 | `dev/LEADERBOARD.md` |

### 4.2 前置条件级遗留（`preconditions.csv` 中 `confidence=absent`，每条都写了原因）

`P-C8` 实测峰值显存 · `P-C9` A100/H100 时间倍率 · `P-D4` 训练 token 数与语料体积 · `P-D5` 默认预训练语料身份 · `P-D6` 数据下载耗时 · `P-D7` 数据落盘体积（对照磁盘 ≥100 GB） · `P-D8` 评测集规模 · `P-H8` speedrun 完整超参（lr/warmup/序列长度/depth 配置） · `P-A4` 语料混合与版本 · `P-A5` CORE 评测依赖与版本 · `P-A6` `time` 列计时口径。

> 另有一项**材料内不存在、但迁移会碰到**的约束未列为前置条件：读者只要"方法机制"、不要求复现数字——它是**读者侧约束**（`cases/task-C.md`），不是论文的前置条件，因此未写进 `preconditions.csv`。

---

## ⑤ 前置条件适配与具体改动（satisfied / stretch / blocked / unknown）

`blocked` 项：**0**（不存在"在本约束下拿不到"的方法要素）。

| id | 判定 | 依据 | **具体改动**（不是"有难度"）与预期影响 |
|---|---|---|---|
| P-C1 | stretch | 参考配置是 8×H100 | 改用 8×A100 80GB 节点（材料明说支持，C09）；影响 = 墙钟变长，倍率未知 → 由 P-C9 标定补齐 |
| P-C2 | stretch | ~1.5 h 是 H100 上的数 | 先跑 d12 档（8 卡，约 5 min，C16）测 A100 吞吐，按 4e19 FLOPs 外推总时长；外推 >3 h 时把目标 depth 从 d26 降到 d24（C14 区间内），而不是硬跑超时 |
| P-C3 | satisfied | 材料口径 $3/GPU/hr | 无需改动；订卡前按实际 A100 单价复核（材料未给 A100 报价） |
| P-C4 | satisfied | 8 卡 × 4 h = 32 GPU·h × $3 = **$96 ≤ $100**（余量 4 %） | 无需改动；这是材料自身单价下的**最坏情况**估计，A100 若更便宜则更宽松 |
| P-C5 | stretch | "a bit slower" 未量化 | 与 P-C2 同一条标定动作 |
| P-C6 | satisfied | 读者有 8 卡 | 无需改动（单卡退化路径用不上） |
| P-C7 | satisfied | 读者每卡 80 GB 恰好达标 | 无需改动；只有实测 OOM 时才按 C12 把 `--device-batch-size` 32→16/8/4/2/1 |
| P-C8 | unknown | 无实测峰值显存 | 首跑监控 VRAM 利用率（README 明确可监控，C17）；若逼近 80 GB 立即降 `--device-batch-size` |
| P-C9 | unknown | 无倍率 | d12 标定外推；这是"4 h 预算够不够"的唯一未知量 |
| P-D1 / P-D2 | satisfied | 1.6B / 4e19 FLOPs | 无需改动；目标规模与读者一致 |
| P-D3 | stretch | 数据可下载，但体积/耗时未知 | 先跑 `dataset.py` 下载清单测体积与耗时；若落盘 >100 GB 则改子集/流式读取；下载时间在预算中**单独列出**（读者要求） |
| P-D4 / P-D5 / P-D7 / P-D8 | unknown | 材料未给 | 读 `dataset.py`、`speedrun.sh`、`core_eval.py`（见第 ⑦ 节 1–3） |
| P-D6 | unknown | 材料未给 | 实测下载（不需要训练） |
| P-H1 | satisfied | `--depth` 即要迁的机制本体 | 无需改动 |
| P-H2 | satisfied | 默认 32 | 保持默认 32，仅 OOM 时按 C12 逐级下调 |
| P-H3 | unknown | 只出现在受损表格的 Description 单元格 | 读 `runs/speedrun.sh` 取真实 batch 配置，**不用表格里的 1M tokens 当默认** |
| P-H4 | satisfied | A100 是 SM80，native bf16 | 无需改动（不必退回 fp32，也不必启用 fp16/GradScaler） |
| P-H5 / P-H6 | satisfied | 机制本体 | 无需改动 |
| P-H7 | satisfied | A100 默认 bf16，用不到 fp16 | 无需改动 |
| P-H8 | unknown | 材料只说"自动计算" | 读 `runs/speedrun.sh` 取完整超参，否则无法复算训练量 |
| P-A1 | satisfied | 8 卡 `torchrun` 即参考配置 | 无需改动 |
| P-A2 | satisfied | 原则明确 | 若要改代码，必须对**所有 depth** 有效，否则破坏"单一旋钮"这个被迁的机制本身 |
| P-A3 | stretch | 榜单各行对应不同 commit | **不要用榜单某一行的 commit 去对齐结果**；用当前 master 的 `runs/speedrun.sh`，并把"只迁机制、不追数字"写进验收口径 |
| P-A4 / P-A5 | unknown | 材料未给 | 读 `dataset.py` 与 `core_eval.py`（+ DCLM 论文） |
| P-A6 | unknown | 计时口径未给 | 读 `dev/LEADERBOARD.md`；在此之前，对外报数必须注明"口径未知" |
| P-A7 | satisfied | 门限 CORE > 0.256525 明确 | 无需改动 |

---

## ⑥ 异常处理对照（逐条对照 task-C.md 事先声明的 5 条预期行为）

| # | 事先声明的预期行为 | 我的实际做法 | 证据位置 | 自评 |
|---|---|---|---|---|
| 1 | **识别异常**：指出表头与数据列数不一致、行序与 `#` 错位、至少一个数值被截断，并给出判断依据 | 逐行数单元格后给出**实测**结论：表头 7 个列名 / 分隔行 **8** 段 / 数据行多为 **7** 格、其中 1 行 **9** 格；`#` 在文件中的出现顺序为 **6,1,4,0,3,2,5**，7 行**全部**与物理位置错位；# 4 行的 `time` 单元格被截断（只剩 `2.`）；# 5 行多出 2 个分隔符/2 格（`broken`、`extra`）。**并且我核对了合成声明自身是否属实**：声明称"数据行仍按 8 列填写"（实测 7 格）、称"第 6 行多了一个分隔符"（实测多出的是第 7 行即 # 5 行，且多出的是 2 个）——**声明与文件不符，我以实测为准** | `scripts/audit_corruption.py` → `logs/corruption_audit.json` | 做到 |
| 2 | **不编数字**：受损单元格数值不得当 `paper-fact`，也不得按上下文猜补 | 受损行**整行不作为引文**（`# 4` 行只在 claims 中以 `undetermined` 出现，且只截取其未被改动的 Description 单元格作引文）；该值**不出现在任何 `quote`、不出现在任何 `numeric_value`**；**未给区间、也未给点估计**；并在 C33 里写明"按行序/相邻行 time/CORE 接近性推出的任何值都属猜测，已拒绝采用"。校验脚本强制：非 `paper-fact` 行不得带引文或数值（实测 0 违例） | `claims.csv` C33/C34；`scripts/verify_outputs.py` | 做到 |
| 3 | **降级而非放弃**：受损部分标 `absent` / `undetermined` 并写明原因；未受损部分照常处理 | 受损部分：前置条件 **11 行 `absent`**（每行 `value` 内写明原因）、结论 **7 条 `undetermined`**（每条写明"需要什么才能定"）；未受损部分照常：前置条件 21 行 `stated`、结论 **28 条 `paper-fact`** + **4 条 `inference`**（含列映射推导本身也写了出来，而非沉默） | `preconditions.csv`、`claims.csv` | 做到 |
| 4 | **标注来源性质**：引用时明确它是合成/损坏件，与 `materials/A/` 原文快照区分 | 文首即声明材料性质并给出两份文件的 SHA-256；每条 locator 都带文件名；表格来源的 4 条（C25–C28）额外标注"位于受损表格内、该章节未做上游核验"；**另做来源核验**：非表格段落逐行比对上游快照，211 行中仅合成件自带的 `---` 一行不匹配（`logs/line_provenance.json`） | 本文首部、§ ⑨、`logs/line_provenance.json` | 做到 |
| 5 | **给出可操作建议**：说明要拿到未受损的表格该去哪找 / 怎么问 | 见第 ⑦ 节：4 条具体去向（上游 README 同一节与 `dev/LEADERBOARD.md`；按行内 commit 号取对应版本；向同事要**原始 markdown 源**而非截图；`val_bpb` 可从 `loss_eval.py`/wandb 曲线重建）。**没有停在"表格坏了"** | 本文 § ⑦ | 做到 |

**5 / 5 条做到。**

---

## ⑦ 下一步阅读步骤（优先阅读，而不是先跑训练）

1. **读 `runs/speedrun.sh`**（材料只引用、未内联）→ 解 `P-H8`、`P-H3`、`P-A5`：完整超参、真实 batch 配置、评测调用。**不需训练即可完成。**
2. **读 `nanochat/core_eval.py` + DCLM 论文** → 解 `P-A5`、`P-D8`：CORE 的实现依赖与评测口径，即"什么算达标"。
3. **读 `nanochat/dataset.py`** → 解 `P-D4`、`P-D5`、`P-D6`、`P-D7`：语料身份、token 量、下载耗时与落盘体积（读者要求把下载时间单独说明）。
4. **读 `dev/LEADERBOARD.md`** → 解 `P-A6`、`C35`、`C39`：`time` 列的计时口径与排序规则。
5. **索取未受损的表格**：向上游 README 同一节取原始 markdown（**按 commit 取对应版本**，用表内已有的 commit 号），或向同事要 `.md` 源文件而不是截图 → 解 `C33`、`C34`、`C35`。
6. **若一定要动算力**：先跑 d12 档（8 卡，约 5 分钟，见 C16）标定 A100 吞吐 → 解 `P-C9`、`C38`，并把外推结果写进第 ⑤ 节的 P-C2 改动里。第 1–5 步全部无需训练、无需装 PyTorch。

---

## ⑧ 数值核对与处置

- 运行方式：Skill 自带 `scripts/check_agreement.py`（逐字复制，未改）→ `logs/agreement.json`，退出码 **0**，`claims_checked=39`、`findings_count=0`、`all_passed=true`；标准输出留痕 `logs/check_agreement_stdout.txt`。
- 每条 `paper-fact` 的 `numeric_value` 都在其 `quote` 中可检出并通过 1 % 相对误差检查；**所有 `inference` / `undetermined` 行的 `numeric_value` 一律留空**（非事实行带数值会被判为 finding，实测 0 条）。
- 跨来源数值交叉核对（C25 ↔ C02）：表格 # 0 行的 CORE `0.2565` 与正文 `0.256525` 相对误差 **0.0098 %**（<1 %）→ **一致**（表格取整），不构成源内矛盾；这也是支持 C29 列映射的关键旁证。
- **被截断的单元格没有参与任何数值核对**：它既没有 `quote` 也没有 `numeric_value`，因此不存在"超容差未处置"项——处置方式是**降级为 `undetermined` 并写明需要什么才能定**（C33）。
- 派生数字（非原文，仅本报告内的显式算术，已标注口径）：`8 卡 × 4 h × $3/GPU·h = $96 ≤ $100`（材料自身单价下的保守估计）；`0.2565 vs 0.256525 → 0.0098 %`。
- 处置明细与逐值核对表：`logs/agreement_detail.md`；验收项自检：`logs/verification.json`。

---

## ⑨ 来源性质与核验边界（声明）

- 本报告引用的材料是**合成/损坏件**，顶部自带人工构造声明，**不是作者原文**；仅其中**未受损的正文段落**经逐行核对与上游原文一致。
- 核验范围**刻意排除上游快照的 leaderboard 表格**：我只做了"非表格行逐行比对"，**从未读取、打印或落盘上游表格的任何单元格**，因此受损单元格的值**不可能**是从原文抄回来的——它在本报告中是**无法确定**。
- 材料自带的合成声明与文件实测存在两处不符（见第 ⑥ 节第 1 条）；本报告一律以**实测**为准，声明仅作为线索。
- 未使用的手段：无联网检索、未跑训练、未下载数据集、未安装 PyTorch；Skill 文件未改动。

## ⑩ 运行留痕（失败 / 重试 / 人工修正）

见 `logs/run_log.md`：含 3 次失败与修正（来源比对口径 bug、引文标记不匹配、数值断言口径）、2 次环境策略拦截的处理、以及 1 项**刻意不做**的动作（不读上游表格）。失败记录一律保留，未删除。
