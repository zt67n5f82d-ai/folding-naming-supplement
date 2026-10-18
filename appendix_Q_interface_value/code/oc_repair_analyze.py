#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Analyse oc_repair_results.jsonl -- does an explicit invariant+rollback
framing beat a generic "fix these failures" instruction?"""
import json
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "oc_repair_results.jsonl")


def load():
    rows = []
    with open(RES, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return [r for r in rows if r.get("ok")]


def num(s):
    try:
        a, b = s.split("/")
        return int(a), int(b)
    except Exception:
        return 0, 0


def main():
    rows = load()
    if not rows:
        print("no repair results"); return
    models = sorted({r["model"] for r in rows})
    tasks = sorted({r["task"] for r in rows})

    print("=" * 96)
    print("实验二：不变量驱动的回滚修复（第 1 轮用 π/α 契约，无示例）")
    print("=" * 96)
    print("%-34s %-6s %10s %10s %10s %10s" %
          ("model", "arm", "第1轮可见", "需修复率", "修复后隐藏", "修复后全对"))
    print("-" * 96)
    agg = defaultdict(lambda: dict(n=0, need=0, hp=0, ht=0, allp=0, out=0))
    for m in models:
        for arm in ("R-raw", "R-inv"):
            rs = [r for r in rows if r["model"] == m and r["repair"] == arm]
            if not rs:
                continue
            a = agg[(m, arm)]
            a["n"] = len(rs)
            a["need"] = sum(1 for r in rs if r.get("needs_repair"))
            for r in rs:
                hp, ht = num(r.get("final_hidden", "0/0"))
                a["hp"] += hp; a["ht"] += ht
                a["allp"] += 1 if r.get("final_hidden_all") else 0
                a["out"] += r.get("out2", 0)
            print("%-34s %-6s %10s %9.0f%% %9.1f%% %9.1f%%"
                  % (m.replace("opencode/", ""), arm,
                     "%.0f%%" % (100.0 * (1 - a["need"] / a["n"])),
                     100.0 * a["need"] / a["n"],
                     100.0 * a["hp"] / a["ht"] if a["ht"] else float("nan"),
                     100.0 * a["allp"] / a["n"]))
        print("-" * 96)

    print()
    print("=" * 96)
    print("跨模型汇总（仅统计**确实需要修复**的样本，配对比较）")
    print("=" * 96)
    # paired: same (model, task)
    pairs = defaultdict(dict)
    for r in rows:
        pairs[(r["model"], r["task"])][r["repair"]] = r
    tot = {"R-raw": [0, 0], "R-inv": [0, 0]}
    pairs_used = 0
    for k, v in pairs.items():
        if "R-raw" not in v or "R-inv" not in v:
            continue
        # a pair is informative if BOTH arms needed repair
        if not (v["R-raw"].get("needs_repair") and v["R-inv"].get("needs_repair")):
            continue
        pairs_used += 1
        for arm in ("R-raw", "R-inv"):
            hp, ht = num(v[arm].get("final_hidden", "0/0"))
            tot[arm][0] += hp; tot[arm][1] += ht
    for arm, label in (("R-raw", "通用改错指令 (\"请修正\")"),
                       ("R-inv", "不变量+回滚 (\"违反即重写\")")):
        p, t = tot[arm]
        print("  %-32s 修复后隐藏断言通过 %5.1f%%  (%d/%d)"
              % (label, 100.0 * p / t if t else float("nan"), p, t))
    if pairs_used:
        d = 100.0 * tot["R-inv"][0] / tot["R-inv"][1] - 100.0 * tot["R-raw"][0] / tot["R-raw"][1]
        print()
        print("  Δ(不变量 − 通用) = %+.1f pp   配对样本 = %d 对" % (d, pairs_used))
    else:
        print("  （没有配对样本：两条臂都需修复的样本为 0）")

    print()
    print("=" * 96)
    print("逐任务：第 1 轮（π/α 契约、无示例）的失败率与修复效果")
    print("=" * 96)
    print("%-18s %8s %10s %10s" % ("task", "样本", "第1轮需修复", "修复后全对"))
    for t in tasks:
        rs = [r for r in rows if r["task"] == t]
        if not rs:
            continue
        need = sum(1 for r in rs if r.get("needs_repair"))
        allp = sum(1 for r in rs if r.get("final_hidden_all"))
        print("%-18s %8d %9.0f%% %9.0f%%"
              % (t, len(rs), 100.0 * need / len(rs), 100.0 * allp / len(rs)))


if __name__ == "__main__":
    main()
