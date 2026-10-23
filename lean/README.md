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
当前结果：**54 条定理，零 `sorryAx`**。10 条完全不依赖任何公理，其余只依赖 `propext` 与 `Quot.sound`（Lean 的标准公理，任何数学证明都可以用）。

## 六个部分

| 文件 | 对应书内 | 内容 |
|---|---|---|
| `Basic.lean` | 21.12 / 21.13 / 21.14 | 良基序与变式的通用理论、反例 |
| `Lexicographic.lean` | 21.12 / R235 | 字典序变式；Ackermann 终止 |
| `While.lean` | 21.12 ① | 带变式的循环；无变式则写不出来 |
| `Certificate.lean` | 21.12 / 21.14 / 21.16 | 把公理当判据用：通过必停、上界可算、反例无证书 |
| `FSM.lean` | 16–17 章 | 两个状态机的完备性/安全性/活跃性/不变量 |
| `TCP.lean` | 19 章 | TCP 的复算：完备性、四条属性、强模拟与弱模拟 |

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

### Certificate：把公理当判据用

前面三部分证明的是「公理是真的」「公理是一道门」。这一部分证明的是「**公理能用来判**」——
拿它去查一个具体程序，通过检查的在可算步数内停。这才是免疫系统的准入门该有的样子。

先要一个**不带任何终止性假设**的执行器，否则就是拿终止性证终止性：

```lean
def runFuel (cond : Nat → Bool) (body : Basic) (fuel : Nat) (st : Nat) : Option Nat
```

燃料是结构递归的参数，所以它总能定义出来——程序即使发散，也只是把燃料烧完返回 `none`。
**燃料就是那根保险丝**：熔断返回 `none`，可执行、可观测，这是 21.16 第二道门（监测门）的机器版。

| 定理 | 说的是什么 |
|---|---|
| `fuel_enough` | 变式逐轮严格下降 ⇒ 燃料 `V st` 就够。21.12「算出了一个迭代次数的有限上界」就是它，上界可算，不是存在性断言 |
| `Loop.stops` | 拿公理判一处循环：`V st` 步内一定停 |
| `admission_sound` | **准入门的可靠性（sound）**：通过检查的程序，从任何初始状态出发都有限步停 |
| `countdown_stops_in_17` | 用公理证明一个具体程序停：17 步内 |
| `countdown_needs_more_than_4` | 上界是紧的：燃料 4 步不够，熔断。`decide` 算出来的 |
| `no_variant_identity` | 拒绝：循环体不动的程序，任何变式都过不了 |
| `no_variant_int_descent` | 拒绝：整数域上 `n ↦ n-1`，不存在递减的 `V : Int → Nat`（无下界） |
| `no_variant_growing_queue` | 拒绝：待遍历元素只增不减，不存在递减的 `V` |

这里有三件事必须分清，否则这套说法会显得比它实际做到的强：

1. **可靠（sound）**：通过 ⇒ 一定停。方向不能反。反方向「必停 ⇒ 有证书」不成立，那正是 21.17「公理换掉了表达力」。
2. **有界（bounded）**：不只是「会停」，是「`V st` 步内停」，而且这个数能算出来。
3. **能拒（refuting）**：21.13 的三个反例，证明的是「**这样的证书不存在**」，不是「我们没找到」。
   免疫系统不能只会盖章。

`Loop.dec` 是**结构体字段**，不是注释：不带递减证明的循环在这个类型里构造不出来。
「每一处重复控制流都是带良基变式的循环」不是运行期检查的结果，是类型的形状。

**但有一处必须诚实写明**：可判的只有结构那一半（燃料计数、覆盖形状、变式值域，这些是 `Bool`，自动且便宜）。
「每轮真的变小」这条义务要对全体状态量化，它不是 `Bool` 判定，是**内核逐条检查的证明项**——
机械、局部、便宜，但不是「算一下就有答案」。21.14 说这是**证书关系不是判定关系**，在机器上就是这个区别。

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


### TCP：第 19 章的复算

书里 19.5 列了四条属性（安全性、活跃性、不变量、精化），19.6 又说这一章「有一部分属于设计目标，只有设计论证，没有运行记录」。这一节把它们补成机器证明。

