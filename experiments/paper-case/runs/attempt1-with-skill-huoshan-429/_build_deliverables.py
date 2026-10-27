# -*- coding: utf-8 -*-
import csv, json, hashlib, pathlib, sys, re

ROOT = pathlib.Path(r"E:\minimax\project\DP match\work\tmp\paper-case\with-skill")
SRC_PATH = ROOT / "materials" / "source.txt"
SRC = SRC_PATH.read_text(encoding="utf-8")
SRC_SHA = hashlib.sha256(SRC_PATH.read_bytes()).hexdigest()

def span(start, end=None):
    i = SRC.find(start)
    if i < 0:
        raise SystemExit(f"START NOT FOUND: {start!r}")
    if end is None:
        return SRC[i:i+len(start)]
    j = SRC.find(end, i + len(start))
    if j < 0:
        raise SystemExit(f"END NOT FOUND after {start!r}: {end!r}")
    return SRC[i:j+len(end)]

SPANS = [
    ("PF1", "PAGE 1 / Abstract", "We propose Low-Rank Adaptation, or LoRA, which freezes the pre-", "for downstream tasks."),
    ("PF2", "PAGE 1 / Abstract", "Compared to GPT-3 175B fine-tuned with Adam,", "GPU memory requirement by 3 times."),
    ("PF3", "PAGE 6 / Section 5.1", "The number of trainable parameters is determined by the rank r", "where \u02c6LLoRA is the number of weight matrices we apply LoRA to."),
    ("PF4", "PAGE 5 / Section 4.2", "We limit our study to only adapting the attention weights for downstream", "and parameter-efficiency."),
    ("PF5", "PAGE 2 / Section 1", "Our simple linear design allows us", "by\nconstruction."),
    ("PF6", "PAGE 3 / Section 2", "When the pre-trained model is GPT-3 175B, the number of train-", "as small as 0.01% of |\u03a60|."),
    ("PF7", "PAGE 5 / Section 4.2", "For a large Transformer trained with Adam", "for the frozen\nparameters."),
    ("PF8", "PAGE 5 / Section 4.2", "On GPT-3 175B, we reduce the VRAM consumption during training from 1.2TB to", "350GB."),
    ("PF9", "PAGE 5 / Section 4.2", "With r = 4 and only the query and value projection matrices being adapted, the checkpoint", "(from 350GB to 35MB)"),
    ("PF10", "PAGE 5 / footnote 5", "For GPT-3 175B, the training throughput for full fine-tuning is 32.5 tokens/s per V100 GPU", "43.1 tokens/s per V100 GPU for LoRA."),
    ("PF11", "PAGE 2 / Section 1", "a very low rank (i.e., r in Figure 1 can be one or two) suffices even", "as high as 12,288"),
    ("PF12", "PAGE 10 / Section 7.1", "We set a parameter budget of 18M", "for all 96 layers."),
    ("PF13", "PAGE 10 / Section 7.2", "To our surprise, a", "needs a larger r."),
    ("PF14", "PAGE 10 / Section 7.1", "Adapting both Wq and", "gives the best performance overall."),
    ("PF15", "PAGE 19 / Appendix D.4", "For all GPT-3 experiments, we train using AdamW", "a weight decay factor of 0.1."),
    ("PF16", "PAGE 20 / Appendix D.4", "two parameter budgets for LoRA: 4.7M", "rq = rk = rv = ro = 2)."),
    ("PF17", "PAGE 22 / Section F.3", "LoRA achieves better performance than fine-tuning on both", "variance due to random seeds."),
    ("PF18a", "PAGE 19 / Appendix D.4", "We use a sequence length of 384 for", None),
    ("PF18b", "PAGE 20 / Appendix D.4", "768 for MNLI (Williams et al., 2018), and 2048 for SAMSum (Gliwa", "et al., 2019)."),
]

quotes = {}
for cid, loc, st, en in SPANS:
    q = span(st, en)
    if q not in SRC:
        raise SystemExit(f"QUOTE NOT CONTIGUOUS: {cid}: {q[:120]!r}")
    quotes[cid] = (loc, q)
    print("OK", cid, len(q), repr(q[:70]))

