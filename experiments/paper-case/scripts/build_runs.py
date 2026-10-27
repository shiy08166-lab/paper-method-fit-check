#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""装配两次运行的同条件工作区。

唯一变量 = **给不给 SKILL.md**：
  * runs/with-skill/   多一个 skill/SKILL.md，提示词多一句「再读 skill/SKILL.md 并按它的工作流做」
  * runs/without-skill/ 其余完全相同（任务书、材料、脚本、提示词逐字相同，只删掉 skill 相关的那几行）

装配内容（两侧逐字一致的部分由本脚本从同一批冻结文件复制，复制后哈希必然相同）：
  cases/task-paper.md      ← 冻结的 cases/task-paper.md
  materials/source.txt     ← 冻结的 materials/source.txt
  materials/source_pages.json
  materials/source_manifest.json
  scripts/check_agreement.py ← 作品仓库 scripts/check_agreement.py

用法（在 experiments/paper-case/ 下运行）：
    python scripts/build_runs.py
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPO = ROOT.parents[1]          # ai-github-work/repo
SRC_MATERIALS = ROOT / "materials"
FROZEN_TASK = ROOT / "cases" / "task-paper.md"
SKILL = REPO / "paper-method-fit-check" / "SKILL.md"
CHECKER = REPO / "scripts" / "check_agreement.py"

SOURCE_SHA = "a8f387d278213370e3b7705539545292188a7c44ba185875f83c373a36b5984d"
SOURCE_BYTES = 82806
SKILL_SHA = "7ec803cb2f547c340515e3e5a0e04cc447d5b4348e7585e892d41d8fb35d79f3"

PROMPT_TEMPLATE = """本次任务的附件已经装配在工作目录里，目录布局如下：

  cases/task-paper.md            任务书（读者约束、材料性质声明、事先写明的 5 条预期行为、交付物字段表、硬性要求）
  materials/source.txt           论文 PDF 的逐页抽取文本（页与页之间有 `=== PAGE n ===` 页码锚点）
  materials/source_pages.json    同一份文本按页切分的机器可读版本
  materials/source_manifest.json 来源 URL / 版本 / 许可证 / SHA-256 / **抽取规则与已知限制**
  scripts/check_agreement.py     数值一致性自检脚本
{skill_layout}
先做环境自检（只读，不要改材料）：

```bash
python -c "import hashlib,pathlib; [print(p, hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest(), pathlib.Path(p).stat().st_size) for p in [{hash_list}]]"
```

`materials/source.txt` 的 SHA-256 必须是 `{source_sha}`（{source_bytes} 字节）{skill_hash_line}
**如果对不上，请停下来说明，不要自行修改材料。**

装配完成后：
- 先读 `cases/task-paper.md`（读者约束、材料性质声明、事先写明的 5 条预期行为、交付物字段表、硬性要求）；
- 再读 `materials/source_manifest.json` 里的**抽取规则与已知限制**（抽取文本和作者手写原文不是一回事）；
{skill_read}

交付物（写到工作目录里，字段见 `cases/task-paper.md` 的「你要交付什么」表）：

  preconditions.csv / claims.csv / evidence_index.json / verdict.md / logs/agreement.json

几条硬要求：
1. 引文必须是 `materials/source.txt` 的**逐字连续片段**（能朴素子串搜索命中），**含换行符**；
   不要转述、不要拼接、不要改大小写、不要把跨行的词合起来。
2. `paper-fact` 行才带 `quote` 与 `locator`；`inference` / `undetermined` 行的 `quote` 与 `numeric_value`
   **必须留空**，推理过程写进 `reasoning` 列。
3. 表格在抽取文本里是**压平**的单元格序列。引用表格里的数字时必须说明它对应**哪一行、哪一列**；
   确实无法确定就降级为 `undetermined` 并写明原因，**不要按出现顺序猜**。
4. 落到读者场景（24 GB 单卡 + 7B）的任何换算都要给**算式、参数来源和假设**，并标为 `inference`。
5. 最后跑一次数值一致性自检：

   ```bash
   python scripts/check_agreement.py --claims claims.csv --preconditions preconditions.csv --source materials/source.txt --tolerance 0.01 --report logs/agreement.json
   ```

   （`--source` 必填；退出码 0 = 全部通过；有 flag **不要删行**，要么改、要么降级为 `inference`、
   要么写进 `verdict.md` 第 4 段作为原文自身的不一致。）
6. 把**失败与重试**写进 `logs/run_log.md`（哪一步试了几次、报了什么错、怎么改的）。

只做「判断」，不要跑训练、不要下载数据集、不要联网（除上面已列出的命令外）。
"""

