#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Analyse oc_repair2_results.jsonl -- does an invariant+rollback framing beat a
generic "fix these failures" instruction, inside a LOOP?

Why a v2 analyser exists: the v1 analyser (`oc_repair_analyze.py`) reads fields
(`needs_repair`, `final_hidden`, `final_hidden_all`, `out2`, `r1v`, `r1h`) that
the v1 data file does not always contain, and it filters on `ok` first -- so
every R-raw unit killed by the v1 KeyError bug silently vanished, and the
headline table reported "R-raw: 0% need repair". That is survivorship bias.
This analyser works off the v2 nested schema (row["arms"][arm]) and never
drops a unit without saying so.

Design of the v2 experiment (see oc_repair2.py):
  * round 1: BARE prompt (arm A) -- run ONCE per (model, task, repeat)
  * if round 1 already passes the VISIBLE oracle -> nothing to repair
  * otherwise BOTH arms repair the SAME failure, with IDENTICAL information
    (failing assertions + full pi/alpha contract), differing ONLY in framing
  * score = HIDDEN oracle after the repair

So the informative sample is the set of units where round 1 failed, and every
such unit yields a genuine PAIR.
"""
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "oc_repair2_results.jsonl")
ARMS = ("R-raw", "R-inv")
LABEL = {"R-raw": '通用改错指令 ("请修正")', "R-inv": '不变量+回滚 ("违反即重写")'}


def num(s):
    try:
        a, b = str(s).split("/")
        return int(a), int(b)
    except Exception:
        return 0, 0


def load(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def exact_binom_two_sided(k, n):
    """Exact two-sided sign-test p-value (binomial, p=0.5)."""
    if n == 0:
        return float("nan")
    from math import comb
    total = 2 ** n
    obs = comb(n, k)
    p = sum(comb(n, i) for i in range(n + 1) if comb(n, i) <= obs) / total
    return min(1.0, p)


def wilcoxon_like(diffs):
    """Return (n_nonzero, n_positive, sign-test p) for paired differences."""
    d = [x for x in diffs if x != 0]
    n = len(d)
    k = sum(1 for x in d if x > 0)
    return n, k, exact_binom_two_sided(k, n)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else RES
    if not os.path.exists(path):
        print("no results file:", path)
        return
    rows = load(path)
    print("=" * 100)
    print("实验二（v2，配对设计）：不变量驱动的回滚修复 —— 第 2 轮改错的效果")
    print("=" * 100)
    print("数据文件：%s" % os.path.basename(path))
    print("记录总数：%d" % len(rows))

    bad = [r for r in rows if not r.get("ok")]
    print("执行失败（err）的记录：%d %s" % (
        len(bad), sorted({r.get("err", "")[:60] for r in bad})[:3] if bad else ""))
    ok = [r for r in rows if r.get("ok") and "arms" in r]
    print("可用于分析：%d" % len(ok))

    models = sorted({r["model"] for r in ok})
    tasks = sorted({r["task"] for r in ok})

    # ---------- 1. 第 1 轮基线 ----------
    print()
    print("-" * 100)
    print("1. 第 1 轮基线（裸模式 arm A，无 π/α 契约，无示例）")
    print("-" * 100)
    print("%-34s %10s %12s %12s" % ("model", "样本", "可见断言通过", "隐藏断言通过"))
    for m in models:
        rs = [r for r in ok if r["model"] == m]
        vp = sum(num(r["round1_visible"])[0] for r in rs)
        vt = sum(num(r["round1_visible"])[1] for r in rs)
        hp = sum(num(r["round1_hidden"])[0] for r in rs)
        ht = sum(num(r["round1_hidden"])[1] for r in rs)
        print("%-34s %10d %11.1f%% %11.1f%%" % (
            m.replace("opencode/", ""), len(rs),
            100.0 * vp / vt if vt else 0, 100.0 * hp / ht if ht else 0))
    fail_units = [r for r in ok if not r["round1_visible_all"]]
    print()
    print("第 1 轮可见断言未全通过（= 需要修复）的单元：%d / %d（%.0f%%）" % (
        len(fail_units), len(ok), 100.0 * len(fail_units) / len(ok) if ok else 0))

    # ---------- 2. 配对比较（只取真正需要修复的单元） ----------
    print()
    print("-" * 100)
    print("2. 配对比较：同一个失败，两种改错说法（信息完全相同，只有措辞不同）")
    print("-" * 100)
    pairs = [r for r in fail_units if all(a in r["arms"] for a in ARMS)]
    print("配对单元数：%d" % len(pairs))
    if not pairs:
        print("（没有配对单元，无法比较）")
        return

    agg = {a: dict(hp=0, ht=0, allp=0, n=0) for a in ARMS}
    diffs_assert = []
    diffs_allpass = []
    for r in pairs:
        row = {}
        for a in ARMS:
            hp, ht = num(r["arms"][a].get("final_hidden"))
            agg[a]["hp"] += hp
            agg[a]["ht"] += ht
            agg[a]["allp"] += 1 if r["arms"][a].get("final_hidden_all") else 0
            agg[a]["n"] += 1
            row[a] = (hp, ht, bool(r["arms"][a].get("final_hidden_all")))
        diffs_assert.append(row["R-inv"][0] - row["R-raw"][0])
        diffs_allpass.append(int(row["R-inv"][2]) - int(row["R-raw"][2]))

    print()
    print("%-32s %12s %14s %12s" % ("改错说法", "修复后隐藏断言", "修复后全对率", "样本"))
    for a in ARMS:
        d = agg[a]
        print("%-32s %11.1f%% %13.1f%% %12d" % (
            LABEL[a], 100.0 * d["hp"] / d["ht"] if d["ht"] else float("nan"),
            100.0 * d["allp"] / d["n"] if d["n"] else float("nan"), d["n"]))
    d_pp = (100.0 * agg["R-inv"]["hp"] / agg["R-inv"]["ht"]
            - 100.0 * agg["R-raw"]["hp"] / agg["R-raw"]["ht"])
    print()
    print("  Δ(不变量 − 通用)，断言级 = %+.1f pp" % d_pp)
    n, k, p = wilcoxon_like(diffs_assert)
    print("  配对符号检验（断言级）：非零差 %d 对，其中 %d 对偏向“不变量”  p = %.3f"
          % (n, k, p))
    n2, k2, p2 = wilcoxon_like(diffs_allpass)
    print("  配对符号检验（全对率）：非零差 %d 对，其中 %d 对偏向“不变量”  p = %.3f"
          % (n2, k2, p2))

    # ---------- 3. 逐模型 ----------
    print()
    print("-" * 100)
    print("3. 逐模型（配对单元）")
    print("-" * 100)
    print("%-34s %6s %14s %14s %10s" % ("model", "配对", "通用改错", "不变量+回滚", "Δ pp"))
    for m in models:
        ps = [r for r in pairs if r["model"] == m]
        if not ps:
            continue
        cells = []
        for a in ARMS:
            hp = sum(num(r["arms"][a].get("final_hidden"))[0] for r in ps)
            ht = sum(num(r["arms"][a].get("final_hidden"))[1] for r in ps)
            cells.append(100.0 * hp / ht if ht else float("nan"))
        print("%-34s %6d %13.1f%% %13.1f%% %+9.1f" % (
            m.replace("opencode/", ""), len(ps), cells[0], cells[1], cells[1] - cells[0]))

    # ---------- 4. 逐任务 ----------
    print()
    print("-" * 100)
    print("4. 逐任务（配对单元）")
    print("-" * 100)
    print("%-18s %6s %14s %14s %10s" % ("task", "配对", "通用改错", "不变量+回滚", "Δ pp"))
    for t in tasks:
        ps = [r for r in pairs if r["task"] == t]
        if not ps:
            continue
        cells = []
        for a in ARMS:
            hp = sum(num(r["arms"][a].get("final_hidden"))[0] for r in ps)
            ht = sum(num(r["arms"][a].get("final_hidden"))[1] for r in ps)
            cells.append(100.0 * hp / ht if ht else float("nan"))
        print("%-18s %6d %13.1f%% %13.1f%% %+9.1f" % (
            t, len(ps), cells[0], cells[1], cells[1] - cells[0]))

    # ---------- 5. ITT 口径（不剔除"无需修复"的单元） ----------
    print()
    print("-" * 100)
    print("5. ITT 口径：把“第 1 轮就通过”的单元也计入（第 2 轮视作不改变）")
    print("-" * 100)
    itt = {a: dict(hp=0, ht=0, allp=0, n=0) for a in ARMS}
    for r in ok:
        for a in ARMS:
            if a not in r["arms"]:
                continue
            d = r["arms"][a]
            if d.get("needs_repair"):
                hp, ht = num(d.get("final_hidden"))
            else:
                hp, ht = num(r.get("round1_hidden"))
            itt[a]["hp"] += hp
            itt[a]["ht"] += ht
            itt[a]["allp"] += 1 if (d.get("final_hidden_all") if d.get("needs_repair")
                                    else r.get("round1_visible_all") and hp == ht) else 0
            itt[a]["n"] += 1
    for a in ARMS:
        d = itt[a]
        print("%-32s 隐藏断言 %6.1f%%  全对 %5.1f%%  n=%d" % (
            LABEL[a], 100.0 * d["hp"] / d["ht"] if d["ht"] else float("nan"),
            100.0 * d["allp"] / d["n"] if d["n"] else float("nan"), d["n"]))

    print()
    print("=" * 100)
    print("读法提醒：样本只有 %d 个配对单元、%d 个模型，且全是免费小模型。"
          % (len(pairs), len(models)))
    print("本表能说明“在这个设置下两种说法的差别有多大”，不能外推到 GPT/Claude 级模型。")
    print("=" * 100)


if __name__ == "__main__":
    main()
