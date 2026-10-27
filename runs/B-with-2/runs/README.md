# runs/ · 运行过程留痕（脚本 + 日志 + 失败记录）

> 失败、重试、人工修正**全部保留**，未删除任何一次尝试。

## 一、生产脚本（按执行顺序）

| 脚本 | 作用 | 产出 |
|---|---|---|
| `00_env_and_hashes.py` | 环境快照 + 全部输入文件 SHA-256 | `logs/00_env_and_hashes.{json,txt}` |
| `01_build_artifacts.py` | **从原始字节**切引文（行号由字节自算，每条带 start_marker 断言）；生成证据索引与两张表 | `evidence_index.json`、`claims.csv`、`preconditions.csv`、`preconditions_fit.csv`、`quote_resolution.json`、`precondition_numeric_policy.json` |
| `01a_fix_inner_quotes.py` | 修复脚本里中文文案内误用的 ASCII 双引号（**规则过宽，误伤了定界符，已废弃，见下**） | `logs/01a_quote_fix.log` |
| `01b_fix_inner_quotes.py` | 回滚 01a 后重做（**未排除三引号文档串，仍失败**） | `logs/01b_quote_fix.log` |
| `01c_fix_inner_quotes.py` | 最终版：字符串状态机 + CJK 邻近判定 | `logs/01c_quote_fix.log` |
| `02_verify_quotes.py` | **独立**校验：引文在原始字节/文本视图下连续命中、行号与 locator 一致、与证据索引一致、分类合法、前置条件四类齐全、依赖 ID 不悬空 | `logs/quote_verification.json` |
| `03_derive_values.py` | 把 inference 里的算术全部复算（参数量、LR 缩放、评测步数、整除断言、缓冲字节、注意力 FLOPs、显存数量级） | `logs/derive_values.{json,txt}` |
| `04_run_check_agreement.py` | 调用 skill 自带 `check_agreement.py`，**三次尝试全部记录** | `logs/04_check_agreement_attempts.txt`、`logs/agreement_official_raw.json`、`source_combined.txt` |
| `05_numeric_crosscheck.py` | 逐个数值算相对误差（claims + preconditions），三种核对策略 | `logs/numeric_crosscheck.json` |
| `06_patch_preconditions.py` | 依据数值核对暴露的问题回改 PRE 规格（行区间、字面短语、表达式展开） | `logs/06_patch_preconditions.log` |
| `07_merge_agreement.py` | 官方判定逐字段原样保留 + 补充核对另起一栏；断言官方字段未被改动 | `logs/agreement.json`、`logs/agreement_official_snapshot.json` |
| `08_summary.py` | 写 verdict 前的事实摘录（防止手写数字出错） | 控制台 |
| `09_write_verdict.py` | 生成 `verdict.md`：引文由 `[[EV-xxx]]` 占位**从证据索引注入**，并断言每条在原文命中 | `verdict.md` |
| `10_write_manifest.py` | 写 `manifest.json`（供 B-P10 / B-P11 核对） | `manifest.json` |
| `11_acceptance_selfcheck.py` | 按 `cases/acceptance-B.md` 的 B-P1..B-P12 + 2 项附加逐条自检 | `logs/acceptance_selfcheck.json` |
| `12_cleanroom_repro.py` | 干净目录重跑（只带 cases/ + materials/ + skill/ + 脚本），比对产物是否逐字节一致 | `logs/cleanroom_repro.json` |

## 二、失败与处置（全部保留）

