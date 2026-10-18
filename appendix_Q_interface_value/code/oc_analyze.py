#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Analyse the 4-arm experiment.

Two rigour rules are baked in:

1. DEDUPE -- re-runs append to the same file; the LAST record per
   (model, task, arm) wins, so a successful re-run supersedes a timeout.

2. INTENT-TO-TREAT -- a run that errored or timed out is scored as a
   FAILURE (0 of that task's hidden asserts), not dropped. Dropping them
   is survivorship bias: timeouts cluster on the arms that ask for the
   longest outputs, so silently discarding them flatters those arms.
"""
import json
import os
import sys
from collections import defaultdict

from oc_tasks import TASKS
from oc_tasks_hard import HARD

HARD_IDS = {t["id"] for t in HARD}
EASY_IDS = {t["id"] for t in TASKS}
POOL = {t["id"]: t for t in TASKS + HARD}

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "oc_ab_results.jsonl")
if len(sys.argv) > 1:
    RES = sys.argv[1]

ARM_LABEL = {
    "A": "A 裸模式 (只给目标+签名)",
    "D": "D 分层π/α (无示例、无I)",
    "C": "C 完整规格·平铺散文 (同信息量)",
    "B": "B 分层接口三元组 π/α/I",
}
ORDER = ["A", "D", "C", "B"]


def load():
    last = {}
    with open(RES, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                r = json.loads(line)
                last[(r["model"], r["task"], r["arm"])] = r
    return list(last.values())


def pct(a, b):
    return (100.0 * a / b) if b else float("nan")


def main():
    rows = load()
    if not rows:
        print("no results"); return
    models = sorted({r["model"] for r in rows})
    agg = defaultdict(lambda: dict(hp=0, ht=0, tasks_all=0, tasks=0,
                                   out=0, el=0.0, rounds=0.0, n=0, dead=0))
    # intent-to-treat: failed/missing runs count as 0 / len(hidden)
    for r in rows:
        k = (r["model"], r["arm"])
        a = agg[k]
        ht = len(POOL[r["task"]]["hidden"])
        if r.get("ok"):
            hp = r.get("hidden_pass", 0)
            a["out"] += (r.get("tokens") or {}).get("output", 0)
            a["el"] += r.get("elapsed", 0)
            a["rounds"] += r.get("rounds", 0)
        else:
            hp = 0
            a["dead"] += 1
        a["hp"] += hp
        a["ht"] += ht
        a["tasks"] += 1
        a["tasks_all"] += 1 if (r.get("ok") and r.get("hidden_all")) else 0
        a["n"] += 1

    print("=" * 100)
    print("真实 LLM 实验（本地 OpenCode server · 免费模型）· 判定=隐藏断言，超时/报错计为失败")
    print("=" * 100)
    print("%-34s %-4s %9s %9s %9s %9s %8s %6s"
          % ("model", "arm", "assert%", "all-pass", "out_tok", "elapsed", "rounds", "超时"))
    print("-" * 100)
    for m in models:
        for arm in ORDER:
            a = agg.get((m, arm))
            if not a:
                continue
            print("%-34s %-4s %8.1f%% %8.1f%% %9.0f %8.1fs %8.2f %6d"
                  % (m.replace("opencode/", ""), arm,
                     pct(a["hp"], a["ht"]), pct(a["tasks_all"], a["tasks"]),
                     a["out"] / max(1, a["n"] - a["dead"]),
                     a["el"] / max(1, a["n"] - a["dead"]),
                     a["rounds"] / max(1, a["n"] - a["dead"]), a["dead"]))
        print("-" * 100)

    armm = {}
    print()
    print("=" * 100)
    print("对比（跨模型平均，断言级通过率，ITT）")
    print("=" * 100)
    for arm in ORDER:
        hp = sum(agg[(m, arm)]["hp"] for m in models if (m, arm) in agg)
        ht = sum(agg[(m, arm)]["ht"] for m in models if (m, arm) in agg)
        armm[arm] = pct(hp, ht)
        print("  %-34s %6.1f%%   (n=%d asserts)" % (ARM_LABEL[arm], armm[arm], ht))
    print()
    print("  A -> D   完整契约散文的价值         : %+6.1f pp" % (armm["D"] - armm["A"]))
    print("  D -> C   具体示例的价值             : %+6.1f pp" % (armm["C"] - armm["D"]))
    print("  C -> B   分层形式本身的价值(等信息)  : %+6.1f pp" % (armm["B"] - armm["C"]))
    print("  A -> B   本书模式总增益             : %+6.1f pp" % (armm["B"] - armm["A"]))

    print()
    print("=" * 100)
    print("统一律检验：接口价值 ∝ 1/模型能力  →  基线越弱，Δ(B-A) 应越大")
    print("=" * 100)
    print("%-34s %10s %10s %10s" % ("model", "A基线", "B", "Δ(B-A)"))
    pts = []
    for m in models:
        if (m, "A") not in agg or (m, "B") not in agg:
            continue
        aA = pct(agg[(m, "A")]["hp"], agg[(m, "A")]["ht"])
        aB = pct(agg[(m, "B")]["hp"], agg[(m, "B")]["ht"])
        pts.append((aA, aB - aA))
        print("%-34s %9.1f%% %9.1f%% %+9.1f pp"
              % (m.replace("opencode/", ""), aA, aB, aB - aA))
    if len(pts) >= 3:
        n = len(pts)
        mx = sum(p[0] for p in pts) / n
        my = sum(p[1] for p in pts) / n
        cov = sum((p[0] - mx) * (p[1] - my) for p in pts)
        vx = sum((p[0] - mx) ** 2 for p in pts) ** 0.5
        vy = sum((p[1] - my) ** 2 for p in pts) ** 0.5
        r = cov / (vx * vy) if vx and vy else float("nan")
        print()
        print("  Pearson r(基线, Δ) = %+.3f   %s"
              % (r, "支持统一律（负相关）" if r < -0.3 else
                 ("与统一律方向相反" if r > 0.3 else "无明显相关（不足以支持）")))

    print()
    print("=" * 100)
    print("分难度层（断言级通过率，跨模型，ITT）")
    print("=" * 100)
    print("%-12s %10s %10s %10s %10s" % ("tier", *ORDER))
    for tier, ids in (("易 (8题)", EASY_IDS), ("难 (4题)", HARD_IDS)):
        cells = []
        for arm in ORDER:
            hp = ht = 0
            for r in rows:
                if r["arm"] != arm or r["task"] not in ids:
                    continue
                t = len(POOL[r["task"]]["hidden"])
                ht += t
                hp += r.get("hidden_pass", 0) if r.get("ok") else 0
            cells.append("%9.1f%%" % pct(hp, ht) if ht else "        -")
        print("%-12s %s" % (tier, " ".join(cells)))

    print()
    print("=" * 100)
    print("逐任务：hidden 断言通过率（ITT）")
    print("=" * 100)
    per = defaultdict(lambda: [0, 0])
    for r in rows:
        t = len(POOL[r["task"]]["hidden"])
        per[(r["task"], r["arm"])][1] += t
        per[(r["task"], r["arm"])][0] += r.get("hidden_pass", 0) if r.get("ok") else 0
    tasks = sorted({r["task"] for r in rows}, key=lambda t: (t not in EASY_IDS, t))
    print("%-18s %8s %8s %8s %8s" % ("task", *ORDER))
    for t in tasks:
        cells = []
        for arm in ORDER:
            v = per.get((t, arm))
            cells.append("%7.0f%%" % pct(v[0], v[1]) if v and v[1] else "      -")
        print("%-18s %s" % (t, " ".join(cells)))


if __name__ == "__main__":
    main()
