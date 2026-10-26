#!/usr/bin/env python3
"""案例 C：生成 preconditions.csv / claims.csv / evidence_index.json。

设计原则（对应本案例最硬的一条：不许编造数字）：
  * 所有 quote 都由「行号 + 起止标记」从材料里**切出来**，不手打，
    因此天然是原文的连续片段；写盘前逐条断言 quote ∈ 原文。
  * 被破坏的单元格所在行**不作为引文**（避免让截断值以任何形式进入引文/
    numeric_value）；受损行的信息只以 undetermined + 原因的形式出现。
  * 非 paper-fact 行的 numeric_value 一律留空（Skill 的 check_agreement.py
    会把「非事实却带数值」判为 finding）。

用法：
    python scripts/build_outputs.py --material materials/source.txt --outdir .
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

# ---------------------------------------------------------------- quote 定义
# id -> (kind, locator, line_no, start_marker, end_marker)
# start/end marker 为 None 时表示取整行（去首尾空白）。
QUOTES: dict[str, tuple[str, str, int, str | None, str | None]] = {
    "EV01": ("paragraph", "§ Time-to-GPT-2 Leaderboard（L41 段）", 41,
             "the wall clock time needed to outperform", "8XH100 GPU node"),
    "EV02": ("paragraph", "§ Time-to-GPT-2 Leaderboard（L41 段）", 41,
             "The GPT-2 CORE score is", "0.256525."),
    "EV03": ("paragraph", "§ Time-to-GPT-2 Leaderboard（L41 段）", 41,
             "at the current", "~$3/GPU/hr"),
    "EV04": ("paragraph", "§ Time-to-GPT-2 Leaderboard（L41 段）", 41,
             "an 8XH100 node is", "~$24/hr"),
    "EV05": ("paragraph", "§ Time-to-GPT-2 Leaderboard（L41 段）", 41,
             "so 2 hours is", "~$48"),
    "EV06": ("paragraph", "§ Time-to-GPT-2 Leaderboard（L41 段）", 41,
             "In 2019, the training of GPT-2 cost approximately", "$43,000"),
    "EV07": ("paragraph", "§ Getting started > Reproduce and talk to GPT-2（L65）", 65,
             "The entire pipeline to do so is contained in", "8XH100 GPU node."),
    "EV08": ("paragraph", "§ Getting started > Reproduce and talk to GPT-2（L71）", 71,
             "as this will take", "hours to run"),
    "EV09": ("list-item", "§ Getting started > A few more notes（L98）", 98,
             "The code will run just fine on the Ampere", "a bit slower."),
    "EV10": ("list-item", "§ Getting started > A few more notes（L99）", 99,
             "All code will run just fine on even a single GPU", "8 times longer."),
    "EV11": ("list-item", "§ Getting started > A few more notes（L100）", 100,
             "If your GPU(s) have less than 80GB", "run out of VRAM."),
    "EV12": ("list-item", "§ Getting started > A few more notes（L100）", 100,
             "Look for `--device-batch-size`", "or even 1."),
    "EV13": ("paragraph", "§ nanochat 首段（L23）", 23,
             "setting one single complexity dial", "approximately depth 26"),
    "EV14": ("paragraph", "§ Research（L125）", 125,
             "happens to be somewhere around", "range with the current code"),
    "EV15": ("paragraph", "§ Getting started > Reproduce and talk to GPT-2（L77）", 77,
             "The speedrun is a", "capability model"),
    "EV16": ("paragraph", "§ Research（L105）", 105,
             "For quick experimentation", "(GPT-1 sized)"),
    "EV17": ("list-item", "§ Research > 监控指标（L119）", 119,
             "`val_bpb` (validation loss", "total_training_flops`."),
    "EV18": ("table-row", "§ Precision / dtype 表（L137 行）", 137, None, None),
    "EV19": ("paragraph", "§ Precision / dtype（L148）", 148,
             "model weights are stored in fp32", "during the forward pass."),
    "EV20": ("paragraph", "§ Precision / dtype（L150）", 150,
             "`float16` training automatically enables", "RL currently does not."),
    "EV21": ("code-block", "§ File structure > nanochat/optim.py（L181）", 181,
             "AdamW + Muon optimizer", "distributed"),
    "EV22": ("code-block", "§ File structure > nanochat/core_eval.py（L174）", 174,
             "core_eval.py", "(DCLM paper)"),
    "EV23": ("list-item", "§ Acknowledgements（L226）", 226,
             "Thank you to [HuggingFace]", "for fineweb and smoltalk."),
    "EV24": ("paragraph", "§ Contributing（L218）", 218,
             "Currently this takes", "(down from 3h)"),
    "EV25": ("table-row", "§ Time-to-GPT-2 Leaderboard 表（# 0 行，L36）", 36, None, None),
    "EV26": ("table-row", "§ Time-to-GPT-2 Leaderboard 表（# 1 行，L34）", 34, None, None),
    "EV27": ("table-row", "§ Time-to-GPT-2 Leaderboard 表（# 6 行，L33）", 33, None, None),
    "EV28": ("table-cell", "§ Time-to-GPT-2 Leaderboard 表（# 4 行 Description 单元格，L35）", 35,
             "change dataset to", "ClimbMix"),
    "EV29": ("table-header", "§ Time-to-GPT-2 Leaderboard 表（L31 表头行）", 31, None, None),
    "EV30": ("table-header", "§ Time-to-GPT-2 Leaderboard 表（L32 分隔行）", 32, None, None),
}

# ---------------------------------------------------------------- 前置条件
# id, category, value, unit, source_locator, confidence
PRECONDITIONS: list[tuple[str, str, str, str, str, str]] = [
    ("P-C1", "compute", "8×H100 单节点是 speedrun 的参考配置", "GPU 节点",
     "nanochat_README_table_corrupted.md § Getting started > Reproduce and talk to GPT-2（L65）", "stated"),
    ("P-C2", "compute", "speedrun 全流程墙钟时间 ~1.5 小时", "hours",
     "nanochat_README_table_corrupted.md § Getting started > Reproduce and talk to GPT-2（L71）", "stated"),
    ("P-C3", "compute", "GPU 单价 ~$3/GPU/hr", "USD/hour",
     "nanochat_README_table_corrupted.md § Time-to-GPT-2 Leaderboard（L41）", "stated"),
    ("P-C4", "compute", "8×H100 节点约 $24/hr；2 小时约 $48", "USD",
     "nanochat_README_table_corrupted.md § Time-to-GPT-2 Leaderboard（L41）", "stated"),
    ("P-C5", "compute", "代码可在 8×A100 节点运行，原文仅称 \"a bit slower\"（未给量化倍率）", "-",
     "nanochat_README_table_corrupted.md § Getting started > A few more notes（L98）", "stated"),
    ("P-C6", "compute", "单 GPU 可跑（去掉 torchrun，自动切梯度累积），代价是等待时间 ×8", "×墙钟",
     "nanochat_README_table_corrupted.md § Getting started > A few more notes（L99）", "stated"),
    ("P-C7", "compute", "每 GPU 显存需 ≥80GB，否则必须调超参或 OOM / 显存溢出", "GB VRAM/GPU",
     "nanochat_README_table_corrupted.md § Getting started > A few more notes（L100）", "stated"),
    ("P-C8", "compute",
     "未给出 —— 原因：训练/评测的实测峰值显存从未出现；README 只给 80GB 这一经验阈值。"
     "迁移到 A100 80GB 时没有余量数据可依，必须先实测占用。", "MiB",
     "nanochat_README_table_corrupted.md（全文检索：未出现峰值显存陈述）", "absent"),
    ("P-C9", "compute",
     "未给出 —— 原因：A100 相对 H100 的时间倍率没有量化（L98 只有 \"a bit slower\"）。"
     "它是判断 ≤4 小时训练预算能否覆盖的唯一缺失量。", "×",
     "nanochat_README_table_corrupted.md § Getting started > A few more notes（L98）", "absent"),

    ("P-D1", "data scale", "GPT-2 参数量 1.6B", "params",
     "nanochat_README_table_corrupted.md § Time-to-GPT-2 Leaderboard（L41）", "stated"),
    ("P-D2", "data scale", "speedrun 模型算力规模 4e19", "FLOPs",
     "nanochat_README_table_corrupted.md § Getting started > Reproduce and talk to GPT-2（L77）", "stated"),
    ("P-D3", "data scale", "预训练数据经 nanochat/dataset.py 下载/读取（数据可下载）", "-",
     "nanochat_README_table_corrupted.md § File structure（L171）", "stated"),
    ("P-D4", "data scale",
     "未给出 —— 原因：训练 token 数与语料体积全文未出现。", "tokens / GB",
     "nanochat_README_table_corrupted.md（全文检索：未出现 token 数或数据体积陈述）", "absent"),
    ("P-D5", "data scale",
     "未给出 —— 原因：默认预训练语料的身份/混合/版本全文未声明；"
     "语料线索只有致谢里的 fineweb/smoltalk（L226）与受损表格 Description 单元格的 ClimbMix（L35），"
     "都不足以确定当前 speedrun 默认用什么。", "-",
     "nanochat_README_table_corrupted.md § Acknowledgements（L226）与 § Time-to-GPT-2 Leaderboard 表（L35）", "absent"),
    ("P-D6", "data scale",
     "未给出 —— 原因：全文没有任何下载耗时陈述。读者约束明确要求单独说明下载时间，"
     "材料无法支撑该预算项。", "minutes",
     "nanochat_README_table_corrupted.md（全文检索：未出现下载时间陈述）", "absent"),
    ("P-D7", "data scale",
     "未给出 —— 原因：全文没有数据落盘体积，无法与读者的磁盘 ≥100GB 约束对照。", "GB",
     "nanochat_README_table_corrupted.md（全文检索：未出现数据体积陈述）", "absent"),
    ("P-D8", "data scale",
     "未给出 —— 原因：验证集/CORE 评测所用数据规模未出现，val_bpb 与 CORE 的可比性无从判断。", "samples",
     "nanochat_README_table_corrupted.md（全文检索：未出现评测集规模陈述）", "absent"),

    ("P-H1", "hyperparameters", "唯一复杂度旋钮 --depth（层数）；GPT-2 能力 ≈ depth 26，当前代码在 d24–d26 区间",
     "layers",
     "nanochat_README_table_corrupted.md § nanochat 首段（L23）与 § Research（L125）", "stated"),
    ("P-H2", "hyperparameters", "--device-batch-size 默认 32，可依次降到 16/8/4/2/1", "tokens/step",
     "nanochat_README_table_corrupted.md § Getting started > A few more notes（L100）", "stated"),
    ("P-H3", "hyperparameters",
     "总 batch size 1M tokens（leaderboard #3 行 Description 单元格自述；该单元格位于受损表格内，未做上游核验）",
     "tokens", "nanochat_README_table_corrupted.md § Time-to-GPT-2 Leaderboard 表（# 3 行，L37）", "stated"),
    ("P-H4", "hyperparameters",
     "计算精度由全局 COMPUTE_DTYPE 决定；SM80+（A100/H100）默认 bfloat16，权重以 fp32 存储供优化器用", "dtype",
     "nanochat_README_table_corrupted.md § Precision / dtype（L133/L137/L148）", "stated"),
    ("P-H5", "hyperparameters", "优化器 AdamW + Muon（支持单 GPU 与分布式）", "-",
     "nanochat_README_table_corrupted.md § File structure（L181）", "stated"),
    ("P-H6", "hyperparameters", "学习率调整、训练时长、权重衰减等由代码按 depth 自动计算，用户无需设置", "-",
     "nanochat_README_table_corrupted.md § nanochat 首段（L23）", "stated"),
    ("P-H7", "hyperparameters", "fp16 训练自动启用 GradScaler（SFT 支持，RL 目前不支持）", "-",
     "nanochat_README_table_corrupted.md § Precision / dtype（L150）", "stated"),
    ("P-H8", "hyperparameters",
     "未给出 —— 原因：speedrun 的完整超参取值（lr、warmup、batch 切分、序列长度、depth 具体配置）没有内联在材料里，"
     "README 只说\"自动计算\"并指向 runs/speedrun.sh。", "-",
     "nanochat_README_table_corrupted.md § nanochat 首段（L23，仅指向 runs/speedrun.sh）", "absent"),

    ("P-A1", "hidden assumptions", "单机 8 卡多进程（torchrun --standalone --nproc_per_node=8）为参考配置", "-",
     "nanochat_README_table_corrupted.md § Research（L108）", "stated"),
    ("P-A2", "hidden assumptions", "depth 单一旋钮原则必须对所有 depth 成立，仓库改动须对全谱系有效", "-",
     "nanochat_README_table_corrupted.md § Research（L125）", "stated"),
    ("P-A3", "hidden assumptions",
     "runs/speedrun.sh 是榜单的参考实现；榜单各行对应不同 commit（代码版本随行变化）", "-",
     "nanochat_README_table_corrupted.md § Time-to-GPT-2 Leaderboard（L29）", "stated"),
    ("P-A4", "hidden assumptions",
     "未给出 —— 原因：预训练语料的混合比例与版本只在致谢里被提及，未作为方法前置条件声明。", "-",
     "nanochat_README_table_corrupted.md § Acknowledgements（L226）", "absent"),
    ("P-A5", "hidden assumptions",
     "未给出 —— 原因：CORE（DCLM）评测的实现依赖与版本只出现在文件清单里，方法能否达标直接依赖这个门限。", "-",
     "nanochat_README_table_corrupted.md § File structure（L174）", "absent"),
    ("P-A6", "hidden assumptions",
     "未给出 —— 原因：榜单 \"time\" 列的计时口径（是否含评测/保存/数据加载）表头没有说明；"
     "且该表格整体结构受损，无法从行内文字反推口径。", "-",
     "nanochat_README_table_corrupted.md § Time-to-GPT-2 Leaderboard 表（L31–L39）", "absent"),
    ("P-A7", "hidden assumptions", "训练验收门限：CORE 需超过 0.256525", "CORE",
     "nanochat_README_table_corrupted.md § Contributing（L218）", "stated"),
]

# ---------------------------------------------------------------- 结论
# claim_id, claim_text, classification, locator, quote_id, numeric_value,
# dependency_preconditions, confidence
CLAIMS: list[tuple[str, str, str, str, str | None, str, str, str]] = [
    ("C01",
     "主要指标 \"time to GPT-2\" = 在 8×H100 节点上把 GPT-2 (1.6B) 的 CORE 超过去所需的墙钟时间。",
     "paper-fact", "nanochat_README_table_corrupted.md § Time-to-GPT-2 Leaderboard（L41）", "EV01", "",
     "P-C1,P-D1,P-A7", "high"),
    ("C02", "GPT-2 的 CORE 分数为 0.256525（本文用它做验收门限）。",
     "paper-fact", "nanochat_README_table_corrupted.md § Time-to-GPT-2 Leaderboard（L41）", "EV02", "0.256525",
     "P-A7", "high"),
    ("C03", "GPU 单价约 $3/GPU/hr。",
     "paper-fact", "nanochat_README_table_corrupted.md § Time-to-GPT-2 Leaderboard（L41）", "EV03", "3",
     "P-C3", "high"),
    ("C04", "8×H100 节点约 $24/hr。",
     "paper-fact", "nanochat_README_table_corrupted.md § Time-to-GPT-2 Leaderboard（L41）", "EV04", "24",
     "P-C4", "high"),
    ("C05", "在 8×H100 上跑 2 小时约 $48。",
     "paper-fact", "nanochat_README_table_corrupted.md § Time-to-GPT-2 Leaderboard（L41）", "EV05", "48",
     "P-C4", "high"),
    ("C06", "2019 年训练 GPT-2 的成本约 $43,000。",
     "paper-fact", "nanochat_README_table_corrupted.md § Time-to-GPT-2 Leaderboard（L41）", "EV06", "43000",
     "", "high"),
    ("C07", "整个 GPT-2 级训练流程收敛在单个文件 runs/speedrun.sh 中，设计为在 8×H100 节点上运行。",
     "paper-fact", "nanochat_README_table_corrupted.md § Getting started > Reproduce and talk to GPT-2（L65）", "EV07", "8",
     "P-C1,P-A3", "high"),
    ("C08", "speedrun 端到端墙钟时间约 1.5 小时。",
     "paper-fact", "nanochat_README_table_corrupted.md § Getting started > Reproduce and talk to GPT-2（L71）", "EV08", "1.5",
     "P-C2", "high"),
    ("C09", "代码可在 8×A100 节点上运行，原文只说\"会慢一点\"，没有给量化倍率。",
     "paper-fact", "nanochat_README_table_corrupted.md § Getting started > A few more notes（L98）", "EV09", "8",
     "P-C5", "high"),
    ("C10", "单 GPU 可跑（去掉 torchrun，自动切梯度累积），结果 ~identical，代价是等待时间 ×8。",
     "paper-fact", "nanochat_README_table_corrupted.md § Getting started > A few more notes（L99）", "EV10", "8",
     "P-C6", "high"),
    ("C11", "GPU 显存低于 80GB 必须调超参，否则 OOM / 显存溢出。",
     "paper-fact", "nanochat_README_table_corrupted.md § Getting started > A few more notes（L100）", "EV11", "80",
     "P-C7", "high"),
    ("C12", "--device-batch-size 默认 32，可依次降到 16/8/4/2/1。",
     "paper-fact", "nanochat_README_table_corrupted.md § Getting started > A few more notes（L100）", "EV12", "32",
     "P-H2", "high"),
    ("C13", "nanochat 以单一复杂度旋钮 --depth（层数）配置，其余超参自动计算；GPT-2 能力约 depth 26。",
     "paper-fact", "nanochat_README_table_corrupted.md § nanochat 首段（L23）", "EV13", "26",
     "P-H1,P-H6", "high"),
    ("C14", "当前代码下 GPT-2 能力模型落在 d24–d26 区间。",
     "paper-fact", "nanochat_README_table_corrupted.md § Research（L125）", "EV14", "24",
     "P-H1", "high"),
    ("C15", "speedrun 模型是 4e19 FLOPs 的能力模型。",
     "paper-fact", "nanochat_README_table_corrupted.md § Getting started > Reproduce and talk to GPT-2（L77）", "EV15", "4e19",
     "P-D2", "high"),
    ("C16", "快速实验档位：12 层（GPT-1 量级）模型，约 5 分钟预训练。",
     "paper-fact", "nanochat_README_table_corrupted.md § Research（L105）", "EV16", "12",
     "P-H1", "high"),
    ("C17", "迭代时监控 val_bpb（按字节归一的验证损失）、core_metric、VRAM/MFU/吞吐。",
     "paper-fact", "nanochat_README_table_corrupted.md § Research > 监控指标（L119）", "EV17", "",
     "P-D8", "high"),
    ("C18", "CUDA SM 80+（A100/H100）默认计算精度 bfloat16。",
     "paper-fact", "nanochat_README_table_corrupted.md § Precision / dtype 表（L137 行）", "EV18", "80",
     "P-H4", "high"),
    ("C19", "权重以 fp32 存储以保证优化器精度，前向时由自定义 Linear 层转到 COMPUTE_DTYPE。",
     "paper-fact", "nanochat_README_table_corrupted.md § Precision / dtype（L148）", "EV19", "32",
     "P-H4", "high"),
    ("C20", "fp16 训练自动启用 GradScaler 防下溢；SFT 支持，RL 目前不支持。",
     "paper-fact", "nanochat_README_table_corrupted.md § Precision / dtype（L150）", "EV20", "16",
     "P-H7", "high"),
    ("C21", "优化器为 AdamW + Muon（支持单 GPU 与分布式）。",
     "paper-fact", "nanochat_README_table_corrupted.md § File structure > nanochat/optim.py（L181）", "EV21", "",
     "P-H5", "high"),
    ("C22", "CORE 评测由 nanochat/core_eval.py 实现（DCLM 论文口径）。",
     "paper-fact", "nanochat_README_table_corrupted.md § File structure > nanochat/core_eval.py（L174）", "EV22", "",
     "P-A5", "medium"),
    ("C23", "致谢确认语料来自 HuggingFace（fineweb 与 smoltalk）。",
     "paper-fact", "nanochat_README_table_corrupted.md § Acknowledgements（L226）", "EV23", "",
     "P-A4", "medium"),
    ("C24", "项目目标是把 CORE 提到 0.256525 之上，当前约 1.5 小时（此前 3h）。",
     "paper-fact", "nanochat_README_table_corrupted.md § Contributing（L218）", "EV24", "1.5",
     "P-A7,P-C2", "high"),
    ("C25",
     "被破坏的 leaderboard 表中确有一行 OpenAI 原始 GPT-2 检查点记录：168 hours、0.2565、2019、OpenAI。"
     "（该行单元格本身未见改动，但整表结构受损，且本行所在章节**未做上游逐字核验**。）",
     "paper-fact", "nanochat_README_table_corrupted.md § Time-to-GPT-2 Leaderboard 表（# 0 行，L36）", "EV25", "0.2565",
     "P-A6", "medium"),
    ("C26",
     "被破坏的表中确有一行 d24 baseline 记录：3.04、0.74833、Jan 29 2026、348fbb3。（整表受损，未做上游核验。）",
     "paper-fact", "nanochat_README_table_corrupted.md § Time-to-GPT-2 Leaderboard 表（# 1 行，L34）", "EV26", "3.04",
     "P-A6", "medium"),
    ("C27",
     "被破坏的表中确有一行 autoresearch round 2 记录：1.65、0.71800、Mar 14 2026、a825e63。（整表受损，未做上游核验。）",
     "paper-fact", "nanochat_README_table_corrupted.md § Time-to-GPT-2 Leaderboard 表（# 6 行，L33）", "EV27", "1.65",
     "P-A6", "medium"),
    ("C28",
     "被破坏的表中确有一行的 Description 单元格自述为\"把数据集换成 NVIDIA ClimbMix\"；"
     "该单元格本身未见改动（但同行的 time 单元格受损，见 C31）。",
     "paper-fact", "nanochat_README_table_corrupted.md § Time-to-GPT-2 Leaderboard 表（# 4 行 Description 单元格，L35）",
     "EV28", "", "P-D5", "medium"),

    ("C29",
     "【推断】表格单元格→列名的映射成立：数据行的 7 格按位置对应表头的 #/time/CORE/Description/Date/Commit/Contributors。"
     "推导依据：(a) # 0 行里\"168 hours\"只可能是 time，\"0.2565\"与正文 0.256525 的相对误差为 0.0098%（<1%），"
     "该行其余单元格也各自自洽；(b) 其余行的 Description/Date/Commit/Contributors 文本自洽；"
     "(c) 机械破坏通常对各行删除同一列。该映射是**我的推导，不是原文声明**，只影响\"各行 time 怎么读\"，"
     "不影响受损单元格不可恢复这一结论。",
     "inference", "nanochat_README_table_corrupted.md § Time-to-GPT-2 Leaderboard 表（L31–L39）", None, "",
     "P-A6", "medium"),
    ("C30",
     "【推断】本表已读出的行里，time 值随 # 增大而单调变小（# 6 行的 1.65 为最小），说明 # 列更像名次而非序号；"
     "但文件中的物理行序已被打乱（# 出现顺序为 6,1,4,0,3,2,5），不能按出现顺序读榜。"
     "该单调性同时是本任务明令禁止的猜补路径——**本运行据此拒绝给出受损单元格的任何区间或点估计**。",
     "inference", "nanochat_README_table_corrupted.md § Time-to-GPT-2 Leaderboard 表（L33–L39）", None, "",
     "P-A6", "medium"),
    ("C31",
     "【推断】迁移判定：nanochat 的**方法机制**（单一 --depth 旋钮 + 单文件 runs/speedrun.sh 流水线 + "
     "DCLM CORE 门限 + d12 快速标定循环）在 8×A100 80GB / ≤4h / ≤$100 的约束下**可迁，但不是开箱即用**。"
     "推导：(a) A100 被明确支持（C09）；(b) 每卡 80GB 恰好满足 ≥80GB 的阈值（C11）；"
     "(c) 参考墙钟 1.5h（H100，C08）落在 4h 预算内，而 A100 只被描述为\"慢一点\"且未量化（C35）→ 属 stretch；"
     "(d) 成本按材料自身口径 $3/GPU/hr 推算：8 卡 × 4h = $96 ≤ $100（余量 4%）；材料未给 A100 报价，"
     "故按同价保守估计；(e) 数据侧下载时间与体积未给（C34）→ 预算无法闭合。"
     "读者目标只取\"方法机制\"、不要求复现数字，因此被破坏的 leaderboard 不构成阻塞。",
     "inference", "依赖 C01–C28 与 P-C1…P-A7（推导见正文）", None, "",
     "P-C9,P-D6,P-D7", "medium"),
    ("C32",
     "【推断】被破坏的 leaderboard 只影响\"数字基线/名次\"的可引用性，不影响\"机制能否迁移\"的判定："
     "机制所需的输入（单文件流水线、--depth 旋钮、A100 兼容性、80GB 阈值、4e19 FLOPs 规模、d12 标定档）"
     "全部位于**未受损的正文段落**，且这些段落已逐行核对为上游原文。",
     "inference", "依赖 C01–C24（正文段落，已逐行核验）", None, "",
     "", "medium"),

    ("C33",
     "排行榜 # 4 行（Description = change dataset to NVIDIA ClimbMix）的训练墙钟时间**无法从本文件确定**："
     "该单元格被截断（内容只剩 \"2.\"，仅描述受损形态，不作为数值引用）。"
     "**不按上下文猜补**——按行序、按相邻行的 time、按 CORE 接近性推出的任何值都属猜测，已拒绝采用；"
     "numeric_value 留空。**需要什么才能定**：上游 README 或 dev/LEADERBOARD.md 中未损坏的同一行，或该 run 的作者日志。",
     "undetermined", "nanochat_README_table_corrupted.md § Time-to-GPT-2 Leaderboard 表（# 4 行，time 单元格，L35）",
     None, "", "P-A6", "absent"),
    ("C34",
     "原表存在一个本文件无法复原的列：表头只列出 7 个列名，分隔行却有 8 段，数据行多为 7 格（一行 9 格）；"
     "合成声明称该列为 val_bpb。**该列的任何取值都无法从本文件确定**，也**不得按上下文重建**。"
     "需要什么才能定：未损坏的表头与数据行（上游 README 的同一节，或 dev/LEADERBOARD.md）。",
     "undetermined", "nanochat_README_table_corrupted.md § Time-to-GPT-2 Leaderboard 表（L31–L32 表头/分隔行）",
     None, "", "", "absent"),
    ("C35",
     "排行榜的官方名次/榜首**无法从本文件确定**：物理行序被打乱（# 出现顺序 6,1,4,0,3,2,5），"
     "且材料从未声明 # 列是否即名次。**需要什么才能定**：未损坏的榜单，或 dev/LEADERBOARD.md 的贡献与排序说明。",
     "undetermined", "nanochat_README_table_corrupted.md § Time-to-GPT-2 Leaderboard 表（L33–L39）",
     None, "", "P-A6", "absent"),
    ("C36",
     "当前 speedrun 使用的预训练语料（混合/版本/token 量）**无法确定**：材料只在致谢里提 fineweb/smoltalk，"
     "未声明默认配置；受损表格中出现的 ClimbMix 是行内 Description 文字，且该行整体受损。"
     "**需要什么才能定**：nanochat/dataset.py 与 runs/speedrun.sh 的源码，或仓库里的数据准备说明。",
     "undetermined", "nanochat_README_table_corrupted.md § Acknowledgements（L226）与 § Time-to-GPT-2 Leaderboard 表（L35）",
     None, "", "P-D4,P-D5", "absent"),
    ("C37",
     "数据下载耗时与落盘体积**无法确定**：材料全文没有任何下载时间或数据体积陈述，"
     "而读者约束要求把下载时间单独说明。**需要什么才能定**：dataset.py 的下载清单与各文件体积，"
     "或一次实测下载（不需要训练）。",
     "undetermined", "nanochat_README_table_corrupted.md（全文检索：未出现下载时间/体积陈述）",
     None, "", "P-D6,P-D7", "absent"),
    ("C38",
     "A100 相对 H100 的时间倍率**无法确定**：原文只有未量化的 \"a bit slower\"。"
     "**需要什么才能定**：一次 A100 实测标定（例如 d12 档，约 5 分钟预训练，见 C16），"
     "或在 8×A100 上跑一次 d24 量级短跑。",
     "undetermined", "nanochat_README_table_corrupted.md § Getting started > A few more notes（L98）",
     None, "", "P-C9", "absent"),
    ("C39",
     "榜单 \"time\" 列的计时口径（是否含评测/保存/数据加载）**无法确定**：表头只有列名，未给口径；"
     "整表结构受损也无法从行内文字反推。**需要什么才能定**：dev/LEADERBOARD.md 的口径说明，或榜单的提交规则。",
     "undetermined", "nanochat_README_table_corrupted.md § Time-to-GPT-2 Leaderboard 表（L31–L39）",
     None, "", "P-A6", "absent"),
]


def extract_quote(text: str, lines: list[str], line_no: int, start: str | None, end: str | None) -> str:
    raw = lines[line_no - 1]
    if start is None and end is None:
        q = raw.strip()
    else:
        s = raw.index(start)
        e = raw.index(end, s) + len(end)
        q = raw[s:e]
    assert q in text, f"引文不是原文连续子串: L{line_no} {q[:60]!r}"
    return q


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--material", required=True, type=Path)
    ap.add_argument("--outdir", required=True, type=Path)
    args = ap.parse_args()

    raw = args.material.read_bytes()
    text = raw.decode("utf-8")
    lines = text.split("\n")
    digest = hashlib.sha256(raw).hexdigest()

    quotes = {}
    for qid, (kind, locator, line_no, start, end) in QUOTES.items():
        quotes[qid] = {
            "id": qid,
            "kind": kind,
            "locator": f"materials/nanochat_README_table_corrupted.md {locator}",
            "quote": extract_quote(text, lines, line_no, start, end),
            "sha256": digest,
        }

    args.outdir.mkdir(parents=True, exist_ok=True)

    write_csv(
        args.outdir / "preconditions.csv",
        ["id", "category", "value", "unit", "source_locator", "confidence"],
        [list(r) for r in PRECONDITIONS],
    )

    claim_rows = []
    for cid, ctext, cclass, cloc, qid, num, deps, conf in CLAIMS:
        quote = quotes[qid]["quote"] if qid else ""
        if cclass == "paper-fact":
            assert quote, f"{cid}: paper-fact 必须有引文"
            # 与 check_agreement.py 同样的口径：数字在引文里，去掉千分位逗号后也应能命中
            assert num == "" or num in quote or num in quote.replace(",", ""), \
                f"{cid}: numeric_value 未出现在引文中"
        else:
            assert quote == "", f"{cid}: 非 paper-fact 不得带引文"
            assert num == "", f"{cid}: 非 paper-fact 不得带 numeric_value"
        claim_rows.append([cid, ctext, cclass, cloc, quote, num, deps, conf])

    write_csv(
        args.outdir / "claims.csv",
        ["claim_id", "claim_text", "classification", "locator", "quote",
         "numeric_value", "dependency_preconditions", "confidence"],
        claim_rows,
    )

    used = sorted({q for _, _, c, _, q, _, _, _ in CLAIMS if q})
    evidence = [quotes[q] for q in used]
    (args.outdir / "evidence_index.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print("material sha256 :", digest)
    print("preconditions    :", len(PRECONDITIONS))
    print("claims           :", len(CLAIMS))
    print("evidence entries :", len(evidence))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