⚠ 口径先声明（19.6 的规矩）：`TCP.lean` 里的转移表是**按书内 19.1–19.5 的文字重建的教学模型**——11 个状态、书内点名的那几个事件、19.3 与 19.4 那两次失败的具体形态。它**不是 RFC 793 全文，也不是作者当年那个脚本的原件**。结论只对这个重建模型成立。

| 定理 | 对应书内 | 说的是什么 |
|---|---|---|
| `v1_rst_undefined` | 19.4 | 补全前 `FIN_WAIT_1 × rcv_rst` 是**未定义**——19.4 那个失败的精确形态 |
| `v1_eq_some_v2` | 19.4 | 补全是**保守**的：原来有定义的地方，补全后行为不变 |
| `strong_simulation_fails` | 19.3 / 19.5 | **强模拟不成立**。见证：`ESTABLISHED × rcv_ack`——具体不动、抽象必须动 |
| `stuttering_simulation` | 19.5 最后一条 | **弱模拟成立**（11 × 9 全称）：具体走一步时，抽象允许停原地 |
| `no_data_before_established` | 19.5 安全性 | □(¬Connected → ¬DataSent)，对 11 个状态全称 |
| `established_entry` | 19.5 不变量 | 从别处进 ESTABLISHED 只有两条路；**自环必须先摘掉**，否则命题是假的 |
| `time_wait_absorbs` / `time_wait_exit` | 19.5 不变量 | TIME_WAIT 除 `timeout` 外吸收一切，包括 RST——2MSL 的落点 |
| `close_path_visits_time_wait` | 19.5 活跃性 | 关闭路径**经过** TIME_WAIT，不是直跳；路径本身就是证明 |

**最要紧的一条**：19.5 那句「精化（simulation）：TCP 商空间相对于具体系统是可靠的——抽象不遗漏任何具体行为」，在**强模拟**口径下**不成立**。`ESTABLISHED` 收到 `rcv_ack` 是数据确认（状态不变），而 `LAST_ACK` 收到 `rcv_ack` 是关闭确认（回 CLOSED），两者同在 `active` 类里——同一个事件名，同一个类，两个目标。

换成**弱（stuttering）模拟**（允许抽象停步，即折叠丢掉的细节不要求抽象也走一步）后，3 类划分完全成立，11 × 9 无一例外。所以那句话要读成弱模拟：**不遗漏 ≠ 一一对应**。

顺带把 19.3 的账算清：书里说 `rcv_ack` 有两种语义（握手确认、数据确认），按这个模型其实是**三种**，第三种是 `LAST_ACK` 上的关闭确认——而它才是强模拟失败的直接原因。若要强模拟成立，最小划分会退化成 11 类（压缩比 1.0，等于没压缩）；这个数是用独立脚本算的，没有形式化，所以只作参考。

**一处刻意的取舍**：RFC 793 允许 `TIME_WAIT` 收到 RST 提前关闭，那会破坏 19.5 那条「必须等 2MSL」。这里让 RST 被吸收（RFC 1337 的做法），因为两条不能同时成立，必须选一条。取舍写在定理的文档注释里，不藏在代码里。

## 两套方法的关系

|  | Python 脚本 | Lean |
|---|---|---|
| 性质 | 同一批（表 37 四类） | 同一批 |
| 覆盖 | 穷举 + 5000×20 随机抽样 | 全称，无抽样 |
| 结果 | 19/19 通过 | 54 条全部通过，零 `sorry` |
| 可核 | 输出可 diff | 编译器逐条核，`#print axioms` 可查 |

两者不互相替代：脚本给的是「跑过，没出错」，Lean 给的是「对所有情况成立」。
书里那句话（21.14）说的是「证书不是判定」——Lean 在这里的角色正是一个**证书**：
它证明的是「给定这个变式，这个程序终止」，而不是「这个程序能判定任何东西」。

## 构建环境

- Lean `4.34.1`，x86_64-w64-windows-gnu
- 无 mathlib、无第三方依赖
- `lake build` 9 jobs，从零约 70 秒（含编译 6 个模块）
- `#eval` 的输出在 build 日志里可见（9 / 61 / 253 / 0 / 0 / 0 / some 0 / none / some 0）
