#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate the paper-case deliverables from materials/source.txt.

Quotes are verified as contiguous substrings of materials/source.txt before any
file is written.  This script only writes the deliverable files; it does not
modify the frozen materials.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "materials" / "source.txt"

SOURCE_SHA256 = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
SOURCE_TEXT = SOURCE.read_text(encoding="utf-8")


def verify_quotes(quotes: dict[str, str]) -> None:
    missing = []
    for qid, quote in quotes.items():
        if quote not in SOURCE_TEXT:
            missing.append(qid)
    if missing:
        raise SystemExit(f"quote not contiguous in source: {missing}")
    print(f"verified {len(quotes)} quotes against {SOURCE.name} "
          f"(sha256={SOURCE_SHA256})")


QUOTES: dict[str, str] = {
    "F1": ("We propose Low-Rank Adaptation, or LoRA, which freezes the pre-\n"
           "trained model weights and injects trainable rank decomposition matrices into each\n"
           "layer of the Transformer architecture, greatly reducing the number of trainable pa-\n"
           "rameters for downstream tasks."),
    "F2": ("Compared to GPT-3 175B fine-tuned with Adam,\n"
           "LoRA can reduce the number of trainable parameters by 10,000 times and the\n"
           "GPU memory requirement by 3 times."),
    "F3a": ("On GPT-3 175B, we reduce the VRAM consumption during training from 1.2TB to\n"
            "350GB."),
    "F3b": ("For a large Transformer trained with Adam, we reduce that VRAM\n"
            "usage by up to 2/3 if r (cid:28) dmodel as we do not need to store the optimizer states for the frozen\n"
            "parameters."),
    "F4": ("With r = 4 and only the query and value projection matrices being adapted, the checkpoint\n"
           "size is reduced by roughly 10,000× (from 350GB to 35MB)4."),
    "F5": "|Θ| = 2 × ˆLLoRA × dmodel × r, where ˆLLoRA is the number of weight matrices we apply LoRA to.",
    "F6": "As mentioned in Section 4.2, we only apply LoRA to Wq and Wv in most experiments for simplicity.",
    "F7": ("During training, W0 is frozen and does not receive gradient updates, while A and B contain trainable\n"
           "parameters."),
    "F8": ("When deployed in production, we can explicitly compute and\n"
           "store W = W0 + BA and perform inference as usual."),
    "F9": ("we show that a very low rank (i.e., r in Figure 1 can be one or two) suffices even\n"
           "when the full rank (i.e., d) is as high as 12,288"),
    "F10a": ("We also observe a 25% speedup\n"
             "during training on GPT-3 175B compared to full fine-tuning5"),
    "F10b": ("For GPT-3 175B, the training throughput for full fine-tuning is 32.5 tokens/s per V100 GPU; with the same\n"
             "number of weight shards for model parallelism, the throughput is 43.1 tokens/s per V100 GPU for LoRA."),
    "F11": ("For all GPT-3 experiments, we train using AdamW (Loshchilov & Hutter, 2017) for 2 epochs with\n"
            "a batch size of 128 samples and a weight decay factor of 0.1. We use a sequence length of 384 for"),
    "F12": "WikiSQL (Zhong et al., 2017), 768 for MNLI (Williams et al., 2018), and 2048 for SAMSum (Gliwa",
    "F13": ("LoRA achieves better performance than fine-tuning on both\n"
            "MNLI-100 and MNLI-Full, and comparable results on MNLI-1k and MNLI-10K considering the\n"
            "(±0.3) variance due to random seeds."),
    "F14": "We use NVIDIA Tesla V100 for all experiments.",
}


