/-
  折叠与命名 · 第 21 章「有界构造公理」的机器验证
  第二部分：字典序变式

  无外部依赖，仅 Lean 4 core。

  对应书内位置：
    21.12 有界构造公理
    21.13 三反例 / R235 的裁决：Ackermann 在类内。
          它非原始递归，但 (m, n) 的字典序是一个可检查的良基变式。
          「类外」是给不出这个量的程序，见 Basic.lean 第四节。

  本文件要说明的正是 21.14 那句话：
    「给变式，检查递减是自动的、便宜的、局部的。」
  机器上，那个检查器就是 Lean 的 termination checker：
    `termination_by` 声明变式，`decreasing_by` 把「每处都下降」
    拆成若干个**局部**子目标，交给 `omega` 自动收掉。
-/

set_option linter.unusedVariables false

namespace FoldingNaming

/-! # 一、字典序是良基的 -/

/-- `Nat × Nat` 上的字典序：先比第一分量，相等再比第二分量。 -/
abbrev NatLex : Nat × Nat → Nat × Nat → Prop := Prod.Lex (· < ·) (· < ·)

/-- 字典序良基。证明是两次强归纳：第一分量可以下降（用外层假设），
    或第一分量不变、第二分量下降（用内层假设）。 -/
theorem lex_acc : ∀ a b : Nat, Acc NatLex (a, b) := by
  intro a
  induction a using Nat.strongRecOn with
  | ind a iha =>
    intro b
    induction b using Nat.strongRecOn with
    | ind b ihb =>
      refine Acc.intro _ (fun p hp => ?_)
      obtain ⟨x, y⟩ := p
      cases hp with
      | left _ _ h => exact iha x h y
      | right _ h => exact ihb y h

theorem lex_pair_wellFounded : WellFounded NatLex :=
  WellFounded.intro (fun p => by
    obtain ⟨a, b⟩ := p
    exact lex_acc a b)

/-! # 二、变式递减检查：三个局部子目标

    Ackermann 的三条递归分支，对应三处需要检查的递减。
    单独写出来，是为了让「检查是局部的」这件事看得见：
    每一处都只涉及当前这一行，不需要看整个程序。 -/

/-- 分支二：`ack (m+1) 0` 调用 `ack m 1`，第一分量下降。 -/
theorem ack_step₁ (m : Nat) : NatLex (m, 1) (m + 1, 0) :=
  Prod.Lex.left _ _ (by omega)

/-- 分支三之内层：`ack (m+1) (n+1)` 调用 `ack (m+1) n`，第一分量不变，第二分量下降。 -/
theorem ack_step₂ (m n : Nat) : NatLex (m + 1, n) (m + 1, n + 1) :=
  Prod.Lex.right _ (by omega)

/-- 分支三之外层：`ack (m+1) (n+1)` 调用 `ack m (…)`，第一分量下降，
    第二分量是多少都无所谓——这就是字典序「便宜」的地方。 -/
theorem ack_step₃ (m n k : Nat) : NatLex (m, k) (m + 1, n + 1) :=
  Prod.Lex.left _ _ (by omega)

/-! # 三、Ackermann 终止

    三处检查全部通过 ⇒ 递归被 Lean 接受 ⇒ 函数是全的（total）。
    注意：Ackermann **不是**原始递归，但它在公理的类内——
    因为 `(m, n)` 的字典序是可检查的良基变式。 -/

/-- Ackermann 函数。`termination_by` 声明变式是 `(m, n)` 的字典序；
    `decreasing_by` 把三处递减检查自动收掉。 -/
def ack : Nat → Nat → Nat
  | 0, n => n + 1
  | m + 1, 0 => ack m 1
  | m + 1, n + 1 => ack m (ack (m + 1) n)
termination_by m n => (m, n)
decreasing_by
  all_goals simp_wf
  all_goals omega

/-- 自测：第一分支。 -/
example (n : Nat) : ack 0 n = n + 1 := by simp [ack]

/-! # 四、数值自测（编译时执行） -/

#eval ack 2 3     -- 9
#eval ack 3 3     -- 61
#eval ack 3 5     -- 253

end FoldingNaming
