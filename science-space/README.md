# 玻尔科学空间 · 一次真实实践（会话 `35822cccea564cf59cf21`）

> 这是**本次分享里唯一一段在玻尔平台内真实跑出来的实践**。它要回答一个具体问题：
> **同一份方法、同一份材料，换一个完全不同的执行系统，结论还站得住吗？**

## 1. 环境与配置方法

| 项 | 值 |
|---|---|
| 平台 | 玻尔科学空间（网页端 `www.bohrium.com`，会话面板 `/agent-widget/`） |
| 会话 | `35822cccea564cf59cf21`（`https://www.bohrium.com/agent-widget/35822cccea564cf59cf21`） |
| 运行位置 | 玻尔云端（会话内选"玻尔云端"），工作目录 `/bohr-workspace` |
| Python | 3.12.4（会话第 0 轮环境自检实测） |
| 附件 | `upload/` 下：`SKILL.md`、`task-C.md`、`material-corrupted.md`、`check_agreement.py` |
| 布局 | 按包内 CLI 运行的同一套四层布局装配：`cases/` + `materials/` + `skill/` + `scripts/` |

**装配命令**（会话第 1 轮实际发出的第一段，见 `prompt-turn1.md`）：

```bash
mkdir -p cases materials skill scripts logs
cp upload/task-C.md cases/task-C.md
cp upload/material-corrupted.md materials/nanochat_README_table_corrupted.md
cp upload/material-corrupted.md materials/source.txt
cp upload/SKILL.md skill/SKILL.md
cp upload/check_agreement.py scripts/check_agreement.py
sha256sum materials/source.txt skill/SKILL.md
```

**输入字节校验**：装配后模型自己先算了哈希——`materials/source.txt` = `64a46d32…1917c`（17,623 B）、
`cases/task-C.md` = `e364bf2a…45ae8`、`scripts/check_agreement.py` = `1f1ee512…9a0f2a`。
**云端读到的任务书、材料、自检脚本与包内冻结输入逐字节一致**；唯一差别是 Skill 用了 **v1.1**
（v1.0 的第 7 步命令补上 `--source`，见 `tests/test_skill_step7.py`）。

**取件通道实测**（会话第 0 轮只做环境自检，不碰材料；逐条试了三条 GitHub 取件通道）：

| 通道 | 玻尔云端内实测 |
|---|---|
| `https://ghproxy.net/https://raw.githubusercontent.com/…` | ✅ http=200，17,623 B，SHA-256 与权威副本一致 |
| `https://api.github.com/…/contents/…` | ❌ 30 s 超时（rc=28） |
| `https://cdn.jsdelivr.net/gh/…` | ⚠️ 301（未跟 `-L`），直接取会拿到重定向页 |

结论：**在玻尔云端里取 GitHub 原文要走 ghproxy**。这次实际没用到下载通道（附件直接挂载即可），
这条是"下次要拉大文件时哪条能用"的实测。第 0 轮是环境脚手架，不是案例的一部分，故其提示词与输出不随包
（其**结论**即上表，已逐项写在这里）。

## 2. 实际过程（两轮，提示词与完整答案逐字随包）

| 轮次 | 提示词 | 答案 | 做了什么 |
|---|---|---|---|
| 第 1 轮 · 主任务 | `prompt-turn1.md` | `answer-turn1.md` | 装配 → 读任务书与 Skill → 产出 5 个交付物 → 跑数值自检 → 失败重试 3 次 → 0 标记 |
| 第 2 轮 · 残余错误审查 | `prompt-turn2.md` | `answer-turn2.md` | **只读**复核上一轮产物：挑错 + 独立复测 5 条预期行为 + 只列不修 |

## 3. 结果（逐项对照见正文 §7 的跨系统表）

- **结论词：`transferable-with-changes`** —— 与包内两次 CLI 运行**逐字相同**。
- 交付物：结论 22 条（12/5/5）、前置条件 14 条（3 条 `absent`）、引文索引 12 条、结论文档四段 + 异常处理对照 + 失败留痕。
- 官方自检：`check_agreement.py` 共跑 **3 次**（1 → 1 → 0 标记）；第一版草稿与其报告**没有删除**。
- **5 条预期行为**：第 1 轮自评 5/5；**第 2 轮自审下调为「4 条完全做到 + 第 ④ 条部分做到」**（根因见 `author-verification.md` §5）。

## 4. 开发经验（3 条，都是这次真踩出来的；正文 §7 有摘要版）

1. **官方 checker 查不出"引文在原文出现多次"。** 第一版的 `"$48"` 在原文里命中 2 次，`check_agreement.py` 放过了它
   （它只验"连续子串"）。模型自己补了一道"命中恰好 1 次"的自检（`logs/quote_check_v2.json`）。
   → 与包内 `scripts/check_agreement.py` 的已知盲点同源：**"唯一命中"该做成 checker 的内建检查**。
2. **CRLF 会伪装成"行号全错"。** 模型第一版复核脚本用 `read_text` 读源文件，CRLF 被折成 `\n`，
   按 `\r\n` 切分只得到 1 行，于是 12 条 locator 全部显示 L1；改用 `read_bytes` 后 12 条行号全部对上。
   → 与包内 §4.1 记的是**同一个坑的两次独立发作**（我们踩在生成侧，它踩在校验侧）。
3. **`check_agreement.py` 验的是格式，不是语义。** `numeric_value=80` 取自 `SM 80+`（算力等级，不是量值），
   因为"这个数出现在引文里"就放行了。→ 数值字段还需要一层语义约束（包内逐值核对里 C11/C18 同理）。

## 5. 三条纪律的落实

1. **提示词逐字保留**：两轮提示词与两轮完整最终答案都在本目录，**未摘要、未截断**。
2. **完整最终答案不摘要**：第 2 轮那条 13,691 B 的残余错误清单原样保留，包括它对自己的 4 处自我修正。
3. **作者验证要写差评**：见 `author-verification.md`——我逐条复核了云端的 16 处原文引用，
   并对它列出的 16 条残余错误逐条给出我的判断。

## 6. 未随包的部分与原因

云端工作区里还有 5 个交付物文件本体（`preconditions.csv` / `claims.csv` / `evidence_index.json` / `verdict.md` /
`logs/agreement.json`）与两个中间产物。**它们没有随包**：一是被赛题的"去掉冗长"要求管着（材料包文本上限 240 KiB），
二是它们的**内容已逐字出现在本目录两轮答案正文里**（条数、分类计数、checker 字段、失败与重试过程），
三是作者已对其中可核验的部分做了独立复核（`author-verification.md` + `author-verification-cites.csv`）。
云端会话链接与平台未披露项登记在 `provenance.json`。

**如实声明**：本轮**没有**运行训练、没有下载数据集；联网仅限上表那 3 条通道探测（材料靠附件挂载）。
模型名称与调用成本**平台界面未披露**，故不写（见 provenance.json）。
