先做环境准备：本次任务的附件在 `upload/` 目录下（`task-C.md`、`material-corrupted.md`、`check_agreement.py`）。请装配成下面这个目录布局：

```bash
mkdir -p cases materials scripts logs
cp upload/task-C.md cases/task-C.md
cp upload/material-corrupted.md materials/nanochat_README_table_corrupted.md
cp upload/material-corrupted.md materials/source.txt
cp upload/check_agreement.py scripts/check_agreement.py
ls -la cases materials scripts
sha256sum materials/source.txt
```

材料 `materials/source.txt` 的 SHA-256 必须是 `64a46d328926d45842d9e8ad0a1817b01d176ad915e55ba92609119ca571917c`（17623 字节）。**如果对不上，请停下来说明，不要自行修改材料。**

装配完成后，把 `materials/source.txt` 当作**只读材料**处理：读 `cases/task-C.md`（读者约束、材料的合成声明、事先写明的 5 条预期行为、交付物字段表、硬性要求），然后按任务书完成这个任务。

交付物（写到工作目录里，字段见 `cases/task-C.md` 的「你要交付什么」表）：
  preconditions.csv / claims.csv / evidence_index.json / verdict.md / logs/agreement.json

几条硬要求：
1. 引文必须是**原文的逐字连续片段**（能朴素子串搜索命中，且只命中一次），不要转述、不要拼接。
2. `paper-fact` 行才带 `quote` 与 `locator`；`inference` / `undetermined` 行的 `quote` 与 `numeric_value` **必须留空**，推理过程写进 `reasoning` 列。
3. 材料顶部的合成声明块声明了 4 个破坏点，但声明本身**可能与实测不符**——请以**实测**为准，并把差异写进 verdict.md。
4. 最后跑一次数值一致性自检：
   python3 scripts/check_agreement.py --claims claims.csv --preconditions preconditions.csv --source materials/source.txt --tolerance 0.01 --report logs/agreement.json
   （`--source` 必填；退出码 0 = 全部通过；有 flag 不要删行，要么改、要么降级为 inference、要么写进 verdict.md 第 4 段作为原文自身的不一致。）
5. 报告里请保留**失败与重试**（哪一步试了几次、报了什么错、怎么改的）。

只做「判断」，不要跑训练、不要下载数据集、不要联网（除上面已列出的装配命令外）。

完成时给出：结论词、三分类各多少条、降级条数、5 条预期行为各做到了几条、实际耗时、最不确定的一点。
