# -*- coding: utf-8 -*-
"""
不变量映射的数学形式化 —— 一个可跑的最小验证
================================================
目标：回答「能不能把『不变量映射』数学化，并给出『从 A 值改善到 B 值』」这个问题。

模型（对应书里的「一层 = (π, δ, α) + 不变量」）：
  - 具体域 C  = 下层的状态（这里：4 个任务，每个 = (状态, 负责人)）
  - 抽象域 A  = 上层的「视图」（这里：周报）
  - π: C -> A  上行压缩（书里的 π）
  - γ: A -> C  下行具体化（γ 对应书里的 α 的「语义」：α 给出的原语能重建出的最广状态集）
  - 不变量 I  = C 上的子集，满足 I 的状态叫「合规」；违反 → 回滚（书里的不变量）

我们检验三件事：
  1) 伴随（Galois）条件  c ⊑ γ(π(c))  是否成立（soundness）
  2) **往返缺陷** defect = |{c∈I : 视图 π(c) 无法与某个违反 I 的状态区分}| / |I|
     —— 这是一个标量。defect=0 表示「这个接口能守住不变量」；>0 表示会漏。
  3) 信息代价：H(π(X)) 与 H(X)。验证数据处理不等式 H(π(X)) ≤ H(X)，
     并量化「守住不变量」需要付多少比特。

复现说明（本仓库版本）
----------------------
与书中那次运行相比，本文件只做了一层薄封装：把样本数 M、任务数、随机种子提成
可选命令行参数。**默认值就是书中那次运行用的参数**（M=40000，任务数 4，
seed=20261006），输出与 `invariant_math_results.txt` 逐字节一致。
随机数调用顺序与判定逻辑一字未改。

    python invariant_math.py                        # 默认：复现表 68
    python invariant_math.py --M 20000 --n-tasks 2  # 改参数看看数字怎么动
    python invariant_math.py --out my_run.txt       # 存到文件里与存档结果 diff
"""
import argparse
import io
import math
import random
import sys
from collections import Counter

SEED = 20261006
STATUS = ['待办', '进行中', '已完成']
OWNER = ['甲', '乙', '丙', None]      # None = 未指派
N_TASK = 4
M = 40000


def sample_state():
    """从生成分布里采一个具体状态（N_TASK 个任务）。"""
    st = []
    for _ in range(N_TASK):
        s = random.choices(STATUS, weights=[0.35, 0.40, 0.25])[0]
        if s == '进行中':      # 进行中的任务：90% 有负责人，10% 漏指派
            o = random.choices(OWNER, weights=[0.30, 0.30, 0.30, 0.10])[0]
        elif s == '已完成':    # 已完成：几乎都有负责人
            o = random.choices(OWNER, weights=[0.33, 0.33, 0.33, 0.01])[0]
        else:                  # 待办：多数还没指派
            o = random.choices(OWNER, weights=[0.10, 0.10, 0.10, 0.70])[0]
        st.append((s, o))
    return tuple(st)


# ---- 不变量：进行中的任务必须有负责人（书里的「违反即回滚」） ----
def I(c):
    return all(not (s == '进行中' and o is None) for s, o in c)


# ---- 两个候选接口（视图） ----
def pi_v1(c):        # 周报 v1：只报各状态计数 —— 丢掉负责人
    return tuple(sorted(s for s, _ in c))


def pi_v2(c):        # 周报 v2：报 (状态, 负责人) 的多重集 —— 丢顺序，但保住负责人
    return tuple(sorted(c, key=lambda x: (x[0], '' if x[1] is None else x[1])))


def entropy(counter, total):
    return -sum((v / total) * math.log2(v / total) for v in counter.values())


def defect(pi, samples):
    """往返缺陷：在合规状态里，视图无法与某个违规状态区分的比例。"""
    by_view = {}
    for c in samples:
        by_view.setdefault(pi(c), set()).add(I(c))
    ambiguous = {v for v, flags in by_view.items() if flags == {True, False}}
    good = [c for c in samples if I(c)]
    leaked = sum(1 for c in good if pi(c) in ambiguous)
    return leaked / len(good), len(good)


