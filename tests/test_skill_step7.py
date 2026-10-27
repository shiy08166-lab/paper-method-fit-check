#!/usr/bin/env python3
"""paper-method-fit-check 的**文档命令自检**（确定性，不联网、不调模型）。

为什么要有这个测试
------------------
`SKILL.md` 第 7 步把一条**要读者照抄的命令**写在正文里。v1.0 的这条命令漏了
`check_agreement.py` 的**必填**参数 `--source`，照抄必然得到 argparse 的 `exit 2`。
这是**读者第一次执行 Skill 就会撞上的**失败，而且它不会自己暴露——除非有人真的把
文档里的命令抽出来跑一遍。

这个测试做的正是这件事：
  1. **从 SKILL.md 正文里解析出第 7 步的 bash 命令**（不是手抄一份），
  2. 在临时目录里用**真实产物**（claims.csv / preconditions.csv / materials/source.txt）搭好工作区，
  3. **原样执行**这条命令，
  4. 断言退出码 == 0。

用法
----
    python3 tests/test_skill_step7.py                 # 测当前 SKILL.md
    python3 tests/test_skill_step7.py --skill <path>  # 测指定 SKILL.md
    python3 tests/test_skill_step7.py --all           # 同时测 v1.0 固件（预期失败）与当前版（预期通过）

退出码：0 = 全部符合预期；1 = 有用例不符预期（并打印实际输出）。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent                       # submission/ 根
FIXTURE_V10 = HERE / "fixtures" / "skill_v1.0_step7.sh"

# 真实产物（C 案例严格对称复测那一轮）
REAL_RUN = PKG / "runs" / "C-with-3"
REAL_MATERIAL = PKG / "paper_materials" / "nanochat_README_table_corrupted.md"


def extract_step7_command(skill_md: Path) -> list[str]:
    """从 SKILL.md 正文里解析第 7 步的 bash 命令（返回 argv 列表）。

    解析规则：找到 '### 7.' 小节里的第一个 ```bash 代码块，
    去掉行尾续行符 '\\'，按 shell 词法切分。
    """
    text = skill_md.read_text(encoding="utf-8")
    m = re.search(r"^###\s*7\..*?```(?:bash|sh|shell)\n(.*?)```", text, re.S | re.M)
    if not m:
        raise SystemExit("SKILL.md 里找不到第 7 步的 bash 代码块")
    block = m.group(1)
    flat = " ".join(line.rstrip().rstrip("\\").strip() for line in block.splitlines())
    flat = flat.strip()
    if not flat:
        raise SystemExit("第 7 步的代码块是空的")
    argv = shlex.split(flat, posix=True)
    return argv


def build_workspace(tmp: Path) -> None:
    """搭出命令要用的工作区：scripts/ + 真实产物 + materials/。"""
    (tmp / "scripts").mkdir(parents=True, exist_ok=True)
    shutil.copy2(PKG / "scripts" / "check_agreement.py", tmp / "scripts" / "check_agreement.py")
    shutil.copy2(REAL_RUN / "claims.csv", tmp / "claims.csv")
    shutil.copy2(REAL_RUN / "preconditions.csv", tmp / "preconditions.csv")
    (tmp / "materials").mkdir(parents=True, exist_ok=True)
    shutil.copy2(REAL_MATERIAL, tmp / "materials" / "source.txt")


def run_command(argv: list[str], tmp: Path) -> tuple[int, str, str]:
    cmd = list(argv)
    if cmd and cmd[0] in ("python3", "python"):
        cmd[0] = sys.executable
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run(cmd, cwd=str(tmp), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env, timeout=120)
    return r.returncode, r.stdout or "", r.stderr or ""


def case(label: str, argv: list[str], expect_rc: int) -> dict:
    with tempfile.TemporaryDirectory(prefix="step7_") as td:
        tmp = Path(td)
        build_workspace(tmp)
        rc, out, err = run_command(argv, tmp)
    return {
        "label": label,
        "argv": argv,
        "expected_rc": expect_rc,
        "actual_rc": rc,
        "passed": rc == expect_rc,
        "stdout": out.strip()[:600],
        "stderr": err.strip()[:600],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill", default=str(PKG / "paper-method-fit-check" / "SKILL.md"))
    ap.add_argument("--all", action="store_true", help="同时测 v1.0 固件与当前版")
    args = ap.parse_args()

    results = []
    if args.all:
        if FIXTURE_V10.exists():
            argv10 = shlex.split(FIXTURE_V10.read_text(encoding="utf-8").replace("\\\n", " "),
                                  posix=True)
            results.append(case("v1.0（固件：文档命令缺 --source）", argv10, expect_rc=2))
        else:
            print("缺少固件 %s" % FIXTURE_V10)
    skill = Path(args.skill)
    argv_now = extract_step7_command(skill)
    results.append(case("%s（当前版：文档命令原样抽出来跑）" % skill.name, argv_now, expect_rc=0))

    print("=" * 92)
    print("SKILL.md 第 7 步命令自检")
    print("=" * 92)
    for r in results:
        print("\n[%s] %s" % ("PASS" if r["passed"] else "FAIL", r["label"]))
        print("  命令    : %s" % " ".join(r["argv"]))
        print("  期望退出码 %s，实际 %s" % (r["expected_rc"], r["actual_rc"]))
        if r["stdout"]:
            print("  stdout  : %s" % r["stdout"].replace("\n", " | ")[:300])
        if r["stderr"]:
            print("  stderr  : %s" % r["stderr"].replace("\n", " | ")[:300])
    bad = [r for r in results if not r["passed"]]
    print("\n结论：%d / %d 个用例符合预期" % (len(results) - len(bad), len(results)))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
