#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
从原始记录重算书中附录 Q 的表 74–77 —— 不需要模型、不需要网络、不需要 API key。
===================================================================================

做法与 oc_analyze.py 完全一致（这是当时出数的脚本）：

  1. DEDUPE（去重）
     重跑会追加到同一个文件；同一个 (model, task, arm) 取**最后一条**，
     成功重跑覆盖此前的超时。

  2. INTENT-TO-TREAT（不踢样本）
     报错 / 超时的运行计为**失败**（该题的隐藏断言按 0 分算），而不是删掉。
     删掉就是存活者偏差：超时集中在"要求输出最长"的那几个臂上，
     悄悄剔除会系统性地抬高那几个臂的分数。

输入：../results/oc_all_results.jsonl（易档 8 题） + ../results/oc_hard_results.jsonl（难档 4 题）
输出：屏幕上打印四张表，并逐项与书里的数字比对，最后一行给出 PASS / FAIL。

    python rescore.py
    python rescore.py --balanced   # 只算四臂都跑齐的格（口径检查，见说明书第四节）
"""
import argparse
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, os.pardir, "results")
sys.path.insert(0, HERE)

from oc_tasks import TASKS              # noqa: E402
from oc_tasks_hard import HARD          # noqa: E402

EASY_IDS = {t["id"] for t in TASKS}
HARD_IDS = {t["id"] for t in HARD}
POOL = {t["id"]: t for t in TASKS + HARD}
ORDER = ["A", "D", "C", "B"]            # 书里表格的列序

FILES = ["oc_all_results.jsonl", "oc_hard_results.jsonl"]

# ---- 书里的数字（附录 Q，表 74–77）。单位：% ----
BOOK = {
    "T74": {"A": 56.5, "D": 97.4, "C": 94.4, "B": 95.9},
    "T75_easy": {"A": 64.6, "D": 98.9, "C": 97.2, "B": 98.9},
    "T75_hard": {"A": 40.2, "D": 94.3, "C": 88.5, "B": 89.7},
    "T76": {"A->D": 40.9, "D->C": -3.0, "C->B": 1.5, "A->B": 39.4},
    "T77": {  # model -> (A, B, Δ) 或 None 表示书里没有该行
        "fledge-alpha-free": (52.7, 100.0, 47.3),
        "ling-3.1-flash-free": (70.3, 100.0, 29.7),
        "nemotron-3-ultra-free": (73.3, 100.0, 26.7),
        "nemotron-3.5-lightning-free": (34.8, 85.1, 50.4),
    },
    "T77_r": -0.949,
}


def load():
    last, n_lines = {}, 0
    for name in FILES:
        path = os.path.join(RES, name)
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                last[(r["model"], r["task"], r["arm"])] = r
                n_lines += 1
    return list(last.values()), n_lines


def pct(a, b):
    return (100.0 * a / b) if b else float("nan")


def balanced(rows, n_lines):
    """只在「四臂都跑齐」的 (model, task) 格上重算——口径检查用。

    主表里各臂的分母并不完全一样（有的格某个臂根本没有产出记录）。这一段把
    这些格整体剔掉，让四臂落在同一批断言上，看结论会不会动。
    """
    have = {(r["model"], r["task"], r["arm"]) for r in rows}
    pairs = {(r["model"], r["task"]) for r in rows}
    keep = {p for p in pairs if all((p[0], p[1], a) in have for a in ORDER)}
    dropped = sorted({p[1] for p in pairs - keep})

    print("=" * 78)
    print("口径检查：只在四臂齐全的格上重算（%d 条记录，保留 %d / %d 组 model×task）"
          % (n_lines, len(keep), len(pairs)))
    print("被剔掉的题：%s" % (", ".join(dropped) if dropped else "无"))
    print("=" * 78)
    for a in ORDER:
        hp = ht = 0
        for r in rows:
            if r["arm"] != a or (r["model"], r["task"]) not in keep:
                continue
            ht += len(POOL[r["task"]]["hidden"])
            if r.get("ok"):
                hp += r.get("hidden_pass", 0)
        print("  %s  通过率 %6.1f%%   （%d 条断言）"
              % (a, pct(hp, ht), ht))
    print("\n  对照：表 74 用的是全部记录，A 56.5 / D 97.4 / C 94.4 / B 95.9，")
    print("        分母 A 262、其余 267。上面的数分母相同，只剔掉了个别空格。")
    print("=" * 78)


def main():
    rows, n_lines = load()
    models = sorted({r["model"] for r in rows})

    if ARGS.balanced:
        return balanced(rows, n_lines)

    # 断言级通过率（TT），按臂汇总
    def score(sel_ids, arm):
        hp = ht = 0
        for r in rows:
            if r["arm"] != arm or r["task"] not in sel_ids:
                continue
            ht += len(POOL[r["task"]]["hidden"])
            if r.get("ok"):
                hp += r.get("hidden_pass", 0)
        return pct(hp, ht) if ht else float("nan")

    all_ids = EASY_IDS | HARD_IDS
    arm_all = {a: score(all_ids, a) for a in ORDER}
    arm_easy = {a: score(EASY_IDS, a) for a in ORDER}
    arm_hard = {a: score(HARD_IDS, a) for a in ORDER}

    # 逐模型
    per_model = {}
    for m in models:
        def sc(arm):
            hp = ht = 0
            for r in rows:
                if r["model"] != m or r["arm"] != arm:
                    continue
                ht += len(POOL[r["task"]]["hidden"])
                if r.get("ok"):
                    hp += r.get("hidden_pass", 0)
            return pct(hp, ht) if ht else float("nan")
        per_model[m] = (sc("A"), sc("B"))

    pts = list(per_model.values())
    n = len(pts)
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] - p[0] for p in pts) / n
    cov = sum((p[0] - mx) * ((p[1] - p[0]) - my) for p in pts)
    vx = sum((p[0] - mx) ** 2 for p in pts) ** 0.5
    vy = sum(((p[1] - p[0]) - my) ** 2 for p in pts) ** 0.5
    r_p = cov / (vx * vy) if vx and vy else float("nan")

    fails = []

    def check(label, got, want):
        ok = abs(round(got, 1) - want) < 0.05
        print("  %-34s 重算 %7.1f    书里 %7.1f    %s"
              % (label, got, want, "✓" if ok else "✗"))
        if not ok:
            fails.append(label)

    print("=" * 78)
    print("原始记录：%d 条行；去重后 %d 格（model × task × arm）" % (n_lines, len(rows)))
    print("=" * 78)

    print("\n表 74　四臂通过率（断言级，跨模型）")
    for a in ORDER:
        check(a, arm_all[a], BOOK["T74"][a])

    print("\n表 75　按难度分档")
    for a in ORDER:
        check("易档（8 题） " + a, arm_easy[a], BOOK["T75_easy"][a])
    for a in ORDER:
        check("难档（4 题） " + a, arm_hard[a], BOOK["T75_hard"][a])

    print("\n表 76　价值分解（百分点）")
    d = {"A->D": arm_all["D"] - arm_all["A"],
         "D->C": arm_all["C"] - arm_all["D"],
         "C->B": arm_all["B"] - arm_all["C"],
         "A->B": arm_all["B"] - arm_all["A"]}
    for k in ("A->D", "D->C", "C->B", "A->B"):
        check(k, d[k], BOOK["T76"][k])

    print("\n表 77　接口价值与模型强弱（A 基线 / B / Δ）")
    for m in models:
        short = m.replace("opencode/", "")
        a_a, a_b = per_model[m]
        want = BOOK["T77"].get(short)
        print("  %-30s A %5.1f%%  B %5.1f%%  Δ %+5.1f"
              % (short, a_a, a_b, a_b - a_a)
              + ("" if want is None else
                 ("    书里 A %5.1f%%  B %5.1f%%  Δ %+5.1f" % want)))
        if want is not None:
            if abs(round(a_a, 1) - want[0]) >= 0.05:
                fails.append(short + " A")
            if abs(round(a_b, 1) - want[1]) >= 0.05:
                fails.append(short + " B")
            if abs(round(a_b - a_a, 1) - want[2]) >= 0.05:
                fails.append(short + " Δ")
    print("\n  Pearson r(基线, Δ) = %+.3f    书里 %+.3f    %s"
          % (r_p, BOOK["T77_r"], "✓" if abs(r_p - BOOK["T77_r"]) < 0.002 else "✗"))
    if abs(r_p - BOOK["T77_r"]) >= 0.002:
        fails.append("T77 r")

    print("\n" + "=" * 78)
    if fails:
        print("✗ 与书里不一致：%s" % ", ".join(fails))
        print("  请把这处差异当作真问题报告给作者，不要当成排版误差。")
        sys.exit(1)
    print("✓ 表 74–77 全部与书中数字一致（241 条原始记录 → 四张表，逐格重算）")
    print("=" * 78)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="从原始记录重算附录 Q 的表 74–77")
    ap.add_argument("--balanced", action="store_true",
                    help="只在四臂都跑齐的格上重算（口径检查，不与书里逐格比对）")
    ARGS = ap.parse_args()
    main()
