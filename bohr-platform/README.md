# 玻尔科学空间 · 平台侧原始记录（随包）

这两个会话是本次**玻尔生态实践**的平台侧一手记录（不是二次整理的转述）；`science-space/` 是我整理过的可读版，
两者互补。

| 会话 | 角色 | 平台侧原始记录（随包） |
|---|---|---|
| `35822cccea564cf59cf21` | 玻尔云端 / Python 3.12.4，同一份材料、同一套交付物契约 | `prompts/turn-01…turn-04.md`（**每轮提示词逐字原文**）、`session.json`（会话 id、消息数、创建/更新时间戳、模型与运行环境）、`workspace/agreement.json`（云端那一轮的结论台账） |
| `3f8b9c490d384432b0a65` | 同一平台第二次会话（对照复跑） | `prompts/turn-01.md`（**提示词逐字原文**） |

**未随包（均在公开仓库同路径，核验不需要）**：`*/artifacts.json`（artifact 清单）、`*/prompts/index.json`、
`*/workspace/index.json`、`*/workspace/agreement_v1.json`（上一版台账）、`*/workspace/quote_check_v2.json`、
`*/workspace/table_measure.txt`、`*/author-recheck/`（复核留痕）、第二次会话的 `session.json`。
按官方「材料范围与容量」要求（去掉与本次结论无关的冗长内容）未随包提供；
本包内保留的是**能核到「方法怎么用、跑了什么、结论是什么」的最小完整集**：提示词原文 + 会话元数据 + 云端结论台账。

**边界**：平台**未披露模型名称与调用成本**，故本包不写这两个数字；会话可见对话文本与原生轨迹分开放，未混同。
未随包的部分与原因见 `science-space/README.md` 第 6 节。
