# -*- coding: utf-8 -*-
"""
第 16–17 章 FSM 验证器：完备性、安全性、活跃性、不变量 + 随机压力 + 幂等压缩
================================================================================

模型来源（全部取自书里印出来的表）：
  · 管理 FSM（第 16 章）：4 个状态 × 6 个事件 = 24 格，见书里表 30。
  · 横切 FSM（第 17 章）：7 个状态 × 6 个事件 = 42 格，见书里图 18（主链 + 升级分支）
    与表 32（同一事件在不同状态下的处理）。
  · 四类属性：完备性、安全性、活跃性、不变量，见书里表 31。

它做三件事：
  1) 静态检查：把转移矩阵逐格填满，再按四类属性逐条核对（17 项）
  2) 随机压力：两个 FSM 各跑 n 条随机轨迹 × m 步（默认 5000 × 20），统计未定义转移
  3) 幂等压缩：把书里那条 11 步轨迹压成 8 步，并核对折掉的正好是 3 处重复

输出是确定的：同一个随机种子，同一台机器上跑两遍，输出逐字节相同。

    python fsm_verify.py                     # 默认：19 项检查 + 5000×20
    python fsm_verify.py --n 20000           # 加大压力
    python fsm_verify.py --out run.txt       # 同时写文件，便于与存档 diff
"""
import argparse
import io
import json
import random
import sys

SEED = 20261018
N_TRAJ = 5000
STEPS = 20
REJECT = "REJECT"

# ============================================================================
# 管理 FSM —— 书里表 30（4 状态 × 6 事件）
# 列序：升级 / 核心离职 / 项目结束 / 报告正常 / 报告风险 / 报告预警
# ============================================================================
M_STATES = ["GREEN", "YELLOW", "RED", "CLOSED"]
M_EVENTS = ["escalation", "member_resign", "project_end",
            "report_green", "report_red", "report_yellow"]

M_TABLE = {
    "CLOSED": ["REJECT", "REJECT", "CLOSED", "REJECT", "REJECT", "REJECT"],
    "GREEN":  ["REJECT", "RED",    "CLOSED", "GREEN",  "YELLOW", "YELLOW"],
    "RED":    ["RED",    "RED",    "REJECT", "YELLOW", "RED",    "RED"],
    "YELLOW": ["RED",    "RED",    "CLOSED", "GREEN",  "REJECT", "YELLOW"],
}

# ============================================================================
# 横切 FSM —— 书里图 18（主链 + 升级分支）+ 表 32（阶段内幂等、阶段外拒绝）
# 主链：IDLE → DETECTED → CONTAINED → RECOVERED → REVIEWED → CLOSED
# 升级分支：DETECTED → ESCALATED → CONTAINED
# ============================================================================
X_STATES = ["IDLE", "DETECTED", "CONTAINED", "ESCALATED", "RECOVERED", "REVIEWED", "CLOSED"]
X_EVENTS = ["detect", "contain", "escalate", "recover", "review", "close"]

X_TABLE = {
    # detect      contain    escalate   recover    review     close
    "IDLE":      ["DETECTED", "REJECT",   "REJECT",   "REJECT",   "REJECT",   "REJECT"],
    "DETECTED":  ["DETECTED", "CONTAINED", "ESCALATED", "REJECT",  "REJECT",   "REJECT"],
    "CONTAINED": ["REJECT",   "CONTAINED", "ESCALATED", "RECOVERED", "REJECT", "REJECT"],
    "ESCALATED": ["REJECT",   "CONTAINED", "ESCALATED", "REJECT",  "REJECT",   "REJECT"],
    "RECOVERED": ["REJECT",   "REJECT",   "REJECT",   "RECOVERED", "REVIEWED", "REJECT"],
    "REVIEWED":  ["REJECT",   "REJECT",   "REJECT",   "REJECT",   "REVIEWED", "CLOSED"],
    "CLOSED":    ["REJECT",   "REJECT",   "REJECT",   "REJECT",   "REJECT",   "REJECT"],
}

