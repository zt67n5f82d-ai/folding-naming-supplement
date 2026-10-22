/-
  折叠与命名 · 第 21 章「有界构造公理」的机器验证
  第四部分：带变式的循环

  无外部依赖，仅 Lean 4 core。

  对应书内位置：
    21.12 有界构造公理 ① 每处重复控制流都是带良基变式的循环

  这一部分要说明的是一件很硬的事：
    在这个语言里，一个循环**如果不带变式、或者变式不递减，就写不出来**。
    不是「写了会报错提醒你」，而是定义本身无法通过类型检查——
    编译器拒绝接受这个定义。

  这就是「准入门」的机器版：公理不是一条建议，是一道门。
-/

set_option linter.unusedVariables false

namespace FoldingNaming

/-! # 一、不含循环的语句：必然终止

    顺序、赋值、分支三种结构。它们的终止性靠结构递归直接给出：
    子语句是原语句的真子项，所以递归必然耗尽。 -/

inductive Basic where
  | skip
  | assign (f : Nat → Nat)
  | seq (a b : Basic)
  | ite (c : Bool) (a b : Basic)

/-- 执行一条不含循环的语句。状态就是一个自然数（足够演示，不损失一般性）。 -/
def runBasic : Basic → Nat → Nat
  | .skip, st => st
  | .assign f, st => f st
  | .seq a b, st => runBasic b (runBasic a st)
  | .ite c a b, st => if c then runBasic a st else runBasic b st

/-! # 二、带变式的循环

    `runWhile` 有三个额外参数，正是公理①要求的三个部分：
      `cond` —— 循环条件（何时继续）
      `V`    —— 变式（那个"每轮严格变小"的量）
      `hdec` —— **递减证明**：每一轮，V 真的变小了

    第三个参数是关键的。它不是注释，不是文档，是**类型的一部分**：
    不给出它，`runWhile` 无法通过终止性检查，函数根本定义不出来。

    21.14 说「给变式，检查递减是自动的、便宜的、局部的」——
    这里的 `decreasing_by exact hdec st hc` 就是那个检查：
    它只用到"当前这一轮"的假设，不看别的任何地方。 -/

def runWhile (cond : Nat → Bool) (V : Nat → Nat) (body : Basic)
    (hdec : ∀ st, cond st = true → V (runBasic body st) < V st) : Nat → Nat
  | st => if hc : cond st then runWhile cond V body hdec (runBasic body st) else st
termination_by st => V st
decreasing_by exact hdec st hc

/-! # 三、一个具体程序：倒计时

    变式就是 `st` 本身，循环体把 `st` 减 1。
    `hdec` 的证明只有一句 `omega`——因为它确实是局部的、便宜的。 -/

/-- 从 st 倒数到 0。 -/
def countdown (st : Nat) : Nat :=
  runWhile (fun s => s > 0) (fun s => s) (.assign (fun s => s - 1))
    (by
      intro s hs
      simp only [decide_eq_true_eq] at hs
      show s - 1 < s
      omega) st

/-! # 四、反例：去掉变式就写不出来

    下面这段（注释掉）如果取消注释，Lean 会拒绝：

      def runWhileBad (cond : Nat → Bool) (body : Basic) : Nat → Nat
        | st => if cond st then runWhileBad cond body (runBasic body st) else st

    报错是「failed to prove termination」。这就是准入门在起作用：
    **没有变式的循环不是"不推荐"，是不可表达。**

    书里 21.13 的第一个反例——「给不出这个量的程序」——
    在这个语言里连写都写不出来。这不是限制，这是公理在收租。
-/

/-! # 五、数值自测（编译时执行） -/

#eval countdown 5    -- 0
#eval countdown 0    -- 0
#eval countdown 17   -- 0

end FoldingNaming