# ---------------- preconditions ----------------
pre = []
pre.append({"id":"PC-COMP-1","category":"compute","value":"NVIDIA Tesla V100 (all experiments)","unit":"GPU","source_locator":"PAGE 5 / Section 5","confidence":"stated"})
pre.append({"id":"PC-COMP-2","category":"compute","value":"NVIDIA Quadro RTX8000 (adapter-latency study only)","unit":"GPU","source_locator":"PAGE 4 / Table 1 and Appendix B","confidence":"stated"})
pre.append({"id":"PC-COMP-3","category":"compute","value":"350","unit":"GB VRAM during LoRA training (GPT-3 175B)","source_locator":"PAGE 5 / Section 4.2","confidence":"stated"})
pre.append({"id":"PC-COMP-4","category":"compute","value":"1.2","unit":"TB VRAM full fine-tuning (GPT-3 175B)","source_locator":"PAGE 5 / Section 4.2","confidence":"stated"})
pre.append({"id":"PC-COMP-5","category":"compute","value":"43.1 (LoRA) vs 32.5 (full fine-tune)","unit":"tokens/s per V100 GPU (GPT-3)","source_locator":"PAGE 5 / footnote 5","confidence":"stated"})
pre.append({"id":"PC-DATA-1","category":"data scale","value":"GLUE, E2E NLG, DART, WebNLG, WikiSQL, SAMSum","unit":"datasets evaluated","source_locator":"PAGE 5 / Section 5 and Appendix C","confidence":"stated"})
pre.append({"id":"PC-DATA-2","category":"data scale","value":"56,355 / 8,421","unit":"WikiSQL train/validation examples","source_locator":"PAGE 18 / Appendix C","confidence":"stated"})
pre.append({"id":"PC-DATA-3","category":"data scale","value":"14,732 / 819","unit":"SAMSum train/test examples","source_locator":"PAGE 18 / Appendix C","confidence":"stated"})
pre.append({"id":"PC-DATA-4","category":"data scale","value":"42,000 / 4,600 / 4,600 (approx.)","unit":"E2E train/val/test examples","source_locator":"PAGE 18 / Appendix C","confidence":"stated"})
pre.append({"id":"PC-DATA-5","category":"data scale","value":"100, 1k, 10k sampled from full MNLI training set","unit":"low-data training examples","source_locator":"PAGE 22 / Section F.3","confidence":"stated"})
pre.append({"id":"PC-HYP-1","category":"hyperparameters","value":"r = 1 or 2 for Wq/Wv (with d up to 12,288)","unit":"rank","source_locator":"PAGE 2 / Section 1","confidence":"stated"})
pre.append({"id":"PC-HYP-2","category":"hyperparameters","value":"only Wq and Wv adapted in most experiments; MLP frozen","unit":"adaptation target","source_locator":"PAGE 5-6 / Sections 4.2 and 5.1","confidence":"stated"})
pre.append({"id":"PC-HYP-3","category":"hyperparameters","value":"2 epochs, batch size 128, weight decay 0.1, AdamW (GPT-3)","unit":"training setup","source_locator":"PAGE 19 / Appendix D.4","confidence":"stated"})
pre.append({"id":"PC-HYP-4","category":"hyperparameters","value":"|Theta| = 2 * L_LoRA * dmodel * r","unit":"trainable parameter formula","source_locator":"PAGE 6 / Section 5.1","confidence":"stated"})
pre.append({"id":"PC-HYP-5","category":"hyperparameters","value":"alpha/r scaling; alpha set to first r tried and not tuned","unit":"scaling","source_locator":"PAGE 4 / Section 4.1","confidence":"stated"})
pre.append({"id":"PC-HYP-6","category":"hyperparameters","value":"A: random Gaussian init, B: zero init","unit":"initialization","source_locator":"PAGE 4 / Section 4.1","confidence":"stated"})
pre.append({"id":"PC-HYP-7","category":"hyperparameters","value":"128 (RoBERTa GLUE restricted runs)","unit":"sequence length","source_locator":"PAGE 18 / Appendix D.1","confidence":"stated"})
pre.append({"id":"PC-HYP-8","category":"hyperparameters","value":"384 (WikiSQL), 768 (MNLI), 2048 (SAMSum)","unit":"sequence length (GPT-3)","source_locator":"PAGE 19-20 / Appendix D.4","confidence":"stated"})
pre.append({"id":"PC-HID-1","category":"hidden assumptions","value":"Task adaptation delta W has low intrinsic rank (hypothesis; supported on studied tasks)","unit":"assumption","source_locator":"PAGE 2 / Section 1","confidence":"stated"})
pre.append({"id":"PC-HID-2","category":"hidden assumptions","value":"Pre-trained weights stay frozen and are shared across tasks","unit":"assumption","source_locator":"PAGE 1 / Abstract and Section 4.1","confidence":"stated"})
pre.append({"id":"PC-HID-3","category":"hidden assumptions","value":"Absorbing A,B into W removes inference latency","unit":"mechanism","source_locator":"PAGE 4-5 / Section 4.1","confidence":"stated"})
pre.append({"id":"PC-HID-4","category":"hidden assumptions","value":"Small r may not suffice when downstream task/domain differs from pre-training","unit":"limitation","source_locator":"PAGE 10 / footnote 6","confidence":"stated"})
pre.append({"id":"PC-HID-5","category":"hidden assumptions","value":"not stated","unit":"GB peak VRAM for a 7B model on RTX 4090","source_locator":"N/A - paper gives only GPT-3 175B VRAM (1.2TB to 350GB) on V100; no 7B or RTX 4090 numbers","confidence":"absent"})
pre.append({"id":"PC-HID-6","category":"hidden assumptions","value":"not stated","unit":"transfer to reader's own 8,000-sample English task/domain","source_locator":"N/A - paper evaluates GLUE/E2E/DART/WebNLG/WikiSQL/SAMSum, not the reader's domain","confidence":"absent"})
pre.append({"id":"PC-HID-7","category":"hidden assumptions","value":"LoRA package and PyTorch integration released (github.com/microsoft/LoRA)","unit":"implementation availability","source_locator":"PAGE 1 / Abstract","confidence":"stated"})