# 书里 17.4 那条轨迹（11 个状态步）
TRAIL = ["IDLE", "DETECTED", "CONTAINED", "CONTAINED", "ESCALATED", "CONTAINED",
         "RECOVERED", "RECOVERED", "REVIEWED", "REVIEWED", "CLOSED"]

BUSINESS_EVENTS = ["detect", "contain", "escalate", "recover", "review"]


# ---------------------------------------------------------------- 基础设施
def build(states, events, table):
    """把按行写的表展开成 (状态, 事件) -> 目标 的字典；顺带查缺格。"""
    m = {}
    missing = []
    for s in states:
        row = table.get(s)
        if row is None or len(row) != len(events):
            missing.append((s, "*"))
            continue
        for e, tgt in zip(events, row):
            if tgt is None or tgt == "":
                missing.append((s, e))
            else:
                m[(s, e)] = tgt
    return m, missing


def step(m, s, e):
    return m.get((s, e))


def reachable(m, states, events, src, dst):
    """src 能否到达 dst（广度优先）。"""
    seen = {src}
    frontier = [src]
    while frontier:
        nxt = []
        for s in frontier:
            for e in events:
                t = step(m, s, e)
                if t is None or t == REJECT:
                    continue
                if t == dst:
                    return True
                if t not in seen:
                    seen.add(t)
                    nxt.append(t)
        frontier = nxt
    return src == dst


def random_walk(m, states, events, n_traj, steps, seed):
    """n 条随机轨迹，每条 steps 步；返回 (未定义转移数, 落进死状态的轨迹数)。"""
    rng = random.Random(seed)
    undefined = 0
    deadend = 0
    for _ in range(n_traj):
        s = states[0]
        stuck = False
        for _ in range(steps):
            e = rng.choice(events)
            t = step(m, s, e)
            if t is None:
                undefined += 1
                break
            if t == REJECT:
                # 显式拒绝不是未定义转移：状态不变，继续走
                continue
            s = t
        # 死状态：除终态外，任何事件都出不去
        if s not in ("CLOSED",) and not any(
                (step(m, s, e) not in (REJECT,)) for e in events):
            stuck = True
        if stuck:
            deadend += 1
    return undefined, deadend


def compress(trail):
    """幂等压缩：把连续重复的状态折成一个。"""
    out = []
    for s in trail:
        if not out or out[-1] != s:
            out.append(s)
    return out


# ---------------------------------------------------------------- 检查
class Suite:
    def __init__(self):
        self.n = 0
        self.failed = []

    def check(self, name, ok, detail=""):
        self.n += 1
        print("[%s] %02d %s%s" % ("PASS" if ok else "FAIL", self.n, name,
                                  (" · " + detail) if detail else ""))
        if not ok:
            self.failed.append(name)