| # | 现象 | 根因 | 处置 |
|---|---|---|---|
| F1 | `python3 scripts/check_agreement.py ...` → **exit 9009** | 本机 `python3` 是 WindowsApps 空壳，不是解释器 | 改用真解释器 `python`；失败原文保留在 `logs/04_check_agreement_attempts.txt` 的 4a 段 |
| F2 | 同上命令（用 `python`）→ **exit 2**，`error: the following arguments are required: --source` | SKILL.md 第 7 步的命令**漏了脚本的必填参数 `--source`** | 按脚本 docstring 补 `--source`；两处失败均保留 |
| F3 | 脚本只接受单个 `--source`，但材料是 4 个独立文件 | 工具限制 | 构造 `source_combined.txt` 原样拼接 4 份原文；引文均为**单行**，落在任一文件内部，拼接不破坏连续性 |
| F4 | `01_build_artifacts.py` 首次运行 **SyntaxError**（`invalid character '，'`） | 中文文案内部用了 ASCII `"` 做引号，Python 字符串提前闭合 | 写了 3 轮修复脚本（01a→01b→01c）；01a/01b 各自失败的原因也保留在日志里；最终版用**字符串状态机**排除三引号文档串、转义引号、字符串前缀，并要求引文紧邻 CJK 语境 |
| F5 | 修复脚本把**字符串定界符**也改成了中文引号（`note="...口径"),` → `...口径“),`） | 01a 规则只看「前一个字符是不是 CJK」 | 01b/01c 改为状态机判定；每一次的错误输出都留在 `logs/01a~01c_*.log` |
| F6 | 前置条件校验串 `not count compilation` 断言失败 | 原文是 `we don't count compilation` | 断言当场报错（这正是它该做的）；改成 `count compilation` |
| F7 | `02_verify_quotes.py` 报 21 条 `quote_on_non_fact` | 题面规定 `quote` **只给 paper-fact 填**，我给 inference/undetermined 也填了 | 改 builder：非 paper-fact 行 `quote` 留空，`locator` 仍指向支撑行，引文全文留在 `evidence_index.json` |
| F8 | `03_derive_values.py` 复算的参数量 41,944,592 ≠ 文档 50.3 M | 我的 MLP 参数公式少算了一个矩阵（`4n²` 写成 `8n²`），且 ve_gate 被重复计入 | 修正公式 → 50,332,176，与文档 50.3 的相对误差 0.06% |
| F9 | 我先前判断「dataloader 预分配缓冲是显存瓶颈」 | 算错了数量级：默认配置下该缓冲只有 **4 MiB**，不是 GB | 由 D6 纠正；并把真正的瓶颈改判为**激活 + fp32 logits**（D8/D9） |
| F10 | 数值核对报 `PC-C11` 超容差、`PC-D08` 超容差、`PC-H05` 假通过 | 前两条是**定位行里没有那个数字** / 原文用下划线写 `1_000_000_000`；第三条是只取了 value 里第一个数字 | 核对脚本升级为「value 里**每个**数字都要在所指行命中」+ 去下划线 + 行区间支持；`PC-C11` 等改为行区间定位，`PC-H05/PC-D04/PC-H14` 标为表达式策略（字面量在原文 + 求值对账） |
| F11 | `PC-D02` 报「1」未命中 | value 里「1 个验证分片」是我自己的措辞，原文写的是 `always pinned` | 改写 value，不再写原文没有的数字 |
| F12 | `05_numeric_crosscheck.py` 的 `safe_eval` 抛异常 | 自写的正则漏了 `**` 里的 `*` 组合，导致 `2**19` 求值失败并把 `literal_token_found` 一起置 False | 改用 Python 原生 `**` 求值；复核后 `2**19=524288`、`40*524288=20971520`、`2**14=16384` 全部对账通过 |
| F13 | 依赖前置条件 ID `PC-A10` **悬空**（3 条结论引用了一个不存在的 ID） | 起草时编号写错 | 新增 `02_verify_quotes.py` 的 V8 完整性检查（自动抓出），改指 `PC-C03;PC-C04` / `PC-C04;PC-H01` / `PC-D09;PC-A09` |
| F14 | B-P6 自检一度 FAIL | 自检脚本按**全文**统计四选一词，把 ④/⑦ 里作为三分类名的 `undetermined` 也算了进去；而验收标准的判定方式写明是「检查第 ① 节」 | 按标准把检查收敛到第 ① 节；同时把 §7 里多余出现的另一个结论词改写；全文 token 普查写进自检 detail 里 |
| F15 | 干净目录重跑时 `02_verify_quotes.py` 报 `FileNotFoundError: logs/...` | 干净目录没建 `logs/` | 在 `12_cleanroom_repro.py` 里预建 `logs/`；重跑后 5 个产物**逐字节一致** |

## 三、核对结论一览

| 检查 | 结果 | 文件 |
|---|---|---|
| 引文程序化命中（原始字节 + 文本视图） | 43/43 通过，findings=0 | `logs/quote_verification.json` |
| skill 自带 `check_agreement.py` | exit 0，64 条结论 **0 标记** | `logs/agreement_official_raw.json` |
| 逐值相对误差 | claims 21 个 + preconditions 44 个，**超容差 0、未处置 0** | `logs/agreement.json`（`numeric_agreement` 栏） |
| 验收标准 B-P1..B-P12 + 2 项附加 | **14/14 通过** | `logs/acceptance_selfcheck.json` |
| 干净目录重跑 | 5 个产物**逐字节一致** | `logs/cleanroom_repro.json` |

## 四、被冻结文件（本次运行**未修改**，仅读取）

`cases/task-B.md`（SHA-256 `934b5e32a63da60a727ff29d3bc44df2b1baa83d8142104cd4b76b4ec3a01a3a`）、
`cases/acceptance-B.md`（SHA-256 `67c7ac92329f1205ec16519598b32223232c0674d6f375d730a0dd79d813136d`）、
`skill/SKILL.md`（SHA-256 `0d048c99959f59b3de51204cac23593f952588359e2c85bf7f759bfbe9a60ade`）、
`skill/scripts/check_agreement.py`（SHA-256 `1f1ee51288dc01d1f88ba95d532987a7f2d668a6d66ac3b72951950371ab0f2a`）。

> `cases/acceptance-B.md` 第四节「冻结清单」里 task/acceptance/Skill 三个哈希与冻结时间为**空白**。
> 本次运行**没有修改该文件**，而是把三个哈希与 Skill 版本标识写进了 `manifest.json`
> （`manifest.json.input_files_check` 与 `manifest.json.skill`），供评审方直接取用。