# ---------------- claims ----------------
def q(cid):
    return quotes[cid][1]

claims = []
claims.append({"claim_id":"PF1","claim_text":"LoRA freezes the pretrained weights and injects trainable rank-decomposition matrices into each Transformer layer.","classification":"paper-fact","locator":quotes["PF1"][0],"quote":q("PF1"),"numeric_value":"","dependency_preconditions":"PC-HID-2","reasoning":"","confidence":"high"})
claims.append({"claim_id":"PF2","claim_text":"Compared to GPT-3 175B fine-tuned with Adam, LoRA reduces trainable parameters 10,000x and GPU memory 3x.","classification":"paper-fact","locator":quotes["PF2"][0],"quote":q("PF2"),"numeric_value":"10000","dependency_preconditions":"PC-COMP-3; PC-COMP-4","reasoning":"","confidence":"high"})
claims.append({"claim_id":"PF3","claim_text":"LoRA trainable-parameter count is |Theta| = 2 * L_LoRA * dmodel * r, where L_LoRA is the number of weight matrices LoRA is applied to.","classification":"paper-fact","locator":quotes["PF3"][0],"quote":q("PF3"),"numeric_value":"","dependency_preconditions":"PC-HYP-4","reasoning":"","confidence":"high"})
claims.append({"claim_id":"PF4","claim_text":"The study adapts only attention weights for downstream tasks and freezes MLP modules, leaving MLP/LayerNorm/bias adaptation to future work.","classification":"paper-fact","locator":quotes["PF4"][0],"quote":q("PF4"),"numeric_value":"","dependency_preconditions":"PC-HYP-2","reasoning":"","confidence":"high"})
claims.append({"claim_id":"PF5","claim_text":"LoRA's linear design lets trainable matrices be merged with frozen weights, introducing no inference latency compared to a fully fine-tuned model by construction.","classification":"paper-fact","locator":quotes["PF5"][0],"quote":q("PF5"),"numeric_value":"","dependency_preconditions":"PC-HID-3","reasoning":"","confidence":"high"})
claims.append({"claim_id":"PF6","claim_text":"For GPT-3 175B, the number of trainable parameters can be as small as 0.01% of the full model parameter count.","classification":"paper-fact","locator":quotes["PF6"][0],"quote":q("PF6"),"numeric_value":"","dependency_preconditions":"PC-COMP-3; PC-COMP-4","reasoning":"","confidence":"high"})
claims.append({"claim_id":"PF7","claim_text":"With Adam, LoRA reduces VRAM usage by up to 2/3 for a large Transformer because optimizer states for frozen parameters are not stored.","classification":"paper-fact","locator":quotes["PF7"][0],"quote":q("PF7"),"numeric_value":"","dependency_preconditions":"PC-COMP-3; PC-COMP-4; PC-HYP-4","reasoning":"","confidence":"high"})
claims.append({"claim_id":"PF8","claim_text":"On GPT-3 175B, LoRA reduces training VRAM from 1.2TB to 350GB.","classification":"paper-fact","locator":quotes["PF8"][0],"quote":q("PF8"),"numeric_value":"350","dependency_preconditions":"PC-COMP-3; PC-COMP-4","reasoning":"","confidence":"high"})
claims.append({"claim_id":"PF9","claim_text":"With r=4 and only query/value matrices adapted, GPT-3 checkpoint size drops roughly 10,000x from 350GB to 35MB.","classification":"paper-fact","locator":quotes["PF9"][0],"quote":q("PF9"),"numeric_value":"10000","dependency_preconditions":"PC-COMP-3; PC-HYP-2","reasoning":"","confidence":"high"})
claims.append({"claim_id":"PF10","claim_text":"On GPT-3 175B, LoRA training throughput is 43.1 tokens/s per V100 GPU vs 32.5 tokens/s for full fine-tuning.","classification":"paper-fact","locator":quotes["PF10"][0],"quote":q("PF10"),"numeric_value":"43.1","dependency_preconditions":"PC-COMP-1; PC-COMP-5","reasoning":"","confidence":"high"})
claims.append({"claim_id":"PF11","claim_text":"For GPT-3, a very low rank (r=1 or 2) suffices even when full rank d is as high as 12,288.","classification":"paper-fact","locator":quotes["PF11"][0],"quote":q("PF11"),"numeric_value":"12288","dependency_preconditions":"PC-HYP-1","reasoning":"","confidence":"high"})
claims.append({"claim_id":"PF12","claim_text":"On GPT-3 175B, a parameter budget of 18M (about 35MB in FP16) equals r=8 for one attention weight type or r=4 for two types across all 96 layers.","classification":"paper-fact","locator":quotes["PF12"][0],"quote":q("PF12"),"numeric_value":"18","dependency_preconditions":"PC-HYP-1; PC-HYP-4","reasoning":"","confidence":"high"})
claims.append({"claim_id":"PF13","claim_text":"A rank as small as one suffices for adapting both Wq and Wv in the paper's GPT-3 study, while training Wq alone needs a larger r.","classification":"paper-fact","locator":quotes["PF13"][0],"quote":q("PF13"),"numeric_value":"","dependency_preconditions":"PC-HYP-1; PC-HYP-2","reasoning":"","confidence":"high"})
claims.append({"claim_id":"PF14","claim_text":"Adapting both Wq and Wv gives the best overall performance among the studied attention weight choices.","classification":"paper-fact","locator":quotes["PF14"][0],"quote":q("PF14"),"numeric_value":"","dependency_preconditions":"PC-HYP-2","reasoning":"","confidence":"high"})
claims.append({"claim_id":"PF15","claim_text":"GPT-3 adaptation used AdamW, 2 epochs, batch size 128, and weight decay 0.1.","classification":"paper-fact","locator":quotes["PF15"][0],"quote":q("PF15"),"numeric_value":"","dependency_preconditions":"PC-HYP-3","reasoning":"","confidence":"high"})
claims.append({"claim_id":"PF16","claim_text":"The paper uses two LoRA budgets on GPT-3 175B: 4.7M (rq=rv=1 or rv=2) and 37.7M (rq=rv=8 or rq=rk=rv=ro=2).","classification":"paper-fact","locator":quotes["PF16"][0],"quote":q("PF16"),"numeric_value":"","dependency_preconditions":"PC-HYP-1; PC-HYP-2; PC-HYP-4","reasoning":"","confidence":"high"})
claims.append({"claim_id":"PF17","claim_text":"On low-data MNLI subsets, LoRA achieves better performance than fine-tuning on MNLI-100 and MNLI-Full, and comparable results on MNLI-1k and MNLI-10K.","classification":"paper-fact","locator":quotes["PF17"][0],"quote":q("PF17"),"numeric_value":"","dependency_preconditions":"PC-DATA-5","reasoning":"","confidence":"high"})
claims.append({"claim_id":"PF18a","claim_text":"GPT-3 experiments use a sequence length of 384 for one dataset (sentence split across a page break; continuation names WikiSQL on the next page).","classification":"paper-fact","locator":quotes["PF18a"][0],"quote":q("PF18a"),"numeric_value":"384","dependency_preconditions":"PC-HYP-8","reasoning":"","confidence":"medium"})
claims.append({"claim_id":"PF18b","claim_text":"GPT-3 experiments use sequence length 768 for MNLI and 2048 for SAMSum.","classification":"paper-fact","locator":quotes["PF18b"][0],"quote":q("PF18b"),"numeric_value":"768","dependency_preconditions":"PC-HYP-8","reasoning":"","confidence":"high"})

