# 迁移判定：LoRA 论文 → 「24 GB 单卡 + 7B + 8,000 条样本」

## 1. Verdict

**transferable-with-changes**

LoRA 的机制（冻结底座权重、只训练低秩 A/B，可合并进 W 以消除推理延迟）与 7B 级微调场景兼容；但论文没有任何 7B / 24 GB 单卡实测，落地必须改为 fp16/bf16 + 梯度检查点 + 小 batch 并实测激活峰值，因此不能原样照搬。

## 2. What is established

以下均为论文直接陈述（`paper-fact`，引文与定位见 claims.csv / evidence_index.json）：

- LoRA 冻结预训练权重、注入可训练的低秩分解矩阵（PAGE 1，Abstract）。
- 相比用 Adam 全微调 GPT-3 175B，可训练参数量减少 10,000 倍、GPU 显存需求降低 3 倍（PAGE 1，Abstract 口径）。
- GPT-3 175B 训练显存从 1.2 TB 降到 350 GB（PAGE 5 §4.2）；对用 Adam 的大 Transformer 最多省 2/3 VRAM，因为冻结参数不需保存优化器状态（PAGE 5 §4.2）。
- r=4 且只适配 query/value 时，checkpoint 从 350 GB 降到 35 MB，约 10,000 倍（PAGE 5 §4.2）。
- 可训练参数量公式 |Θ| = 2 × L̂_LoRA × d_model × r（PAGE 6 §5.1）；大多数实验只对 Wq、Wv 应用 LoRA（PAGE 6 §5.1）。
- 训练时 W0 冻结不收梯度，A、B 可训练（PAGE 4 §4.1）；部署时合并 W = W0 + BA，不增加推理延迟（PAGE 4 §4.1）。
- GPT-3 175B 上低秩 r=1 或 2 已足够，即使满秩 d 高达 12,288（PAGE 2 §1）。
- 正文称训练比全微调快 25%（PAGE 5 §4.2）；脚注给出吞吐 32.5 → 43.1 tokens/s/V100（PAGE 5 footnote 5）。
- GPT-3 实验用 AdamW、2 epochs、batch 128、weight decay 0.1，序列长度 WikiSQL 384 / MNLI 768 / SAMSum 2048（PAGE 19-20 §D.4）。
- 低数据实验：LoRA 在 MNLI-100 与 MNLI-Full 优于全微调，在 MNLI-1k 与 MNLI-10K 与全微调相当（PAGE 22 §F.3）。
- 论文所有实验使用 NVIDIA Tesla V100（PAGE 5 §5）。

## 3. What I inferred

以下是我的推导，**不是论文说的**（`inference`，完整算式在 claims.csv 的 reasoning 列）：

- **7B 全微调装不进 24 GB**：Memory_full ≈ P × (2+2+8) 字节/参数 = 7×10^9 × 12 = 84 GB（fp16 权重 2 + fp16 梯度 2 + AdamW fp32 m/v 8，未计激活）；用论文锚点 1.2 TB/175B ≈ 6.9 B/参数 也得 ≈48 GB，都 > 24 GB。
- **7B LoRA 有条件可行**：Memory_LoRA ≈ 冻结 fp16 权重 14 GB（7×10^9×2，锚点=350 GB/175 B=2 B/参数）+ 可训练部分 ≈4.2 M 参数（|Θ|=2×64×4096×8，取 Wq+Wv、32 层、d_model=4096、r=8）的梯度+Adam 状态 ≈0.05 GB + 激活。24 GB 内可行与否取决于激活（约剩 9.9 GB），必须 bf16/fp16 + 梯度检查点 + 小 batch 并实测。
- **8,000 条样本够用（外推）**：8,000 落在论文 MNLI-1k 与 MNLI-10k 之间，该区间 LoRA 与全微调相当；但论文是 GPT-3 175B/MNLI，迁移到 7B 与自有任务需小规模验证。
- **3 倍显存节省不能直接套用**：它是相对 175B 全微调、主要来自消除冻结参数的优化器状态；7B 上优化器占比与激活占比不同，须按上面公式重算。

## 4. What remains open

`undetermined` 与 `absent` 前置条件（对应 claims.csv U1-U4、preconditions.csv A1-A3）：

- **表格数字无法归行归列**：Table 3 的 354.92M / 774.03M、Table 4 的 4.7M / 37.7M / 准确率等，抽取文本是压平单元格序列、行列身份不保留，无法证明某数字属于哪行哪列，故不按出现顺序猜、降级。需要原始 PDF 重排解析或 LaTeX 源。
- **7B 激活显存峰值未给出**：论文只有 GPT-3 175B 总显存与 V100/Quadro RTX8000 硬件，没有 7B / 24 GB 实测。需要在 RTX 4090 上实测，或用 PyTorch memory snapshot 等 profiler 量化。
- **论文自身不一致**：正文「25% speedup」与脚注 32.5 → 43.1 tokens/s（43.1/32.5 ≈ +32.6%）对不上；两处都保留、不抹平，需要作者澄清。另摘要「3 倍显存」与 1.2 TB→350 GB（≈3.4×）是舍入口径差异。
- **缺少的 7B 直接证据**：论文实验模型为 RoBERTa/DeBERTa/GPT-2（≤1.5B）与 GPT-3 175B，无 7B 级模型；也无数千样本（8k）的专门对比，且无 RTX 4090。这些都需要外部报告或实测补足。

## 预期行为对照

1. **事实与推断分开**：做到。16 条 `paper-fact` 全部带定位与逐字引文；4 条换算/外推全部标 `inference`，reasoning 写算式，未冒充论文声明。
2. **数字可回算**：做到。每条 `paper-fact` 给 PAGE 定位；发现「25% vs 32.6%」不一致，如实写进第 4 节并保留两处原文。
3. **换算给算式**：做到。I1/I2 给出显存公式、参数来源（2/2/8 字节假设、350 GB/175 B=2 B/参数锚点、论文 |Θ| 公式）与假设（32 层/4096/r=8、bf16、梯度检查点、小 batch）。
4. **表格数字说明行列身份**：做到。Table 3/Table 4 数字因行列身份丢失主动降级为 `undetermined`（U1/U2），未按出现顺序猜测。
5. **可操作建议**：做到。落地需 bf16/fp16、梯度检查点、小 batch、r=8 Wq/Wv、先小规模验证 8k 数据；去哪查：原始 PDF/LaTeX 源核对表格、PyTorch/transformers 显存 profiler、外部 7B LoRA 实测。本文不能保证 7B 激活峰值、RTX 4096 上实际吞吐、以及用户自有任务上的质量。