SKILL_LAYOUT = "  skill/SKILL.md                 方法本体（8 步工作流 + 6 条 Validation + 8 条 Failure modes）\n"

WITH_SKILL_EXTRA = """- 再读 `skill/SKILL.md`（方法本体：8 步工作流 + 6 条 Validation + 8 条 Failure modes），
  然后按 `skill/SKILL.md` 的工作流完成这个任务。"""
WITHOUT_SKILL_EXTRA = "- 然后按 `cases/task-paper.md` 的要求完成这个任务。"


def sha256_of(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_prompt(with_skill: bool) -> str:
    if with_skill:
        return PROMPT_TEMPLATE.format(
            skill_layout=SKILL_LAYOUT,
            hash_list="'materials/source.txt', 'skill/SKILL.md'",
            source_sha=SOURCE_SHA,
            source_bytes=SOURCE_BYTES,
            skill_hash_line="；`skill/SKILL.md` 的 SHA-256 必须是 `%s`。" % SKILL_SHA,
            skill_read=WITH_SKILL_EXTRA,
            skill_ref="`skill/SKILL.md` 的工作流",
        )
    return PROMPT_TEMPLATE.format(
        skill_layout="",
        hash_list="'materials/source.txt'",
        source_sha=SOURCE_SHA,
        source_bytes=SOURCE_BYTES,
        skill_hash_line="。",
        skill_read=WITHOUT_SKILL_EXTRA,
        skill_ref="`cases/task-paper.md` 的要求",
    )


def assemble(run_dir: pathlib.Path, with_skill: bool) -> None:
    for sub in ("cases", "materials", "scripts", "logs"):
        (run_dir / sub).mkdir(parents=True, exist_ok=True)
    shutil.copyfile(FROZEN_TASK, run_dir / "cases" / "task-paper.md")
    shutil.copyfile(SRC_MATERIALS / "source.txt", run_dir / "materials" / "source.txt")
    shutil.copyfile(SRC_MATERIALS / "source_pages.json", run_dir / "materials" / "source_pages.json")
    shutil.copyfile(SRC_MATERIALS / "source_manifest.json", run_dir / "materials" / "source_manifest.json")
    shutil.copyfile(CHECKER, run_dir / "scripts" / "check_agreement.py")
    if with_skill:
        (run_dir / "skill").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SKILL, run_dir / "skill" / "SKILL.md")
    (run_dir / "prompt.txt").write_text(build_prompt(with_skill), encoding="utf-8", newline="\n")


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--dest-root", default="", type=pathlib.Path,
                    help="装配目标根目录；默认是 experiments/paper-case/runs。"
                         "会话实际在一个**隔离副本**里跑（避免对照轮从父目录翻到作品仓库里的 SKILL.md），"
                         "产物再按字节复制回 runs/ 下。")
    args = ap.parse_args()
    runs_root = args.dest_root if args.dest_root else (ROOT / "runs")
    runs_root.mkdir(parents=True, exist_ok=True)

    report = {}
    for name, with_skill in (("with-skill", True), ("without-skill", False)):
        run_dir = runs_root / name
        if run_dir.exists():
            shutil.rmtree(run_dir)
        assemble(run_dir, with_skill)
        files = {}
        for p in sorted(run_dir.rglob("*")):
            if p.is_file():
                files[str(p.relative_to(run_dir)).replace("\\", "/")] = {
                    "bytes": p.stat().st_size,
                    "sha256": sha256_of(p),
                }
        report[name] = files

    # 逐项比对：两次运行除 skill/ 与 prompt.txt 外必须完全一致
    a = report["with-skill"]
    b = report["without-skill"]
    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    diff = sorted(k for k in set(a) & set(b) if a[k]["sha256"] != b[k]["sha256"])
    out = {
        "schema": "paper-case/run_workspace/v1",
        "note": "两次运行的差异清单：除 skill/SKILL.md 与 prompt.txt 外必须逐字节一致。",
        "dest_root": str(runs_root),
        "files": report,
        "only_in_with_skill": only_a,
        "only_in_without_skill": only_b,
        "content_differs": diff,
        "identical_except_skill_and_prompt": (diff == ["prompt.txt"] and only_a == ["skill/SKILL.md"] and not only_b),
    }
    (runs_root / "workspace_diff.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: out[k] for k in
                      ("only_in_with_skill", "only_in_without_skill", "content_differs",
                       "identical_except_skill_and_prompt")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