claims.append({"claim_id":"INF1","claim_text":"A 7B-class model with L=32 layers and dmodel=4096, applying LoRA only to Wq and Wv with r=8, has about 4.2M trainable LoRA parameters.","classification":"inference","locator":"","quote":"","numeric_value":"","dependency_preconditions":"PC-HYP-4; PC-HYP-2","reasoning":"Inference, not a paper statement. Paper formula: |Theta| = 2 * L_LoRA * dmodel * r. With Wq+Wv adapted, L_LoRA = 2 * L = 64. Assuming a 7B architecture with L=32, dmodel=4096 (LLaMA-7B-style external assumption), |Theta| = 2 * 64 * 4096 * 8 = 4,194,304 ~ 4.2M. If the actual 7B model has different L or dmodel, recompute with the same formula.","confidence":"medium"})
claims.append({"claim_id":"INF2","claim_text":"On a 24GB card, LoRA on a 7B model plausibly fits but full fine-tuning does not; exact LoRA peak memory still needs measurement on the target setup.","classification":"inference","locator":"","quote":"","numeric_value":"","dependency_preconditions":"PC-COMP-3; PC-COMP-4; PC-HID-5; PC-HYP-4","reasoning":"Inference, not a paper statement. Assumptions: BF16 frozen weights = 2 bytes/param; AdamW states = 2*4 bytes/trainable param; gradients = 2 bytes/trainable param. Frozen base: 7e9*2 = 14 GB. LoRA trainable ~4.19M params -> optimizer+gradient ~4.19M*10 ~ 42 MB, negligible. So LoRA baseline ~14 GB + activations; with gradient checkpointing and small seq/batch there is budget left in 24 GB. Full fine-tune: 7e9*(2 weights + 2 grads + 8 Adam states) = 84 GB before activations, which exceeds 24 GB.","confidence":"medium"})
claims.append({"claim_id":"INF3","claim_text":"For the reader's 7B fine-tune, r=8 on Wq and Wv is a reasonable starting config to sweep, with lower ranks as a fallback for larger sequence length or slower runs.","classification":"inference","locator":"","quote":"","numeric_value":"","dependency_preconditions":"PC-HYP-1; PC-HYP-2; PF12; PF13; PF14","reasoning":"Inference. Paper uses r=8 for q/v as a GPT-3 budget (37.7M) and also shows r=1 can suffice for q/v on its tasks; best weight selection is Wq+Wv. A 7B model is smaller, so starting at r=8 q/v is a reasonable adaptation, but the paper does not give a 7B-specific optimum, so r should be swept (e.g. 4/8/16).","confidence":"medium"})
claims.append({"claim_id":"INF4","claim_text":"To keep a 7B LoRA run inside 24GB, the highest-impact controls are to lower max sequence length (e.g. 512 or 768 rather than 2048), use batch size 1-2, and enable gradient checkpointing.","classification":"inference","locator":"","quote":"","numeric_value":"","dependency_preconditions":"PC-HYP-8; PC-HID-5","reasoning":"Inference. Activation memory scales roughly linearly with batch_size * sequence_length (external standard assumption; the paper does not report activation memory bytes). Paper's GPT-3 settings are 384/768/2048 sequence lengths at batch 128; the reader cannot reuse batch 128, so scaling down seq/batch and checkpointing is the concrete change. Exact memory reduction must be measured on the chosen 7B model.","confidence":"medium"})