def run(n_traj, steps, seed):
    mm, m_missing = build(M_STATES, M_EVENTS, M_TABLE)
    xm, x_missing = build(X_STATES, X_EVENTS, X_TABLE)
    t = Suite()

    print("=" * 78)
    print("第 16–17 章 FSM 验证　（随机种子 %d，%d 条轨迹 × %d 步）" % (seed, n_traj, steps))
    print("=" * 78)
    print("管理 FSM：%d 状态 × %d 事件 = %d 格" % (len(M_STATES), len(M_EVENTS), len(M_STATES) * len(M_EVENTS)))
    print("横切 FSM：%d 状态 × %d 事件 = %d 格" % (len(X_STATES), len(X_EVENTS), len(X_STATES) * len(X_EVENTS)))
    print()

    # ---------------- 管理 FSM：9 项 ----------------
    print("— 管理 FSM（表 30）—")
    t.check("完备性（全函数）· ManagerFSM",
            not m_missing and len(mm) == len(M_STATES) * len(M_EVENTS),
            "%d / %d 格有定义" % (len(mm), len(M_STATES) * len(M_EVENTS)))

    dup = [(s, e) for s in M_STATES for e in M_EVENTS
           if mm.get((s, e)) not in set(M_STATES) | {REJECT}]
    t.check("目标合法 · ManagerFSM", not dup,
            "每个目标都是已声明状态或 REJECT" if not dup else "非法目标：%s" % dup)

    bad = [(s, e) for s in M_STATES for e in M_EVENTS
           if s == "RED" and mm.get((s, e)) == "GREEN"]
    t.check("安全性 · ManagerFSM · 无 RED → GREEN 捷径", not bad,
            "检测到 RED → GREEN 直接跳变" if bad else "RED 的直接出口不含 GREEN")

    absorb = [(s, e) for s in ["CLOSED"] for e in M_EVENTS
              if e != "project_end" and mm.get((s, e)) != REJECT]
    t.check("安全性 · ManagerFSM · CLOSED 为吸收态", not absorb,
            "CLOSED 行除「项目结束」自环外全部 REJECT" if not absorb else str(absorb))

    t.check("活跃性 · ManagerFSM · GREEN → CLOSED 可达",
            reachable(mm, M_STATES, M_EVENTS, "GREEN", "CLOSED"),
            "GREEN → CLOSED")

    unreach = [s for s in M_STATES if not reachable(mm, M_STATES, M_EVENTS, s, "CLOSED")]
    t.check("活跃性 · ManagerFSM · 四个状态均可达 CLOSED", not unreach,
            "无死状态" if not unreach else "到不了 CLOSED：%s" % unreach)

    entries = {}
    for s in M_STATES:
        for e in M_EVENTS:
            if mm.get((s, e)) == "RED" and s != "RED":
                entries.setdefault(e, []).append(s)
    ok = set(entries) <= {"escalation", "member_resign"}
    t.check("不变量 · ManagerFSM · 进入 RED 仅由 escalation / member_resign", ok,
            "触发事件：%s" % (", ".join(sorted(entries)) or "无"))

    wrong = [(s, e) for s in M_STATES if s != "CLOSED" for e in ["member_resign"]
             if mm.get((s, e)) != "RED"]
    t.check("不变量 · ManagerFSM · 非 CLOSED 下核心离职一律进 RED", not wrong,
            "GREEN / YELLOW / RED 三行均 → RED" if not wrong else str(wrong))

    und, dead = random_walk(mm, M_STATES, M_EVENTS, n_traj, steps, seed)
    t.check("随机压力 · ManagerFSM · %d 条 × %d 步" % (n_traj, steps), und == 0,
            "未定义转移 %d 例，死状态轨迹 %d 条" % (und, dead))

    # ---------------- 横切 FSM：10 项 ----------------
    print()
    print("— 横切 FSM（图 18 + 表 32）—")
    t.check("完备性（全函数）· CrossCuttingFSM",
            not x_missing and len(xm) == len(X_STATES) * len(X_EVENTS),
            "%d / %d 格有定义" % (len(xm), len(X_STATES) * len(X_EVENTS)))

    badtgt = [(s, e) for s in X_STATES for e in X_EVENTS
              if xm.get((s, e)) not in set(X_STATES) | {REJECT}]
    t.check("目标合法 · CrossCuttingFSM", not badtgt,
            "每个目标都是已声明状态或 REJECT" if not badtgt else "非法目标：%s" % badtgt)

    leak = [(s, e) for s in ["CLOSED"] for e in BUSINESS_EVENTS
            if xm.get((s, e)) != REJECT]
    t.check("安全性 · CrossCuttingFSM · CLOSED 后业务事件全拒绝", not leak,
            "5 个业务事件在 CLOSED 上全部 REJECT" if not leak else str(leak))

    t.check("活跃性 · CrossCuttingFSM · IDLE → CLOSED 可达",
            reachable(xm, X_STATES, X_EVENTS, "IDLE", "CLOSED"),
            "IDLE → CLOSED")

    unreach_x = [s for s in X_STATES if not reachable(xm, X_STATES, X_EVENTS, s, "CLOSED")]
    t.check("活跃性 · CrossCuttingFSM · 七个状态均可达 CLOSED", not unreach_x,
            "无死状态" if not unreach_x else "到不了 CLOSED：%s" % unreach_x)

    into_esc = {e for s in X_STATES for e in X_EVENTS
                if xm.get((s, e)) == "ESCALATED" and s != "ESCALATED"}
    t.check("不变量 · CrossCuttingFSM · ESCALATED 仅由 escalate 到达",
            into_esc == {"escalate"}, "进入事件：%s" % (", ".join(sorted(into_esc)) or "无"))

    SELF = [("IDLE", "detect", "DETECTED"),
            ("DETECTED", "detect", "DETECTED"),
            ("CONTAINED", "contain", "CONTAINED"),
            ("ESCALATED", "escalate", "ESCALATED"),
            ("RECOVERED", "recover", "RECOVERED"),
            ("REVIEWED", "review", "REVIEWED")]
    loops = [s for s, e, _ in SELF if xm.get((s, e)) == s]
    t.check("阶段内幂等 · 五处自环（detect/contain/escalate/recover/review）",
            len(loops) == 5, "自环：%s" % ", ".join(loops))

    outside = [s for s in ["IDLE", "RECOVERED", "REVIEWED", "CLOSED"]
               if xm.get((s, "contain")) != REJECT]
    t.check("阶段外拒绝 · contain 在 IDLE / RECOVERED / REVIEWED / CLOSED 全拒绝",
            not outside, "四处均 REJECT" if not outside else "漏了：%s" % outside)

    comp = compress(TRAIL)
    dropped = [s for i, s in enumerate(TRAIL) if i and TRAIL[i - 1] == s]
    t.check("幂等压缩 · %d 步 → %d 步" % (len(TRAIL), len(comp)),
            len(TRAIL) == 11 and len(comp) == 8 and len(dropped) == 3,
            "折掉：%s" % ", ".join(dropped))

    und_x, dead_x = random_walk(xm, X_STATES, X_EVENTS, n_traj, steps, seed)
    t.check("随机压力 · CrossCuttingFSM · %d 条 × %d 步" % (n_traj, steps), und_x == 0,
            "未定义转移 %d 例，死状态轨迹 %d 条" % (und_x, dead_x))

    # ---------------- 汇总 ----------------
    print()
    print("=" * 78)
    print("压缩前的轨迹（%d 步）：" % len(TRAIL))
    print("  " + " → ".join(TRAIL))
    print("压缩后的轨迹（%d 步）：" % len(comp))
    print("  " + " → ".join(comp))
    print("=" * 78)
    print("合计 %d 项检查，通过 %d，失败 %d" % (t.n, t.n - len(t.failed), len(t.failed)))
    if t.failed:
        print("未通过：" + "; ".join(t.failed))
        print("=" * 78)
        return 1
    print("全部通过 %d / %d。" % (t.n, t.n))
    print("=" * 78)
    return 0


def main():
    ap = argparse.ArgumentParser(description="第 16–17 章 FSM 验证器")
    ap.add_argument("--n", type=int, default=N_TRAJ, help="随机轨迹条数，默认 5000")
    ap.add_argument("--steps", type=int, default=STEPS, help="每条轨迹步数，默认 20")
    ap.add_argument("--seed", type=int, default=SEED, help="随机种子，默认 20261018")
    ap.add_argument("--out", default=None, help="同时把输出写入该文件")
    args = ap.parse_args()

    if args.out:
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            code = run(args.n, args.steps, args.seed)
        finally:
            sys.stdout = old
        text = buf.getvalue()
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print(text, end="")
        sys.exit(code)

    sys.exit(run(args.n, args.steps, args.seed))


if __name__ == "__main__":
    main()