PRECONDITIONS = [
    {"id": "P1", "category": "compute", "value": "24",
     "unit": "GB VRAM（1× RTX 4090；可选云卡预算 ≤ $200）",
     "source_locator": "cases/task-paper.md「你的约束」表-算力",
     "confidence": "high"},
    {"id": "P2", "category": "model", "value": "7,000,000,000",
     "unit": "parameters（7B 级；GPT-2 medium 量级至 7B 量级）",
     "source_locator": "cases/task-paper.md「你的约束」表-模型规模",
     "confidence": "high"},
    {"id": "P3", "category": "data", "value": "8000",
     "unit": "labeled English samples",
     "source_locator": "cases/task-paper.md「你的约束」表-数据",
     "confidence": "high"},
    {"id": "P4", "category": "objective", "value": "方法机制 + 24GB 单卡可行性判定（不要求复现 GPT-3 175B 数字）",
     "unit": "qualitative",
     "source_locator": "cases/task-paper.md「你的约束」表-目标/判定口径",
     "confidence": "high"},
    {"id": "A1", "category": "paper-evidence", "value": "",
     "unit": "",
     "source_locator": "absent: 论文没有 7B 级模型的 LoRA 显存/吞吐实测；实验模型只有 RoBERTa base/large、DeBERTa XXL(1.5B)、GPT-2 M/L(≤774M) 与 GPT-3 175B",
     "confidence": "absent"},
    {"id": "A2", "category": "paper-evidence", "value": "",
     "unit": "",
     "source_locator": "absent: 论文没有 8,000 样本的 LoRA-vs-全微调对比；低数据研究只用 MNLI-100/1k/10k",
     "confidence": "absent"},
    {"id": "A3", "category": "paper-evidence", "value": "",
     "unit": "",
     "source_locator": "absent: 论文没有 RTX 4090/24GB 单卡显存实测；硬件只有 NVIDIA Tesla V100 与 Quadro RTX8000",
     "confidence": "absent"},
]