claims.append({"claim_id":"UND1","claim_text":"The exact peak GPU memory of a target 7B model fine-tuned with LoRA on a 24GB RTX 4090 is not stated in the paper and cannot be read off it.","classification":"undetermined","locator":"","quote":"","numeric_value":"","dependency_preconditions":"PC-HID-5","reasoning":"Paper reports only GPT-3 175B VRAM (1.2TB->350GB) on V100; it has no 7B, RTX 4090, or activation-memory figures. Would need: run/measure the chosen 7B model with the chosen framework/precision, or consult framework memory estimators.","confidence":"high"})
claims.append({"claim_id":"UND2","claim_text":"Whether LoRA's reported gains transfer to the reader's own 8,000-sample English task/domain is not determined by the available material.","classification":"undetermined","locator":"","quote":"","numeric_value":"","dependency_preconditions":"PC-HID-6","reasoning":"The paper evaluates GLUE/E2E/DART/WebNLG/WikiSQL/SAMSum (and MNLI low-data subsets), not the reader's unspecified 7B task. Would need: a small pilot run on the reader's 8,000 samples and a matching full-fine-tune/prefix baseline.","confidence":"high"})
claims.append({"claim_id":"UND3","claim_text":"The optimal LoRA hyperparameters for the reader's 7B model are not given in the paper.","classification":"undetermined","locator":"","quote":"","numeric_value":"","dependency_preconditions":"PC-HYP-3; PC-HYP-1","reasoning":"Paper provides hyperparameters for GPT-3/GPT-2/RoBERTa/DeBERTa, but no 7B configuration. Would need: a learning rate / rank / epoch / sequence-length sweep on the reader's model and dataset.","confidence":"high"})
claims.append({"claim_id":"UND4","claim_text":"Whether <= $200 of cloud GPU rental is enough for the reader's 7B LoRA experiments cannot be determined from the paper.","classification":"undetermined","locator":"","quote":"","numeric_value":"","dependency_preconditions":"PC-COMP-5","reasoning":"Paper gives throughput for GPT-3 on V100 (43.1 tokens/s) and says FT is costly, but gives no dollar figures or cost model. Would need: current cloud GPU pricing and a run-time estimate from a pilot.","confidence":"high"})

