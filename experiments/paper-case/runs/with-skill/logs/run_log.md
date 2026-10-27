# 运行日志（失败 / 重试 / 人工修正全量留痕）

按时间顺序记录。所有操作只读材料或写入工作目录交付物，未改动 `materials/`、`skill/`、`scripts/` 下任何输入材料。

## 1. 环境自检

- 步骤：对 `materials/source.txt` 与 `skill/SKILL.md` 计算 SHA-256 与字节数。
- 尝试次数：1。
- 结果：两个哈希与任务书给定值完全一致（source.txt = a8f387d2…，82806 字节；SKILL.md = 7ec803cb…，13291 字节）。
- 处置：无需处理。

## 2. 读取任务书 / 材料声明 / 方法本体

- 步骤：先读 `cases/task-paper.md`、`materials/source_manifest.json`、`skill/SKILL.md`、`scripts/check_agreement.py`。
- 尝试次数：2。
- 第 1 次：PowerShell `Get-Content` 输出中文为乱码（控制台按 GBK 解码 UTF-8 内容），无法可靠读取字段表与硬性要求。
- 第 2 次：改用 Python 显式 UTF-8 输出（`sys.stdout` 重配）重读，全部内容正确解码。
- 处置：以第 2 次读取结果为准；材料字节本身未被修改。

## 3. 读取论文抽取文本

- 步骤：按 `=== PAGE n ===` 锚点把 `materials/source.txt` 分页通读（1–26 页）。
- 尝试次数：1。
- 结果：无错误；确认 26 页、82166 字符、2223 行。
- 处置：无需处理。

## 4. 引文定位与逐字校验

- 步骤：为 23 条拟作 `paper-fact` 的句子抽取候选引文，用 Python 做 `quote in source` 逐字连续子串校验。
- 尝试次数：1（一次性列出 23 条候选）。
- 结果：23/23 全部命中，含换行符，字节级一致。
- 处置：无需处理。

## 5. 写入 CSV 与复检

- 步骤：用 `apply_patch` 写入 `preconditions.csv`、`claims.csv`；随后用 `csv.DictReader` 复读并再次做引文子串校验。
- 尝试次数：1。
- 结果：33 行（23 paper-fact / 5 inference / 5 undetermined）、21 行前置条件；所有 paper-fact 引文仍为原文连续子串；无 CRLF 混入。
- 处置：无需处理。

## 6. 生成证据索引

- 步骤：从 `claims.csv` 的 paper-fact 行程序化导出 `evidence_index.json`（id/kind/locator/quote/sha256），sha256 取被引文件 `materials/source.txt` 的哈希。
- 尝试次数：1。
- 结果：23 条证据，逐条断言 quote 命中原文，无失败。
- 处置：无需处理。

## 7. 数值一致性自检

- 命令：`python scripts/check_agreement.py --claims claims.csv --preconditions preconditions.csv --source materials/source.txt --tolerance 0.01 --report logs/agreement.json`
- 尝试次数：1。
- 结果：退出码 0；33 条结论、0 个标记，`all_passed=True`；前置条件四类齐全、无「未定位且未标 absent」的行。
- 说明：终端 stdout 的中文提示出现乱码（同第 2 步的编码问题），但通过直接解析 `logs/agreement.json` 确认结果，不影响判定。
- 处置：0 标记，无行需要修正/删除；未发生被 checker 强制降级的情况。

## 8. 人工修正与降级决策

- 未对任何输入材料做人工修正。
- 分类降级均为「主动、一次性」判断而非 checker 报错后的返工：与 7B / 24GB / RTX 4090 相关的结论（显存换算、参数量换算、吞吐、质量、最优 rank、倍数是否成立）全部标为 `inference` 或 `undetermined`，因为论文没有 7B 或消费级显卡的实测数字；表内单元格数字（GPT-2 Table 11 配置）标为 `inferred` 并写明「表格压平、行列身份不保证」。
- 论文自身两处前后不一（3× vs 3.43× 显存、25% vs 32.6% 加速）未抹平，如实写入 `verdict.md` 第 4 节。

## 总结

- 失败/重试：1 次（第 2 步的读取编码问题），其余步骤一次通过。
- 人工修正：无输入材料修改；分类/降级为一次性判断，无返工。
- 交付物：`preconditions.csv`、`claims.csv`、`evidence_index.json`、`verdict.md`、`logs/agreement.json`、`logs/run_log.md` 均已生成。


---

## 作者侧处置（会话结束后补记；agent 自己写的内容以上未改动）

**会话结束时的状态**：会话自己已经跑过一次官方 checker（`logs/agreement.json` 存在）；作者又用同一命令复跑了一遍以留下可核对的 stdout。

作者的处置（按 Skill 第 7 步「不许写一个没跑过的检查的通过结论」）：
1. 作者用**逐字相同**的命令在**同一工作目录、同一份交付物**上补跑了官方脚本：

   ```bash
   python scripts/check_agreement.py --claims claims.csv --preconditions preconditions.csv \
       --source materials/source.txt --tolerance 0.01 --report logs/agreement.json
   ```

   结果：**退出码 0，33 条结论，标记 0 项**
   （stdout 见 `logs/check_agreement_stdout.txt`，报告见 `logs/agreement.json`）。
   **没有改动任何一行 claims.csv / preconditions.csv。**
2. 因此本轮满足「官方 checker 退出码 0」这一条，但**它是不是会话自己跑的那一次**，
   如实标注在 `comparison.md` 与 `ledger.md` 里。
3. 会话的失败痕迹**全部保留**：本文件、`logs/codex_events_raw.jsonl`、
   `logs/codex_stderr*.txt`、`logs/session_summary.json`，
   以及会话自己写的产出脚本（如有）。
