# QUICKSTART —— 一次跑通（`paper-method-fit-check`）

> **为什么有这份文件**：`SKILL.md` 第 7 步的示例命令**漏了必填参数 `--source`**，直接照抄会得到
> `argparse` 的 `exit 2`（本作品案例 B 的独立复测实测到这一失败，原始输出见
> `runs/B-with-2/runs/README.md` 的 F2）。
>
> 为**不改动已锁定的 `skill_version`**（它 = `SKILL.md` 的 SHA-256，改动会使 B/C 案例的
> 「同一版本」校验失效），我们没有修改 `SKILL.md`，而是在这里给出补齐参数后的完整命令。
> `SKILL.md` 的**文字要求**（第 7 步：跑数值一致性自检、每个标记都要有处置）本身是完整且正确的。

## 1. 数值 / 引文一致性自检

```bash
python3 scripts/check_agreement.py \
    --claims claims.csv \
    --preconditions preconditions.csv \
    --source materials/nanochat_README.md \
    --tolerance 0.01 \
    --report logs/agreement.json
```

- `--source` **必填**：论文/文档原文的路径。脚本要在原文里检索每条 `quote` 是否为连续子串，
  所以必须指向你实际引用的那份原文。
- 材料有多份时，把它们**合并成一份**再传（合并时保持每份原文的原始字节，不要做行尾归一化，
  否则原文里的 CRLF 片段会检索不到）。
- 退出码 `0` = 全部通过；`1` = 存在未处置的标记。

## 2. 会话轨迹导出（把宿主原生记录转成可核查的可见对话文本）

```bash
python3 scripts/export_session_text.py \
    --session "<宿主原生 messages.jsonl>" \
    --out runs/<run-id>/session-export.txt
```

导出只包含用户输入与助手可见输出，不含内部推理与系统提示词，凭据类字符串按导出器规则脱敏；
文件头会写出来源 SHA-256，评审可直接比对原会话。

## 3. 用量抽取（累计 token 口径）

```bash
python3 scripts/extract_usage_v2.py \
    --session "<宿主原生 messages.jsonl>" \
    --label <run-id>
```

**口径说明（重要）**：本脚本输出的是**所有模型调用 `usage.totalTokens` 的累加**（含 `cacheRead`），
即该次运行的真实总消耗。它与「单次调用的 `totalTokens`」不同 —— 后者是**峰值上下文规模**，
主要由会话轮数决定，**不能用来算单位成本**。任何效率对比都请用累计口径，并注明口径。

## 4. 产物清单

| 文件 | 内容 |
|---|---|
| `preconditions.csv` | 硬前置条件，四类齐全；每条必带 `source_locator` 或 `confidence=absent` + 原因 |
| `claims.csv` | 关键结论；`classification` ∈ `paper-fact` / `inference` / `undetermined`；后两类的 `quote` 必须留空 |
| `evidence_index.json` | 逐条引文 + 定位 + 文件/引文 SHA-256 |
| `verdict.md` | 四段：结论 / 原文确证 / 我的推断 / 遗留问题；结尾给出下一步阅读指向 |
| `logs/agreement.json` | 数值一致性自检结果与每条标记的处置 |

完整方法与设计取舍见 `README.md`。