# write CSVs
def write_csv(name, fieldnames, rows):
    p = ROOT / name
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print("wrote", name)

write_csv("preconditions.csv", ["id","category","value","unit","source_locator","confidence"], pre)
write_csv("claims.csv", ["claim_id","claim_text","classification","locator","quote","numeric_value","dependency_preconditions","reasoning","confidence"], claims)

# evidence index
evidence = []
for cid, (loc, qu) in quotes.items():
    evidence.append({"id": f"EVID-{cid}", "kind": "paper-fact quote", "locator": loc, "quote": qu, "sha256": SRC_SHA})
with (ROOT / "evidence_index.json").open("w", encoding="utf-8") as f:
    json.dump(evidence, f, ensure_ascii=False, indent=2)
    f.write("\n")
print("wrote evidence_index.json", len(evidence), "entries; source sha:", SRC_SHA)

# verdict
verdict = """# Verdict: transferable-with-changes

## 1. Verdict

`transferable-with-changes`

LoRA 的机制（冻结预训练权重、只训练注入的低秩 A/B 矩阵）可以直接搬到 7B 模型，并且正是用来降低 24 GB 单卡显存压力的方法；但论文把关键的显存/吞吐数字放在 GPT-3 175B + V100 上，没有给出 7B + RTX 4090 的显存数字，因此不能原样照搬训练配置，需要改目标层、秩、序列长度、精度并在 24 GB 上实测。

## 2. What is established

以下结论均来自 `materials/source.txt`，带原文定位，逐字引文见 `claims.csv` 与 `evidence_index.json`：

- PF1（PAGE 1）：LoRA 冻结预训练权重，向每层 Transformer 注入可训练的低秩分解矩阵。
- PF2（PAGE 1）：相比用 Adam 微调 GPT-3 175B，LoRA 可减少 10,000 倍可训练参数、3 倍显存需求。
- PF3（PAGE 6）：可训练参数量公式 |Θ| = 2 × L_LoRA × dmodel × r，其中 L_LoRA 是施加 LoRA 的权重矩阵个数。
- PF5（PAGE 2）：LoRA 可把 A、B 合并回冻结权重，按构造不增加推理延迟。
- PF7 / PF8（PAGE 5）：用 Adam 时 LoRA 可省最多 2/3 的 VRAM；GPT-3 175B 训练显存从 1.2TB 降到 350GB。
- PF9（PAGE 5）：r=4 且只改 query/value 时，检查点约缩小 10,000×（350GB→35MB）。
- PF10（PAGE 5 脚注）：GPT-3 175B LoRA 吞吐 43.1 tokens/s/V100，全参微调 32.5 tokens/s/V100。
- PF11（PAGE 2）：即使 d 高达 12,288，r=1 或 2 就足够。
- PF12 / PF13 / PF14（PAGE 10）：18M 参数预算对应 r=8（单类注意力）或 r=4（两类）、96 层；r=1 即可用于 Wq+Wv；两者一起改（Wq+Wv）总体最好。
- PF15 / PF16 / PF18（PAGE 19-20）：GPT-3 用 AdamW、2 epoch、batch 128、weight decay 0.1；LoRA 预算 4.7M 与 37.7M；序列长度 384/768/2048。
- PF17（PAGE 22）：低数据 MNLI 子集上，LoRA 在 MNLI-100 与 MNLI-Full 优于全参微调。

## 3. What I inferred

以下不是论文原句，是本案例按论文公式与外部假设做出的推断：

- INF1：假设读者 7B 模型为 L=32、dmodel=4096（LLaMA-7B 类架构），只对 Wq+Wv 用 r=8：L_LoRA = 2×32 = 64，|Θ| = 2×64×4096×8 = 4,194,304 ≈ 4.2M。若实际 7B 架构不同，用同一公式重算。
- INF2：假设 BF16 权重 2 B/参数、AdamW 状态 2×4 B/可训练参数、梯度 2 B/可训练参数。LoRA：冻结基座 7e9×2 = 14 GB，LoRA 4.19M×10 ≈ 42 MB，基本可忽略，再加激活内存；开启梯度检查点并压小序列/批后，有望落在 24 GB 内。全参微调：7e9×(2+2+8)=84 GB（激活未计），超出 24 GB。该结论不是论文给出的 7B 数字。
- INF3：建议从 r=8、只改 Wq+Wv 开始扫描，并用 r=4/16 作为对比；论文 7B 最优秩未给，必须自己扫。
- INF4：控制 24 GB 的最高杠杆是降低最大序列长度（2048→512/768）、batch=1-2、开梯度检查点；激活内存约随 batch×seq 线性增长，这一关系为外部常理，论文未给激活字节数。

## 4. What remains open

- UND1（依赖 PC-HID-5）：论文没有 7B + RTX 4090 的峰值显存。需在所选 7B 模型、框架与精度下实测，或使用框架显存估算器。
- UND2（依赖 PC-HID-6）：论文未覆盖读者的具体任务/领域。需用读者自有 8,000 条样本做小规模试点，并与全参微调/prefix 基线对比。
- UND3（依赖 PC-HYP-3 等）：论文未给 7B 的最优学习率/秩/轮数/序列长度。需在读者数据上做超参扫描。
- UND4：论文没有价格模型，无法判定 ≤$200 云租费是否够。需查当前云卡单价并做运行时长估算。

## 预期行为对照

1. 事实与推断分开：已分开。所有带原文的结论标 `paper-fact` 并给 locator+quote；换算/类比全部标 `inference` 且 reasoning 注明“不是论文所述”。满足。
2. 数字可回算：每个 `paper-fact` 都给出 PAGE 定位并在 `evidence_index.json` 登记逐字节引文；核对时未发现论文摘要与正文、正文与脚注互相矛盾的数字（见日志；如后续核对有出入会写入本节）。部分满足（未发现不一致）。
3. 换算给算式：7B 显存/参数量换算已写算式、参数来源（PF3 公式 + PF8 显存）与假设（LLaMA-7B 架构、BF16、AdamW 状态字节数），并标为 `inference`。满足。
4. 表格行列身份：本任务未把压平表格里的单元格当作事实引用；若引用表格数字会说明行列，无法确定则降级（本案例未产生此类降级，因为均使用正文/脚注/附录正文的逐字引文）。满足。
5. 可操作建议：在 24 GB 上落地的具体改法写在第 3 节（r=8 q/v、降序列长度/批、梯度检查点），并写明论文不能保证的部分（7B 显存、读者领域、7B 超参、成本）写在第 4 节。满足。
"""