CLAIMS = [
    # --- paper-fact ---
    {"claim_id": "F1",
     "claim_text": "LoRA 冻结预训练权重、注入可训练的低秩分解矩阵，从而大幅减少下游任务的可训练参数。",
     "classification": "paper-fact", "locator": "PAGE 1 (Abstract)",
     "quote": "F1", "numeric_value": "",
     "dependency_preconditions": "", "reasoning": "方法机制的直接陈述，原文无数字。",
     "confidence": "high"},
    {"claim_id": "F2",
     "claim_text": "相比用 Adam 全微调 GPT-3 175B，LoRA 把可训练参数量减少 10,000 倍、GPU 显存需求降低 3 倍（摘要口径）。",
     "classification": "paper-fact", "locator": "PAGE 1 (Abstract)",
     "quote": "F2", "numeric_value": "10000",
     "dependency_preconditions": "", "reasoning": "10,000 倍为摘要口径；3 倍与正文 1.2TB→350GB（≈3.4×）存在舍入口径差异，见 F3a/U4 说明。",
     "confidence": "high"},
    {"claim_id": "F3a",
     "claim_text": "GPT-3 175B 上，LoRA 把训练期显存占用从 1.2TB 降到 350GB。",
     "classification": "paper-fact", "locator": "PAGE 5 §4.2",
     "quote": "F3a", "numeric_value": "350",
     "dependency_preconditions": "", "reasoning": "350GB/175B=2 字节/参数，是下文 7B 冻结权重 14GB 的锚点。",
     "confidence": "high"},
    {"claim_id": "F3b",
     "claim_text": "对用 Adam 训练的大 Transformer，LoRA 最多把 VRAM 占用降低 2/3（约降到 1/3），因为冻结参数不需要保存优化器状态。",
     "classification": "paper-fact", "locator": "PAGE 5 §4.2",
     "quote": "F3b", "numeric_value": "",
     "dependency_preconditions": "", "reasoning": "分数 2/3 不作 numeric_value（避免自检把 2、3 拆开误判），数字见引文。",
     "confidence": "high"},
    {"claim_id": "F4",
     "claim_text": "r=4 且只适配 query/value 投影时，checkpoint 从 350GB 降到 35MB，约 10,000 倍。",
     "classification": "paper-fact", "locator": "PAGE 5 §4.2",
     "quote": "F4", "numeric_value": "10000",
     "dependency_preconditions": "", "reasoning": "350GB/35MB=10,000，与引文中 10,000× 一致。",
     "confidence": "high"},
    {"claim_id": "F5",
     "claim_text": "LoRA 可训练参数量公式：|Θ| = 2 × L̂_LoRA × d_model × r。",
     "classification": "paper-fact", "locator": "PAGE 6 §5.1",
     "quote": "F5", "numeric_value": "",
     "dependency_preconditions": "", "reasoning": "公式本身不填 numeric_value；是 I2 换算的核心依据。",
     "confidence": "high"},
    {"claim_id": "F6",
     "claim_text": "论文大多数实验只对 Wq 与 Wv 应用 LoRA。",
     "classification": "paper-fact", "locator": "PAGE 6 §5.1",
     "quote": "F6", "numeric_value": "",
     "dependency_preconditions": "", "reasoning": "",
     "confidence": "high"},
    {"claim_id": "F7",
     "claim_text": "训练时 W0 冻结、不收梯度，A 与 B 是可训练参数。",
     "classification": "paper-fact", "locator": "PAGE 4 §4.1",
     "quote": "F7", "numeric_value": "",
     "dependency_preconditions": "", "reasoning": "",
     "confidence": "high"},
    {"claim_id": "F8",
     "claim_text": "部署时把 LoRA 权重合并为 W = W0 + BA，推理与全微调模型相比不增加延迟。",
     "classification": "paper-fact", "locator": "PAGE 4 §4.1",
     "quote": "F8", "numeric_value": "",
     "dependency_preconditions": "", "reasoning": "",
     "confidence": "high"},
    {"claim_id": "F9",
     "claim_text": "GPT-3 175B 上低秩 r 取 1 或 2 已足够，即使满秩 d 高达 12,288。",
     "classification": "paper-fact", "locator": "PAGE 2 §1",
     "quote": "F9", "numeric_value": "12288",
     "dependency_preconditions": "", "reasoning": "12,288 是 GPT-3 的 hidden 维度，支撑 7B 上小 r 也大概率够用的类比。",
     "confidence": "high"},
    {"claim_id": "F10a",
     "claim_text": "论文正文称 GPT-3 175B 训练比全微调快 25%（注意与脚注吞吐不一致，见 U4）。",
     "classification": "paper-fact", "locator": "PAGE 5 §4.2",
     "quote": "F10a", "numeric_value": "25",
     "dependency_preconditions": "", "reasoning": "25% 与脚注 43.1/32.5≈+32.6% 对不上，两处都保留为原文。",
     "confidence": "high"},
    {"claim_id": "F10b",
     "claim_text": "脚注：GPT-3 175B 全微调吞吐 32.5 tokens/s/V100，LoRA 为 43.1 tokens/s/V100。",
     "classification": "paper-fact", "locator": "PAGE 5 §4.2 footnote 5",
     "quote": "F10b", "numeric_value": "43.1",
     "dependency_preconditions": "", "reasoning": "43.1/32.5≈1.326，即 +32.6%；与正文 25% 不一致（U4）。",
     "confidence": "high"},
    {"claim_id": "F11",
     "claim_text": "GPT-3 实验统一用 AdamW、2 epochs、batch size 128、weight decay 0.1；WikiSQL 序列长度 384。",
     "classification": "paper-fact", "locator": "PAGE 19 §D.4",
     "quote": "F11", "numeric_value": "128",
     "dependency_preconditions": "", "reasoning": "batch 128 是多卡设定；7B 单卡需减小 batch，见 I2。",
     "confidence": "high"},
    {"claim_id": "F12",
     "claim_text": "GPT-3 各任务序列长度：MNLI 768、SAMSum 2048（WikiSQL 的 384 见 PAGE 19）。",
     "classification": "paper-fact", "locator": "PAGE 20 §D.4",
     "quote": "F12", "numeric_value": "2048",
     "dependency_preconditions": "", "reasoning": "序列长度影响激活显存；7B 上需按此缩 batch/开检查点，见 I2。",
     "confidence": "high"},
    {"claim_id": "F13",
     "claim_text": "GPT-3 175B 低数据实验：LoRA 在 MNLI-100 与 MNLI-Full 优于全微调，在 MNLI-1k 与 MNLI-10K 与全微调相当。",
     "classification": "paper-fact", "locator": "PAGE 22 §F.3",
     "quote": "F13", "numeric_value": "",
     "dependency_preconditions": "", "reasoning": "8,000 样本落在 1k 与 10k 之间，见 I3。",
     "confidence": "high"},
    {"claim_id": "F14",
     "claim_text": "论文所有实验使用 NVIDIA Tesla V100。",
     "classification": "paper-fact", "locator": "PAGE 5 §5",
     "quote": "F14", "numeric_value": "",
     "dependency_preconditions": "", "reasoning": "硬件口径为 V100/Quadro RTX8000，无 RTX 4090，见 A3。",
     "confidence": "high"},

    # --- inference ---
    {"claim_id": "I1",
     "claim_text": "7B 模型全微调（Adam/AdamW 混合精度）在 24 GB 单卡上装不下（尚未计入激活）。",
     "classification": "inference", "locator": "",
     "quote": "", "numeric_value": "",
     "dependency_preconditions": "P1;P2",
     "reasoning": ("算式（非论文声明）：Memory_full ≈ P×(2+2+8) 字节/参数，P=7×10^9。"
                  "2=权重 fp16、2=梯度 fp16、8=AdamW 的 fp32 m/v 两矩（假设，不含 fp32 master 权重与激活）。"
                  "得 7e9×12=84 GB（>24 GB）；若再加 fp32 master 权重 4B/参数则 112 GB。"
                  "交叉验证（论文锚点）：175B 全微调 1.2TB ⇒ 1.2e12/175e9≈6.9 B/参数（PAGE 5），同比例 7e9×6.9≈48 GB，仍 >24 GB。"
                  "参数来源：2/2/8 字节为标准 AdamW 混合精度假设；6.9 B/参数由论文 1.2TB/175B 导出。假设：7B=7×10^9 参数的 dense decoder-only 模型。"),
     "confidence": "medium"},
    {"claim_id": "I2",
     "claim_text": "7B 模型 LoRA 微调（冻结 fp16 权重 + r=8 适配 Wq/Wv）的静态显存约 14 GB + 可忽略的优化器状态，24 GB 单卡有条件可行，但必须用 bf16/fp16、梯度检查点、小 batch 并实测激活峰值。",
     "classification": "inference", "locator": "",
     "quote": "", "numeric_value": "",
     "dependency_preconditions": "P1;P2",
     "reasoning": ("算式（非论文声明）：Memory_LoRA ≈ P×2（冻结 fp16 权重）+ |Θ|×(2+2+8)（可训练参数的梯度+Adam 状态）+ 激活。"
                  "|Θ|=2×L̂_LoRA×d_model×r（论文公式，PAGE 6）。取 L̂_LoRA=2×32=64（Wq+Wv，32 层）、d_model=4096、r=8："
                  "|Θ|=2×64×4096×8=4,194,304≈4.2M（假设 32 层/4096 是 7B dense 模型典型配置，非论文数值）。"
                  "冻结权重=7e9×2=14 GB（锚点：论文 350GB/175B=2 B/参数，PAGE 5）。可训练部分=4.19e6×12≈50 MB≈0.05 GB。"
                  "剩给激活≈24−14−0.05≈9.9 GB；能否装下取决于 batch/序列长度/是否梯度检查点（论文未给 7B 激活值，需实测）。"
                  "假设：bf16/fp16、梯度检查点、batch≤4、序列长度按需≤2048 并实测。"),
     "confidence": "medium"},
    {"claim_id": "I3",
     "claim_text": "用户 8,000 条英文样本落在论文 MNLI-1k 与 MNLI-10k 之间，LoRA 与全微调质量相当的结论可外推为「够用」，但论文只在 GPT-3 175B/MNLI 上验证过。",
     "classification": "inference", "locator": "",
     "quote": "", "numeric_value": "",
     "dependency_preconditions": "P3",
     "reasoning": ("8,000 在 1,000 与 10,000 之间；论文 F13（PAGE 22）显示该区间 LoRA 与全微调相当，但那是 GPT-3 175B 的 MNLI，"
                  "不是 7B 或用户自有任务。外推是推断，需在 7B 上小规模验证。"),
     "confidence": "medium"},
    {"claim_id": "I4",
     "claim_text": "论文的 3 倍显存节省是相对 GPT-3 175B 全微调；迁移到 7B 时节省比例会因激活占比不同而变化，不能直接套用 3 倍。",
     "classification": "inference", "locator": "",
     "quote": "", "numeric_value": "",
     "dependency_preconditions": "P1;P2",
     "reasoning": ("论文 1.2TB→350GB 的 3.4× 缩减主体是「消除冻结参数的优化器状态」（PAGE 5）。7B 的优化器状态占比与 175B 不同，"
                  "且激活显存占比随 batch/序列长度变化，因此 3× 不能直接搬用到 24GB 场景，须按 I2 公式重算。"),
     "confidence": "medium"},

    # --- undetermined ---
    {"claim_id": "U1",
     "claim_text": "Table 3 中 GPT-2 medium/large 的可训练参数量（354.92M / 774.03M）无法从压平的抽取文本可靠确定行列归属。",
     "classification": "undetermined", "locator": "",
     "quote": "", "numeric_value": "",
     "dependency_preconditions": "",
     "reasoning": ("source_manifest 明示表格被压平为单元格序列、行列身份不保留；Table 3 片段中数字与 Method 行交错出现，"
                  "无法可靠判定 354.92M/774.03M 属于哪一行哪一列，故不按出现顺序猜测、降级。"
                  "需要回原始 PDF 重新排版解析或查论文 LaTeX 源才能定。"),
     "confidence": "low"},
    {"claim_id": "U2",
     "claim_text": "Table 4 中 GPT-3 各方法的可训练参数量/准确率（如 4.7M、37.7M、73.4 等）无法从压平文本可靠归行归列。",
     "classification": "undetermined", "locator": "",
     "quote": "", "numeric_value": "",
     "dependency_preconditions": "",
     "reasoning": ("Table 4 同为压平单元格序列，行列身份丢失；引用其中任何单个数字都无法证明它对应哪一行哪一列，故不猜、降级。"
                  "需要原始 PDF/LaTeX 源或重新排版抽取才能确定。"),
     "confidence": "low"},
    {"claim_id": "U3",
     "claim_text": "7B 模型在 24 GB 单卡 LoRA 微调时的激活显存峰值，论文未给出。",
     "classification": "undetermined", "locator": "",
     "quote": "", "numeric_value": "",
     "dependency_preconditions": "P1;P2",
     "reasoning": ("论文只给 GPT-3 175B 总显存（1.2TB→350GB，PAGE 5）与 V100/Quadro RTX8000 硬件，没有 7B 激活显存或 24GB 单卡实测。"
                  "需要：在 RTX 4090 上实测，或用 PyTorch memory snapshot / transformers 的显存 profiler 量化激活峰值。"),
     "confidence": "low"},
    {"claim_id": "U4",
     "claim_text": "论文正文的 25% 加速与脚注吞吐 43.1/32.5 ≈ +32.6% 不一致，无法确定最终口径。",
     "classification": "undetermined", "locator": "",
     "quote": "", "numeric_value": "",
     "dependency_preconditions": "",
     "reasoning": ("正文 25%（F10a，PAGE 5）与脚注 32.5→43.1 tokens/s（F10b，PAGE 5）即 43.1/32.5≈1.326（+32.6%）对不上。"
                  "保留两处原文、不抹平；需要作者澄清或按 32.5/43.1 重算才算定。"),
     "confidence": "low"},
]


