# 第 21 章「有界构造公理」的 Lean 4 形式化

这是《折叠与命名》第 21 章那条公理在 Lean 4 里的机器验证。
**没有用 mathlib**，只依赖 Lean 4 自带的核心库。

```
公理（书里 21.12）：
  ① 每处重复控制流都是带良基变式的循环；
  ② 递归只在参数带良基变式时容许（可规约为 ①）。
```

## 怎么跑

需要 Lean 4（`v4.34.1` 或兼容版本）。项目里已有 `lean-toolchain`，`lake` 会自己挑版本。

```bash
lake build            # 编译全部，约 40 秒
lean AxiomCheck.lean  # 打印每条定理的公理依赖（需先 build）
```

`AxiomCheck.lean` 是诚实性检查：若任何定理依赖 `sorryAx`，说明那个证明是假的。
当前结果：**31 条定理，零 `sorryAx`**。8 条完全不依赖任何公理，其余只依赖 `propext` 与 `Quot.sound`（Lean 的标准公理，任何数学证明都可以用）。

## 四个部分

| 文件 | 对应书内 | 内容 |
|---|---|---|
| `Basic.lean` | 21.12 / 21.13 / 21.14 | 良基序与变式的通用理论、反例 |
| `Lexicographic.lean` | 21.12 / R235 | 字典序变式；Ackermann 终止 |
| `While.lean` | 21.12 ① | 带变式的循环；无变式则写不出来 |
| `FSM.lean` | 16–17 章 | 两个状态机的完备性/安全性/活跃性/不变量 |

### Basic：公理的数学内容

| 定理 | 说的是什么 |
|---|---|
| `no_infinite_descent` | 良基关系上不存在无穷下降序列 |
| `variant_bounds_steps` | 每步变式严格下降 ⇒ 第 n 步的状态变式值 ≤ 初值 − n |
| `loop_terminates` | 变式存在 ⇒ 不存在从该点出发的无穷运行 |
| `recursion_reduces_to_variant` | 公理②：良基递归只有唯一解（`WellFounded.fix`） |
| `no_solution_unbounded_recursion` | 反例：`f n = f (n+1) + 1` 在自然数上**无解** |

`variant_bounds_steps` 是 21.14 那句「给变式，检查递减是自动的、便宜的、局部的」的机器版：
只要逐点验证递减，界就自动得到。

### Lexicographic：Ackermann 在类内

R235 的裁决是「Ackermann 不是原始递归，但**在类内**——因为 `(m,n)` 的字典序是可检查的良基变式」。

这里把它落实了。三处递减检查各自独立成一条定理：

| 定理 | 检查点 |
|---|---|
| `ack_step₁` | `ack (m+1) 0` → `ack m 1`：第一分量下降 |
| `ack_step₂` | `ack (m+1) (n+1)` → `ack (m+1) n`：第一分量不变，第二分量下降 |
| `ack_step₃` | `ack (m+1) (n+1)` → `ack m (…)`：第一分量下降，第二分量任意 |

第三处最能说明字典序「便宜」在哪：它根本不需要知道你给的第二个参数是多少。

数值自测（编译时执行）：`ack 2 3 = 9`、`ack 3 3 = 61`、`ack 3 5 = 253`。

### While：准入门

`runWhile` 有三个参数正好对应公理①的三部分：条件、变式、**递减证明**。
第三个是类型的一部分，不是注释：

```lean
def runWhile (cond : Nat → Bool) (V : Nat → Nat) (body : Basic)
    (hdec : ∀ st, cond st = true → V (runBasic body st) < V st) : Nat → Nat
  | st => if hc : cond st then runWhile cond V body hdec (runBasic body st) else st
termination_by st => V st
decreasing_by exact hdec st hc
```

去掉 `hdec` 会怎样？实测（去掉后的定义）：

```
error: fail to show termination for runWhileBad
failed to infer structural recursion:
  Not considering parameter cond of runWhileBad:
    it is unchanged in the recursive calls
  ...
failed to prove termination
```

**这就是「准入门」的机器版**：无变式的循环不是「不推荐」，是不可表达。
书里 21.13 的第一个反例——「给不出这个量的程序」——在这个语言里连写都写不出来。

### FSM：16–17 章那两个状态机

对照 `chapter_16_17_fsm/fsm_verify.py` 的 19 项检查。同四类属性（书内表 37）：

| 脚本项 | Lean 里 |
|---|---|
| 完备性 / 目标合法（4 项） | **类型系统免费给出**：`mStep : MState → MEvent → Option MState` 是全函数，结果只可能是已声明状态或 `none`，不存在第三种情况 |
| 安全性 · 无 RED→GREEN | `m_no_red_green` |
| 安全性 · CLOSED 吸收 | `m_closed_absorb`（只接受 `project_end` 自环） |
| 不变量 · 进 RED 的事件 | `m_red_entry`（需排除 RED 自环） |
| 不变量 · 离职必进 RED | `m_resign_to_red` |
| 活跃性 · 均可达 CLOSED | `m_all_reach_closed` / `x_all_reach_closed`（**构造性**：路径是证明的一部分） |
| 安全性 · CLOSED 后全拒绝 | `x_closed_rejects_all`（比脚本更强：脚本只查 5 个业务事件，这里查全部 6 个） |
| 不变量 · ESCALATED 入口 | `x_escalated_entry` |
| 阶段内幂等 · 五处自环 | `x_idem_*`（5 条） |
| 阶段外拒绝 | `x_contain_outside` |
| 幂等压缩 11→8 | `compress_trail`（`decide` 判定） |
| 随机压力 5000×20 | **不需要**：这里是对所有状态与事件的**全称**证明，比抽样强 |

还多了一条脚本里没有的：

```lean
theorem x_to_closed (s : XState) (e : XEvent)
    (h : xStep s e = some .CLOSED) : s = .REVIEWED ∧ e = .close
```

**进入 CLOSED 只有一条路：从 REVIEWED 出发、且只有 close 事件。**
这是「走完全部检查站才允许关单」的机器版，也是整章「不变量」一词最实在的落点。

## 两套方法的关系

|  | Python 脚本 | Lean |
|---|---|---|
| 性质 | 同一批（表 37 四类） | 同一批 |
| 覆盖 | 穷举 + 5000×20 随机抽样 | 全称，无抽样 |
| 结果 | 19/19 通过 | 30 条全部通过，零 `sorry` |
| 可核 | 输出可 diff | 编译器逐条核，`#print axioms` 可查 |

两者不互相替代：脚本给的是「跑过，没出错」，Lean 给的是「对所有情况成立」。
书里那句话（21.14）说的是「证书不是判定」——Lean 在这里的角色正是一个**证书**：
它证明的是「给定这个变式，这个程序终止」，而不是「这个程序能判定任何东西」。

## 构建环境

- Lean `4.34.1`，x86_64-w64-windows-gnu
- 无 mathlib、无第三方依赖
- `lake build` 7 jobs，从零约 20 秒（含编译 4 个模块）
- `#eval` 的输出在 build 日志里可见（9 / 61 / 253 / 0 / 0 / 0）