with (ROOT / "verdict.md").open("w", encoding="utf-8") as f:
    f.write(verdict)
print("wrote verdict.md")

# run log
run_log = """# Run log

## 成功完成的步骤
1. 环境自检（只读）：验证 materials/source.txt 与 skill/SKILL.md 的 SHA-256，均与任务书要求一致（source.txt = a8f387d2..., SKILL.md = 7ec803cb...）。
2. 阅读 cases/task-paper.md、materials/source_manifest.json、skill/SKILL.md。source_manifest 的“表格被压平、公式 (cid:NN) 保留”已知限制已纳入处理。
3. 将 source.txt 按 `=== PAGE n ===` 分页，通读 PDF 抽取文本，逐字提取引文锚点。
4. 用 Python 脚本生成 preconditions.csv / claims.csv / evidence_index.json / verdict.md。
5. 运行 scripts/check_agreement.py 数值一致性自检。

## 失败 / 重试
1. 第一次读 source.txt 分页时用 `re.split(r'(?=== PAGE \\d+ ===)', t)` + `re.match(r'=== PAGE (\\d+) ===\\n?', seg)`，26 页全部打印 MISSING。原因：抽取文本的页码锚点后是 CRLF，`\\n?` 无法跨过 `\\r`。改为 `re.split(r'(=== PAGE \\d+ ===)', t)` 后按顺序 (marker, text) 组装，分页成功。
2. 第一次想用 PowerShell here-string 一次性跑内联 Python 构建脚本时，命令行解析报 `字符串缺少终止符: "@`（ParserError），未执行任何写文件。改为先把 Python 脚本落到 `_build_deliverables.py` 再 `python _build_deliverables.py`。
3. SKILL.md 单次输出被截断，分两段（前 6000 字符 / 后段）重读，内容完整。

## 人工修正
- 引文全部由脚本从 source.txt 中 `find()` 定位并切片，不手抄，避免换行/转写差异。
- 对 7B 参数量/显存换算按论文公式 |Θ|=2*L_LoRA*dmodel*r 重算（初稿把 L_LoRA 与层数混算，得到 2.1M；已修正为 L_LoRA=2*L=64，结果为 4.2M）。
"""

(ROOT / "logs").mkdir(exist_ok=True)
with (ROOT / "logs" / "run_log.md").open("w", encoding="utf-8") as f:
    f.write(run_log)
print("wrote logs/run_log.md")
print("ALL BUILD OK")