def build() -> None:
    verify_quotes(QUOTES)

    # preconditions.csv
    pre_path = ROOT / "preconditions.csv"
    with pre_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "id", "category", "value", "unit", "source_locator", "confidence"])
        writer.writeheader()
        for row in PRECONDITIONS:
            writer.writerow(row)

    # claims.csv
    claims_path = ROOT / "claims.csv"
    with claims_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "claim_id", "claim_text", "classification", "locator", "quote",
            "numeric_value", "dependency_preconditions", "reasoning", "confidence"])
        writer.writeheader()
        for row in CLAIMS:
            out = dict(row)
            if out["classification"] == "paper-fact":
                out["quote"] = QUOTES[out["quote"]]
            else:
                out["quote"] = ""
                out["numeric_value"] = ""
            writer.writerow(out)

    # evidence_index.json
    evidence = []
    for qid, quote in QUOTES.items():
        locator = next(
            (c["locator"] for c in CLAIMS if c["claim_id"] == qid), "")
        evidence.append({
            "id": qid,
            "kind": "paper-fact-quote",
            "locator": locator,
            "quote": quote,
            "sha256": SOURCE_SHA256,
        })
    (ROOT / "evidence_index.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    print("wrote preconditions.csv, claims.csv, evidence_index.json")
    print("source sha256:", SOURCE_SHA256)


if __name__ == "__main__":
    build()
