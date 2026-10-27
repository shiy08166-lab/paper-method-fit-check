#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 ledger.json（作者侧账本的数据层）。

引文**不是手打**的：每条都按锚点从源文件里切出来，逐字节一致
（论文侧的引文来自 `materials/source.txt`，报告侧的引文来自对应那一轮的 `verdict.md` / `claims.csv`）。
算式与复算值也在这里算好，`scripts/verify_paper_results.py` 会把它们**重新算一遍**。

用法（在 experiments/paper-case/ 下运行）：
    python scripts/build_ledger.py
"""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = (ROOT / "materials" / "source.txt").read_text(encoding="utf-8")


def cut_in(text: str, anchor: str, start: str = "", end: str = "", occurrence: int = 1) -> str:
    i = -1
    for _ in range(occurrence):
        i = text.find(anchor, i + 1)
        if i < 0:
            raise SystemExit("锚点没找到: %r" % anchor)
    s = text.find(start, i) if start else i
    if s < 0 or (start and s > i + 200):
        s = i
    e = text.find(end, s) if end else len(text)
    if e < 0:
        raise SystemExit("结束锚点没找到: %r" % end)
    if end:
        e += len(end)          # 把结束锚点本身也包进来
    return text[s:e]


def cut(anchor: str, start: str = "", end: str = "", occurrence: int = 1) -> str:
    return cut_in(SRC, anchor, start, end, occurrence)


ENTRIES = [
    # ---------------- 论文自身的数字：作者侧重算 ----------------
    dict(
        id="P-01", kind="paper-arithmetic",
        item="论文自述「VRAM 降 2/3」与它自己紧邻的 1.2TB→350GB 例子",
        source_locator="materials/source.txt 第 5 页（§4.2 Practical Benefits and Limitations）",
        page=5,
        quote=cut("For a large Transformer trained with Adam", "For a large Transformer", "350GB."),
        computation="(1 - 350/1200)*100",
        recomputed_value=(1 - 350 / 1200) * 100,
        paper_value=100 * 2 / 3,
        paper_tolerance=0.01,
        verdict="不符",
        notes=("论文写「we reduce that VRAM usage by up to 2/3」＝66.67%，"
               "而它紧挨着的 GPT-3 175B 例子（1.2TB→350GB）实际是 70.83% 的降幅——"
               "自述的界被自己的例子超过。摘要里的「GPU memory requirement by 3 times」"
               "同源：实为 3.43×。"),
    ),
    dict(
        id="P-02", kind="paper-arithmetic",
        item="摘要「GPU memory requirement by 3 times」 vs 论文自己的 1.2TB→350GB",
        source_locator="materials/source.txt 第 1 页（Abstract）",
        page=1,
        quote=cut("Compared to GPT-3 175B fine-tuned with Adam", "Compared to GPT-3 175B fine-tuned with Adam,", "3 times."),
        computation="1200/350",
        recomputed_value=1200 / 350,
        paper_value=3.0,
        paper_tolerance=0.01,
        verdict="不符",
        notes=("论文自己的两个数给出 3.43×；摘要把它写成「3 times」。"
               "报告若直接引「3×」而不标注口径，读者按论文数据复算会对不上。"),
    ),
    dict(
        id="P-03", kind="paper-arithmetic",
        item="正文「25% speedup」 vs 同页脚注 5 的 32.5→43.1 tokens/s",
        source_locator="materials/source.txt 第 5 页（正文 + 脚注 5）",
        page=5,
        quote=cut("We also observe a 25% speedup", "We also observe a 25% speedup", "parameters."),
        computation="(43.1/32.5 - 1)*100",
        recomputed_value=(43.1 / 32.5 - 1) * 100,
        paper_value=25.0,
        paper_tolerance=0.01,
        verdict="不符",
        notes=("脚注 5：full fine-tuning 32.5 tokens/s per V100，LoRA 43.1 tokens/s per V100。"
               "按吞吐提升的常规读法是 +32.62%，不是 25%；只有把 25% 读成"
               "「每 token 时间下降」(1-32.5/43.1=24.59%) 才凑得上。"
               "同一个「speedup」有两种口径，论文没说是哪一种——"
               "**引文逐字命中、数值 1% 内、checker 0 标记，全都拦不住它**。"),
    ),
    dict(
        id="P-04", kind="paper-arithmetic",
        item="脚注 5 的 32.5→43.1 tokens/s 与「25%」的另一种口径",
        source_locator="materials/source.txt 第 5 页（脚注 5）",
        page=5,
        quote=cut("5For GPT-3 175B, the training throughput", "5For GPT-3 175B, the training throughput", "for LoRA."),
        computation="(1 - 32.5/43.1)*100",
        recomputed_value=(1 - 32.5 / 43.1) * 100,
        paper_value=25.0,
        paper_tolerance=0.02,
        round_to=0,
        verdict="符",
        notes="把 25% 理解成「每 token 时间下降 24.59%」才与脚注自洽 —— 说明 P-03 是**口径**问题，不是算错。",
    ),
    dict(
        id="P-05", kind="paper-arithmetic",
        item="checkpoint 体积 350GB→35MB 的「10,000×」",
        source_locator="materials/source.txt 第 5 页（§4.2）",
        page=5,
        quote=cut("With r = 4 and only the query and value", "With r = 4 and only the query and value", "35MB)4."),
        computation="350*1000/35",
        recomputed_value=350 * 1000 / 35,
        paper_value=10000.0,
        paper_tolerance=0.001,
        verdict="符",
        notes="十进制 GB/MB 下 350,000MB / 35MB = 10,000×，与论文一致。",
    ),
    dict(
        id="P-06", kind="paper-arithmetic",
        item="「18M 参数 ≈ 35MB(FP16)」的自洽性",
        source_locator="materials/source.txt 第 10 页（§7.1）",
        page=10,
        quote=cut("We set a parameter budget of 18M", "We set a parameter budget of 18M", "96 layers."),
        computation="18000000*2/1048576",
        recomputed_value=18000000 * 2 / 1048576,
        paper_value=35.0,
        paper_tolerance=0.05,
        verdict="符",
        notes="18M × 2B = 36 MB（十进制）= 34.33 MiB，与论文的「roughly 35MB」差 1.91%，属「roughly」。",
    ),
    dict(
        id="P-07", kind="paper-arithmetic",
        item="第 3 页「|Θ| 可小到 |Φ0| 的 0.01%」与第 10 页的 18M 预算是否自洽",
        source_locator="materials/source.txt 第 3 页（§2）",
        page=3,
        quote=cut("When the pre-trained model is GPT-3 175B", "When the pre-trained model is GPT-3 175B", "of |Φ0|."),
        computation="175000000000*0.0001/1000000",
        recomputed_value=175000000000 * 0.0001 / 1000000,
        paper_value=18.0,
        paper_tolerance=0.05,
        verdict="符",
        notes="0.01% × 175B = 17.5M，与第 10 页的 18M 差 2.86%，属同一处四舍五入；与摘要的「10,000 times」一致（1/0.0001）。",
    ),
    dict(
        id="P-08", kind="paper-arithmetic",
        item="脚注 4 的存储账：350GB + 35MB×100 ≈ 354GB",
        source_locator="materials/source.txt 第 5 页（脚注 4）",
        page=5,
        quote=cut("4We still need the 350GB model", "4We still need the 350GB model", "35TB."),
        computation="350 + 35*100/1000",
        recomputed_value=350 + 35 * 100 / 1000,
        paper_value=354.0,
        paper_tolerance=0.005,
        verdict="符",
        notes="350 + 3.5 = 353.5 ≈ 354GB（论文向上取整到 354）。",
    ),
    dict(
        id="P-09", kind="paper-arithmetic",
        item="脚注 4 的 100×350GB ≈ 35TB",
        source_locator="materials/source.txt 第 5 页（脚注 4）",
        page=5,
        quote=cut("4We still need the 350GB model", "4We still need the 350GB model", "35TB."),
        computation="100*350/1000",
        recomputed_value=100 * 350 / 1000,
        paper_value=35.0,
        paper_tolerance=0.005,
        verdict="符",
        notes="100 × 350GB = 35,000GB = 35TB，与论文一致。",
    ),
    dict(
        id="P-16", kind="paper-arithmetic",
        item="由论文自己的公式（p.6）+ dmodel=12,288（p.2）+ 96 层（p.10）+ r=4，算出 |Θ| 并与 p.10 的「18M 预算」对齐",
        source_locator="materials/source.txt 第 6 页（公式）+ 第 2 页（12,288）+ 第 10 页（96 层 / r=4 / 18M）",
        page=6,
        quote=cut("LoRA adds trainable pairs", "LoRA adds trainable pairs", "we apply LoRA to."),
        computation="2*192*12288*4",
        recomputed_value=2 * 192 * 12288 * 4,
        paper_value=18000000.0,
        paper_tolerance=0.05,
        verdict="符",
        notes=("L_LoRA = 2 类权重（Wq,Wv）× 96 层 = 192 个矩阵，于是 |Θ| = 2×192×12288×4 = 18,874,368。"
               "论文 p.10 写「18M」，实算 18.87M，差 4.7%（论文写 18M、35MB 都是从**四舍五入后的 18M** 推的）。"
               "这条同时验证了「L_LoRA 是**全层累计**的矩阵数」这一读法——"
               "若按每层 2 个算，|Θ| 只有 0.2M，与论文的 18M 差 90 倍。"
               "两轮报告用的都是这个读法（见 P-19、P-21）。"),
    ),
    dict(
        id="P-17", kind="paper-arithmetic",
        item="LoRA 检查点的精确字节数（用 P-16 的精确 |Θ|）vs 论文写的 35MB",
        source_locator="materials/source.txt 第 10 页（18M / roughly 35MB）+ P-16 的精确 |Θ|",
        page=10,
        quote=cut("We set a parameter budget of 18M", "We set a parameter budget of 18M", "96 layers."),
        computation="2*192*12288*4*2/1048576",
        recomputed_value=2 * 192 * 12288 * 4 * 2 / 1048576,
        paper_value=35.0,
        paper_tolerance=0.08,
        verdict="符",
        notes=("精确 |Θ| = 18,874,368，FP16 下 37.75 MiB；论文写「roughly 35MB」"
               "（那是从四舍五入的 18M 算的：18M×2B = 36MB = 34.33 MiB）。"
               "差 7.9%，属论文自己的口径，不影响结论。"),
    ),
    dict(
        id="P-18", kind="paper-arithmetic",
        item="「checkpoint 缩小 10,000×」在精确 |Θ| 下是多少",
        source_locator="materials/source.txt 第 5 页（350GB→35MB, roughly 10,000×）+ P-16/P-17",
        page=5,
        quote=cut("With r = 4 and only the query and value", "With r = 4 and only the query and value", "35MB)4."),
        computation="350*1000/(2*192*12288*4*2/1048576)",
        recomputed_value=350 * 1000 / (2 * 192 * 12288 * 4 * 2 / 1048576),
        paper_value=10000.0,
        paper_tolerance=0.08,
        verdict="符",
        notes=("用论文自己的精确 |Θ| 算，缩小倍数是 9,282×，论文写「roughly 10,000×」。"
               "差 7.2%——**又是四舍五入的连锁**。引用「10,000×」没问题，"
               "但要知道它的分母是 35MB（舍入值）而不是 37.75MB（精确值）。"),
    ),
]

# Table 1 的六个百分比：逐个复算（表 1 的行列身份由作者侧几何重建确认，见 logs/author_table1_geom.txt）
T1 = [
    ("P-22", "AdapterL @ batch 32", "1449.4", "1482.0", 2.2),
    ("P-23", "AdapterH @ batch 32", "1449.4", "1492.2", 3.0),
    ("P-24", "AdapterL @ batch 16", "338.0", "354.8", 5.0),
    ("P-25", "AdapterH @ batch 16", "338.0", "366.3", 8.4),
    ("P-26", "AdapterL @ batch 1", "19.8", "23.9", 20.7),
    ("P-27", "AdapterH @ batch 1", "19.8", "25.8", 30.3),
]
for eid, what, base, val, stated in T1:
    ENTRIES.append(dict(
        id=eid, kind="paper-arithmetic",
        item="表 1 的 %s 相对延迟 %s%%" % (what, stated),
        source_locator="materials/source.txt 第 4 页（Table 1，延迟行）+ logs/author_table1_geom.txt（作者侧几何重建的行列身份）",
        page=4,
        quote=cut("%s±" % val, "%s±" % val, ")", occurrence=1),
        computation="(%s-%s)/%s*100" % (val, base, base),
        recomputed_value=(float(val) - float(base)) / float(base) * 100,
        paper_value=float(stated),
        paper_tolerance=0.03,
        round_to=1,
        verdict="符",
        notes="论文写 +%s%%，实算后四舍五入到 1 位小数一致。行列身份由作者侧按坐标重建确认（base 行=Fine-Tune/LoRA，val 行=AdapterL/AdapterH，列=batch 32/16/1）。" % stated,
    ))

# ---------------- 被测报告引用的数字，作者回头复算 ----------------
WS_V = ROOT / "runs" / "with-skill" / "verdict.md"
WS_C = ROOT / "runs" / "with-skill" / "claims.csv"
WO_V = ROOT / "runs" / "without-skill" / "verdict.md"
WO_C = ROOT / "runs" / "without-skill" / "claims.csv"
A1_V = ROOT / "runs" / "attempt1-with-skill-huoshan-429" / "verdict.md"
A1_C = ROOT / "runs" / "attempt1-with-skill-huoshan-429" / "claims.csv"

if WS_V.exists():
    VT = WS_V.read_text(encoding="utf-8")
    ENTRIES.extend([
        dict(
            id="P-19", kind="report-arithmetic",
            item="【会话引用】有 Skill 轮 INF-2：7B 的 |Θ| = 2×64×4096×8 = 4.19M",
            source_locator="runs/with-skill/verdict.md 第 3 节 INF-2",
            quote_file="runs/with-skill/verdict.md",
            quote=cut_in(VT, "INF-2：7B 全量微调放不进 24GB", "INF-2：7B 全量微调放不进 24GB", "每参数字节数是假设。"),
            computation="2*(2*32)*4096*8",
            recomputed_value=2 * (2 * 32) * 4096 * 8,
            paper_value=4194304.0,
            paper_tolerance=0.001,
            verdict="符",
            notes=("作者复算 = 4,194,304，与报告写的 4.19M 一致；"
                   "L_LoRA = 2 类 × 32 层 = 64（跨层累计），与 P-16 用论文自己的 18M 预算反推的读法一致。"),
        ),
        dict(
            id="P-20", kind="report-arithmetic",
            item="【会话引用】有 Skill 轮 INF-2：7B 全参微调 84GB、LoRA 基座 14GB",
            source_locator="runs/with-skill/verdict.md 第 3 节 INF-2",
            quote_file="runs/with-skill/verdict.md",
            quote=cut_in(VT, "INF-2：7B 全量微调放不进 24GB", "INF-2：7B 全量微调放不进 24GB", "每参数字节数是假设。"),
            computation="7e9*(2+2+4+4)/1000000000",
            recomputed_value=7e9 * (2 + 2 + 4 + 4) / 1e9,
            paper_value=84.0,
            paper_tolerance=0.01,
            verdict="符",
            notes=("2+2+4+4 = 12 B/参数（bf16 权重 2 + bf16 梯度 2 + AdamW m/v 各 4），× 7e9 = 84 GB —— 与报告一致。"
                   "LoRA 侧：7e9×2 = 14 GB + 4.19M×12 ≈ 50 MB ≈ 14.05 GB —— 与报告一致。"
                   "**这一轮的换算做得扎实**：算式、参数来源、假设都写明了。"),
        ),
        dict(
            id="P-28", kind="report-arithmetic",
            item="【会话引用】有 Skill 轮自己发现的两处论文口径不一致（3× vs 3.43×、25% vs 32.6%）",
            source_locator="runs/with-skill/verdict.md 第 4 节「核对时发现的论文自身不一致」",
            quote_file="runs/with-skill/verdict.md",
            quote=cut_in(VT, "摘要称显存需求降", "摘要称显存需求降", "与 25% 对不上。"),
            computation="(43.1/32.5-1)*100",
            recomputed_value=(43.1 / 32.5 - 1) * 100,
            paper_value=25.0,
            paper_tolerance=0.01,
            verdict="不符",
            notes=("**这一轮找到了**：正文 25% vs 脚注 5 推出的 +32.62%，以及摘要 3× vs 1.2TB→350GB 的 3.43×，"
                   "两处都写进了第 ④ 节「遗留」。"
                   "注意：**这是靠推理发现的，不是靠任何机械检查**——"
                   "`check_agreement.py` 对这两处都是 0 标记（引文逐字命中、数值 1% 内）。"),
        ),
    ])

if WO_V.exists():
    OT = WO_V.read_text(encoding="utf-8")
    ENTRIES.extend([
        dict(
            id="P-21", kind="report-arithmetic",
            item="【会话引用】无 Skill 轮 I2：7B 的 |Θ| = 2×64×4096×8 ≈ 4.2M、全参微调 84GB",
            source_locator="runs/without-skill/verdict.md 第 3 节",
            quote_file="runs/without-skill/verdict.md",
            quote=cut_in(OT, "7B LoRA 有条件可行", "7B LoRA 有条件可行", "小 batch 并实测。"),
            computation="7e9*(2+2+8)/1000000000",
            recomputed_value=7e9 * (2 + 2 + 8) / 1e9,
            paper_value=84.0,
            paper_tolerance=0.01,
            verdict="符",
            notes=("作者复算 = 84 GB，与报告写的 84 GB 一致；|Θ| = 2×64×4096×8 = 4,194,304 也与报告的「≈4.2 M」一致。"
                   "**对照轮在换算这一项上做得和有 Skill 那轮一样扎实**，甚至多给了一个锚点："
                   "「用论文锚点 1.2 TB/175B ≈ 6.9 B/参数 也得 ≈48 GB，都 > 24 GB」——"
                   "**这是用论文自己的数据给读者场景做绝对量闭合，正是 ledger 建议加进 Skill 的那条纪律。**"),
        ),
        dict(
            id="P-29", kind="report-arithmetic",
            item="【会话引用】无 Skill 轮也自己发现了「25% vs 32.6%」，并把表格数字降级为 undetermined",
            source_locator="runs/without-skill/verdict.md 第 4 节",
            quote_file="runs/without-skill/verdict.md",
            quote=cut_in(OT, "论文自身不一致", "论文自身不一致", "是舍入口径差异。"),
            computation="(43.1/32.5-1)*100",
            recomputed_value=(43.1 / 32.5 - 1) * 100,
            paper_value=25.0,
            paper_tolerance=0.01,
            verdict="不符",
            notes=("**对照轮也找到了**这处不一致（正文「25% speedup」 vs 脚注 32.5→43.1 tokens/s ≈ +32.6%），"
                   "并且**主动把 Table 3/Table 4 的数字降级为 undetermined**"
                   "（理由写得很清楚：「抽取文本是压平单元格序列、行列身份不保留，无法证明某数字属于哪行哪列，故不按出现顺序猜」）。"
                   "**结论：这处发现不能归因于 Skill**——有 Skill、无 Skill 都做到了。"),
        ),
    ])

if A1_V.exists():
    AT = A1_V.read_text(encoding="utf-8")
    ENTRIES.extend([
        dict(
            id="P-30", kind="report-arithmetic",
            item="【反例·归档的第一次有 Skill 运行】PF2「GPU memory 3x」与 PF8「1.2TB→350GB」并列而未调和",
            source_locator="runs/attempt1-with-skill-huoshan-429/claims.csv（PF2 与 PF8）",
            quote_file="runs/attempt1-with-skill-huoshan-429/claims.csv",
            quote=cut_in(A1_C.read_text(encoding="utf-8"), "PF2,", "PF2,", "GPU memory 3x.\",paper-fact"),
            computation="1200/350",
            recomputed_value=1200 / 350,
            paper_value=3.0,
            paper_tolerance=0.01,
            verdict="不符",
            notes=("**这一次漏了**：报告同时写了「GPU memory 3x」（逐字引自摘要）和「1.2TB→350GB」（逐字引自正文），"
                   "两者都是 paper-fact、checker 0 标记，但报告**没有把两者对上**（按它自己引的 PF8，比值是 3.43×）。"
                   "**这就是「机械检查全绿但语义不成立」的一个真实实例**。"),
        ),
        dict(
            id="P-31", kind="report-arithmetic",
            item="【反例·归档的第一次有 Skill 运行】自称「未发现论文摘要与正文、正文与脚注互相矛盾的数字」——该否定性断言为假",
            source_locator="runs/attempt1-with-skill-huoshan-429/verdict.md「预期行为对照 ②」",
            quote_file="runs/attempt1-with-skill-huoshan-429/verdict.md",
            quote=cut_in(AT, "核对时未发现论文摘要与正文", "核对时未发现论文摘要与正文", "部分满足（未发现不一致）。"),
            computation="(43.1/32.5-1)*100",
            recomputed_value=(43.1 / 32.5 - 1) * 100,
            paper_value=25.0,
            paper_tolerance=0.01,
            verdict="不符",
            notes=("报告写下了「未发现……互相矛盾的数字」这个**否定性断言**，"
                   "而作者侧证明论文第 5 页正文的 25% 与同页脚注 5 的 32.5→43.1 tokens/s（+32.6%）**就是**一处矛盾。"
                   "**否定性断言在整个流程里没有任何机械检查位**——模型说它查过了，机械层面拿不出任何证据。"
               ),
        ),
    ])

SEMANTIC = [
    dict(
        id="S-01",
        item="Table 1 的 |Θ| 行是 **adapter 层**的可训练参数量，不是 LoRA 的",
        source_locator="materials/source.txt 第 4 页（Table 1 + 表注）",
        computation="1",
        expected_value=1.0,
        tolerance=0.0,
        notes=("表注原文：「“|Θ|” denotes the number of trainable parameters in adapter layers.」"
               "（作者侧按坐标重建：|Θ| = 0.5M / 11M / 11M，分属 batch 32/16/1 三列）。"
               "抽取文本把表压平后，这一行紧跟在「Batch Size / Sequence Length」后面，"
               "**很容易被当成 LoRA 的可训练参数量**——而 LoRA 的 |Θ| 是另一个量级"
               "（GPT-3 175B 上 4.7M/37.7M，见第 8 页 Table 4）。"),
    ),
    dict(
        id="S-02",
        item="Table 12（第 21 页）的**行身份**在抽取文本里丢失",
        source_locator="materials/source.txt 第 21 页（Table 12）+ logs/author_table12_geom.txt",
        computation="1",
        expected_value=1.0,
        tolerance=0.0,
        notes=("抽取文本的顺序是：5 个行标签（Optimizer / Batch Size / # Epoch / Warmup Tokens / LR Schedule）"
               "先连着出现，**然后**才是它们的值（AdamW / 128 / 2 / 250,000 / Linear）。"
               "按位置读会把「128」当成 Optimizer 的值。"
               "作者侧按坐标重建的真值：Optimizer=AdamW、Batch Size=128、# Epoch=2、"
               "Warmup Tokens=250,000、LR Schedule=Linear；"
               "Learning Rate 一行：Fine-Tune=5.00E-06、PreEmbed=5.00E-04、PreLayer=1.00E-04、"
               "BitFit=1.6E-03、AdapterH=1.00E-04、LoRA=2.00E-04。"),
    ),
    dict(
        id="S-03",
        item="「LoRA 省显存 3×」是**相对降幅**，不能直接当成「24GB 单卡能跑 7B」的依据",
        source_locator="materials/source.txt 第 5 页 + 第 1 页",
        computation="350/1200*100",
        expected_value=29.166666666666668,
        tolerance=1e-9,
        notes=("1.2TB→350GB 意味着**冻结权重本身就要 350GB**（175B × 2B）。"
               "论文的 3.43× 是同一个 175B 模型上的降幅，"
               "把它搬到 7B/24GB 上时，基线显存本身就只有 14GB 量级、"
               "而 full fine-tune 的优化器状态才是大头。"
               "**报告若只写「LoRA 省显存 3×，所以 24GB 够用」，就是拿相对降幅当绝对可行性**——"
               "引文逐字命中、数值 1% 内、checker 0 标记，全绿，但结论不成立。"
               "（对照轮自己就写了这条：「3 倍显存节省不能直接套用……须按上面公式重算」——"
               "**这条纪律不需要 Skill 也会出现**，但 SKILL 里也确实没有它。）"),
    ),
    dict(
        id="S-04",
        item="论文的「25% speedup」与脚注 5 的口径差：差异确实存在（供 ledger 复核用）",
        source_locator="materials/source.txt 第 5 页",
        computation="(43.1/32.5-1)*100",
        expected_value=25.0,
        tolerance=1e-9,
        expect_differs=True,
        notes=("复算值 +32.6154% 与论文正文的 25% 确实不同（差 7.6 个百分点）。"
               "**这是本案例的「真问题」本体**：三次会话里 checker 都是 0 标记，"
               "两次会话发现了它、一次没有——"
               "**发现与否不取决于有没有 SKILL.md**。"),
    ),
]


def main() -> None:
    out = {
        "schema": "paper-case/ledger/v1",
        "case_id": "paper-case",
        "note": ("作者侧独立重算的数据层。引文按锚点从源文件切出，逐字节一致；"
                 "算式与复算值由 scripts/build_ledger.py 写入，"
                 "再由 scripts/verify_paper_results.py 重新求值复核。"),
        "entries": ENTRIES,
        "semantic_checks": SEMANTIC,
        "runs": [],
    }
    (ROOT / "ledger.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                                      encoding="utf-8", newline="\n")
    print("entries=%d semantic=%d" % (len(ENTRIES), len(SEMANTIC)))


if __name__ == "__main__":
    main()
