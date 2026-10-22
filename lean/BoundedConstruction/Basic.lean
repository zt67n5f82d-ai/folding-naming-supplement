/-
  折叠与命名 · 第 21 章「有界构造公理」的机器验证
  第一部分：良基序与变式

  无外部依赖，仅 Lean 4 core（不使用 mathlib）。

  对应书内位置：
    21.12 有界构造公理   ① 每处重复控制流都是带良基变式的循环
    21.14 证书非判定     "给变式，检查递减是自动的、便宜的、局部的"
-/

set_option linter.unusedVariables false

namespace FoldingNaming

/-! # 一、良基序：不存在无穷下降链 -/

/-- 良基关系上不存在无穷下降序列。
    这是公理①「带良基变式的循环」之所以能终止的根本原因。 -/
theorem acc_no_descent {α : Type} {r : α → α → Prop} {a : α} (h : Acc r a)
    {f : Nat → α} (h0 : f 0 = a) (hf : ∀ n, r (f (n + 1)) (f n)) : False := by
  have key : ∀ x, Acc r x → (∀ k, f k = x → False) := by
    intro x hx
    induction hx using Acc.rec with
    | intro x _ ih =>
      intro k hk
      exact ih (f (k + 1)) (hk ▸ hf k) (k + 1) rfl
  exact key a h 0 h0

theorem no_infinite_descent {α : Type} {r : α → α → Prop} (hwf : WellFounded r) :
    ¬ ∃ f : Nat → α, ∀ n, r (f (n + 1)) (f n) := by
  rintro ⟨f, hf⟩
  exact acc_no_descent (WellFounded.apply hwf (f 0)) rfl hf

/-! # 二、公理①的定量版：变式给出步数上界

    书里 21.14 说「你给出变式，检查递减是自动的、便宜的、局部的」。
    下面这条定理就是那句话的机器版：**只要逐点验证递减，就自动得到界**。 -/

/-- 若每一步变式都严格下降，则从 s 出发第 n 步的状态，其变式值至少比
    初始值少了 n。取 n = V s + 1 即得矛盾，于是循环必然在 V s 步内停止。 -/
theorem variant_bounds_steps {σ : Type} (step : σ → σ → Prop) (V : σ → Nat)
    (hdec : ∀ s s', step s s' → V s' < V s)
    (s : σ) (f : Nat → σ) (h0 : f 0 = s) (hf : ∀ n, step (f n) (f (n + 1))) :
    ∀ n, V (f n) + n ≤ V s := by
  intro n
  induction n with
  | zero => simp [h0]
  | succ k ih =>
    have h1 : V (f (k + 1)) + 1 ≤ V (f k) :=
      Nat.succ_le_of_lt (hdec _ _ (hf k))
    omega

/-- 推论：变式存在 ⇒ 不存在从 s 出发的无穷运行。 -/
theorem loop_terminates {σ : Type} (step : σ → σ → Prop) (V : σ → Nat)
    (hdec : ∀ s s', step s s' → V s' < V s) (s : σ) :
    ¬ ∃ f : Nat → σ, f 0 = s ∧ ∀ n, step (f n) (f (n + 1)) := by
  rintro ⟨f, h0, hf⟩
  have hb := variant_bounds_steps step V hdec s f h0 hf (V s + 1)
  omega

/-! # 三、公理②：递归可规约为变式

    书内固定表述：「递归只在参数带良基变式时容许（可规约为 ①）」。
    Lean 的 `WellFounded.fix` 就是这个规约的构造性版本：
    任何良基关系上的递归都只有唯一解。 -/

theorem recursion_reduces_to_variant {α : Type} {r : α → α → Prop}
    (hwf : WellFounded r) :
    ∀ (C : α → Sort) (F : ∀ x, (∀ y, r y x → C y) → C x),
      ∃ f : ∀ x, C x, ∀ x, f x = F x (fun y _ => f y) :=
  fun C F => ⟨WellFounded.fix hwf F, WellFounded.fix_eq hwf F⟩

/-! # 四、反面：没有变式就没有保证

    书里 21.13 的三反例，第一个就是「给不出这个量」的程序。
    这里给机器版：`f n = f (n+1) + 1` 在自然数上无解——
    不是「很难证」，是**根本不存在这样的函数**。 -/

/-- 反例：`f n = f (n + 1) + 1` 不存在解。 -/
theorem no_solution_unbounded_recursion :
    ¬ ∃ f : Nat → Nat, ∀ n, f n = f (n + 1) + 1 := by
  rintro ⟨f, hf⟩
  have hmono : ∀ n, f (n + 1) < f n := by
    intro n
    have := hf n
    omega
  exact no_infinite_descent Nat.lt_wfRel.wf ⟨f, hmono⟩

end FoldingNaming