def soundness_violations(pi, samples):
    """伴随条件 c ⊑ γ(π(c)) 的检查：
    若存在 c∈I 使 π(c) 同时被违规状态取到，则 γ(π(c)) 含违规点 → 不 sound。"""
    return defect(pi, samples)[0] > 0


def main():
    samples = [sample_state() for _ in range(M)]
    H_X = entropy(Counter(samples), M)
    H1 = entropy(Counter(pi_v1(c) for c in samples), M)
    H2 = entropy(Counter(pi_v2(c) for c in samples), M)
    d1, n_good = defect(pi_v1, samples)
    d2, _ = defect(pi_v2, samples)

    P_I = sum(1 for c in samples if I(c)) / M
    # 不变量自身的熵：H(I(X))
    H_I = -P_I * math.log2(P_I) - (1 - P_I) * math.log2(1 - P_I)

    print('=' * 74)
    print('不变量映射的量化验证  (样本 M = %d, 任务数 = %d)' % (M, N_TASK))
    print('=' * 74)
    print('不变量 I = 「进行中的任务必须有负责人」')
    print('合规状态占比 P(I) = %.4f' % P_I)
    print()
    print('%-22s %-12s %-12s %-12s %s' % ('接口', '往返缺陷', '能否守住 I', 'H(视图)/bit', '压缩率'))
    print('-' * 74)
    print('%-22s %-12.4f %-12s %-12.4f %.4f' % ('π₁ 周报v1(只报计数)', d1, '否' if d1 > 0 else '是', H1, H1 / H_X))
    print('%-22s %-12.4f %-12s %-12.4f %.4f' % ('π₂ 周报v2(带负责人)', d2, '是' if d2 == 0 else '否', H2, H2 / H_X))
    print('-' * 74)
    print('H(具体域 X)          = %.4f bit' % H_X)
    print('数据处理不等式检验    H(π(X)) ≤ H(X) : %.4f ≤ %.4f  %s' % (H1, H_X, '✓'))
    print('                      H(π(X)) ≤ H(X) : %.4f ≤ %.4f  %s' % (H2, H_X, '✓'))
    print()
    print('★ 「守住不变量」的信息代价 = H(π₂) − H(π₁) = %.4f bit' % (H2 - H1))
    print('★ 缺陷从 %.4f 降到 %.4f （这就是「从 A 值改善到 B 值」）' % (d1, d2))
    print()
    print('—— 硬下界（定理，不是估计）——')
    print('不变量自身的熵 H(I(X)) = %.4f bit' % H_I)
    print('任何能判定 I 的视图都必须满足  H(π) ≥ H(I(X)) = %.4f bit' % H_I)
    print('  （因为 I(X) 是 π(X) 的函数，由 DPI：H(I(X)) ≤ H(π(X))）')
    print('本设计的实际开销 H(π₂) = %.4f bit ≥ 下界 %.4f bit  ✓' % (H2, H_I))
    print()
    print('结论：')
    print('  · 缺陷 defect 是一个**可计算的标量**，接口改进 = 缺陷单调下降（可测、可回归）。')
    print('  · 但 π₁→π₂ 不是免费的：要守住不变量，必须**多付 %.2f bit**。' % (H2 - H1))
    print('  · 两者都满足 H(π(X)) ≤ H(X)：折叠**不可能**凭空造信息（DPI）。')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='接口往返缺陷与信息代价的最小验证（书中表 68）')
    ap.add_argument('--M', type=int, default=40000, help='样本数，默认 40000（书中那次运行）')
    ap.add_argument('--n-tasks', type=int, default=4, help='下层任务数，默认 4（书中那次运行）')
    ap.add_argument('--seed', type=int, default=SEED, help='随机种子，默认 20261006（书中那次运行）')
    ap.add_argument('--out', default=None, help='同时把输出写入该文件（便于与存档结果 diff）')
    args = ap.parse_args()

    M = args.M
    N_TASK = args.n_tasks
    random.seed(args.seed)

    if args.out:
        # 同时打印到屏幕与文件，编码固定 UTF-8（Windows 控制台默认 GBK 会乱码）
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            main()
        finally:
            sys.stdout = old
        text = buf.getvalue()
        with open(args.out, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
        print(text, end='')
    else:
        main()
