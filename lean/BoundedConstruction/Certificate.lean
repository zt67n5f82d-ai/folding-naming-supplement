/-
  折叠与命名 · 第 21 章「有界构造公理」的机器验证
  第三部分：把公理当判据用 —— 准入门的「可靠」

  对应书内位置：
    21.12  ① 每一处重复控制流，都是一个带良基变式的循环
    21.13  三个反例
    21.14  「你给出变式，它在本地被检查……自动的、便宜的、局部的」
    21.16  第一道门，准入门：什么可以进来

  这一部分和 Basic / While 的分工：
    Basic  证明「公理是真的」（变式 ⇒ 没有无穷下降链）
    While  证明「公理是一道门」（没有变式，循环定义不出来）
    这里   证明「公理能用来判」——拿它去查一个具体程序，
           通过检查的在可算步数内停；21.13 的三个反例，
           则给出「证书根本不存在」的证明。

  三件事合起来，才是免疫系统的一个完整方面：
    可靠（通过 ⇒ 停，即 18 章那个 sound）＋ 有界（上界可算）＋ 能拒（反例无证书）。
-/

import BoundedConstruction.Basic
import BoundedConstruction.While

set_option linter.unusedVariables false

namespace FoldingNaming

/-! # 一、可判的执行模型

    要谈「用公理去查一个程序」，先得有一个**不带任何终止性假设**的执行器。
    否则就是循环论证：拿终止性去证终止性。

    `runFuel` 就是这个执行器。燃料是结构递归的参数，所以它总能定义出来——
    程序即使发散，也只是把燃料烧完返回 `none`，函数本身不会卡住。

    这一点顺带给出 21.16 第二道门（监测门）的机器版：
    燃料就是那根保险丝。熔断时返回 `none`，是可执行的观测，不是事后推断。
-/

/-- 带燃料的循环执行器。燃料烧完而条件仍为真，返回 `none`。 -/
def runFuel (cond : Nat → Bool) (body : Basic) (fuel : Nat) (st : Nat) : Option Nat :=
  Nat.rec (motive := fun _ => Nat → Option Nat)
    (fun st => if cond st then none else some st)
    (fun _ ih st => if cond st then ih (runBasic body st) else some st)
    fuel st

/-! # 二、公理给出上界：这是「用公理证明程序停止」的正题

    21.12 那句话是：「它给每一个程序算出了一个迭代次数的有限上界」。
    下面这条定理就是它：**只要逐轮验证递减，`V st` 步燃料一定够**。
    上界不是存在性断言，是可以从程序文本里算出来的那个数。 -/

/-- 公理①的定量版（判据形式）：变式逐轮严格下降 ⇒ 燃料 `V st` 就足够。
    证明只用到「当前这一轮」的递减，不看程序别处——这就是 21.14 说的局部。 -/
theorem fuel_enough (cond : Nat → Bool) (body : Basic) (V : Nat → Nat)
    (hdec : ∀ st, cond st = true → V (runBasic body st) < V st) :
    ∀ (k st : Nat), V st ≤ k → (runFuel cond body k st).isSome := by
  intro k
  induction k with
  | zero =>
    intro st h
    have hV : V st = 0 := Nat.le_zero.mp h
    cases hc : cond st
    · show (if cond st then (none : Option Nat) else some st).isSome = true
      rw [hc]; rfl
    · exfalso
      have hlt := hdec st hc
      omega
  | succ k ih =>
    intro st h
    cases hc : cond st
    · show (if cond st then runFuel cond body k (runBasic body st) else some st).isSome = true
      rw [hc]; rfl
    · show (if cond st then runFuel cond body k (runBasic body st) else some st).isSome = true
      rw [hc]
      exact ih (runBasic body st) (by have hlt := hdec st (by assumption); omega)

/-! # 三、证书：一处循环 ＋ 它的变式 ＋ 它的递减证明

    注意 `dec` 是**结构体字段**，不是注释、不是可选标记。
    这意味着：一个不带递减证明的循环，在这个类型里**构造不出来**。
    「每一处重复控制流都是带良基变式的循环」不是运行期检查的结果，
    是类型的形状——这是公理①在语言层的落点，也是准入门的硬底。 -/

structure Loop where
  /-- 循环条件 -/
  guard : Nat → Bool
  /-- 循环体：不含循环的基本语句 -/
  body : Basic
  /-- 变式：那个「每轮严格变小、且有底」的量 -/
  V : Nat → Nat
  /-- 递减证书：只谈一轮，不谈全局 -/
  dec : ∀ st, guard st = true → V (runBasic body st) < V st

/-- 准入：拿公理判一处循环。结论是「`V st` 步内一定停」，不是「大概会停」。 -/
theorem Loop.stops (l : Loop) (st : Nat) :
    (runFuel l.guard l.body (l.V st) st).isSome = true :=
  fuel_enough l.guard l.body l.V l.dec (l.V st) st (Nat.le_refl _)

/-- **准入门的可靠性**（sound，18 章那个「可靠」）：通过了检查的程序，从任何初始状态出发都在有限步内停，
    而且这个「有限步」是可算的。免疫系统要的正是这个方向——
    放行的东西一定安全（不是「安全的才放行」，那是不完备的，见 21.17）。 -/
theorem admission_sound (l : Loop) (st : Nat) :
    ∃ k, (runFuel l.guard l.body k st).isSome = true :=
  ⟨l.V st, l.stops st⟩

/-! # 四、实例：用公理证明一个具体程序停止

    倒计时：变式就是 `st` 本身，循环体每轮减一。
    `hdec` 的证明只有一句 `omega`——局部、便宜，正如 21.14 所述。 -/

/-- 从 st 倒数到 0。 -/
def countdownLoop : Loop where
  guard := fun s => s > 0
  body := .assign (fun s => s - 1)
  V := fun s => s
  dec := by
    intro st hs
    simp only [decide_eq_true_eq] at hs
    show st - 1 < st
    omega

/-- 公理对这个程序给出的判决：17 步内停。这是定理，不是跑出来的。 -/
theorem countdown_stops_in_17 :
    (runFuel countdownLoop.guard countdownLoop.body (countdownLoop.V 17) 17).isSome = true :=
  countdownLoop.stops 17

/-- 上界是紧的：燃料 4 步不够，保险丝熔断（返回 `none`）。
    这条不是为了证明什么，是为了说明「上界可算」不是空话——
    它一边给够，一边给出不够，两条都能被机器算出来。 -/
theorem countdown_needs_more_than_4 :
    runFuel countdownLoop.guard countdownLoop.body 4 17 = none := by
  decide

/-! # 五、拒绝：三个反例**根本没有证书**

    可靠性只说「通过的都安全」。免疫系统还得能识别病，
    否则它就是个只会盖章的门。下面三条是 21.13 那三个反例的
    「无证书」形式：不是「我们没找到变式」，是**这样的变式不存在**。

    这是强得多的结论。它说明准入门不是随意设的门槛：
    门外的形状里，有些确实没有任何通行证。
-/

/-- 反例〇：循环体不动、条件恒真。递减义务退化成 `V st < V st`，
    任何变式都过不了——这是「没有变式」最干净的形态。
    对应 21.13 第一个（`f(n) = f(n+1) + 1`）在循环侧的同胞：
    每层都在做一点事，但没有任何一个量在下降。 -/
theorem no_variant_identity :
    ¬ ∃ V : Nat → Nat, ∀ st : Nat, V st < V st := by
  rintro ⟨V, hV⟩
  exact Nat.lt_irrefl (V 0) (hV 0)

/-- 反例二：一直在下降，却到不了底。
    状态域是整数，转移是 `n ↦ n - 1`。整数在「小于」下没有最小元，
    所以不存在 `V : Int → Nat` 使每一轮都严格下降。
    「在下降」和「会到底」是两件事，缺的那一件叫良基。 -/
theorem no_variant_int_descent :
    ¬ ∃ V : Int → Nat, ∀ n : Int, V (n - 1) < V n := by
  rintro ⟨V, hV⟩
  exact no_infinite_descent (r := (· < ·)) Nat.lt_wfRel.wf
    ⟨fun k => V (-(k : Int)), fun k => by
      have h := hV (-(k : Int))
      have he : -(k : Int) - 1 = -((k : Int) + 1) := by omega
      rwa [he] at h⟩

/-- 反例三：外形是「遍历一个有限集合」，实际不是。
    循环体不停往被遍历的集合里追加元素——待遍历的元素数每轮 +1。
    以「剩余元素数」为变式，它必须每轮严格下降；而它每轮严格上升。
    所以不存在这样的 `V`。对应 `for x in xs: xs.append(x)`：
    有限性必须被认证，不能从外形上读出来。 -/
theorem no_variant_growing_queue :
    ¬ ∃ V : Nat → Nat, ∀ q : Nat, V (q + 1) < V q := by
  rintro ⟨V, hV⟩
  exact no_infinite_descent Nat.lt_wfRel.wf ⟨fun k => V k, fun k => hV k⟩

/-! # 六、这套东西在免疫系统里的位置

    21.16 说免疫有两道门。上面这些定理分别落在哪：

      准入门（第一道）  `Loop.dec` 是字段 —— 不带证书的循环构造不出来；
                         `admission_sound` —— 通过的必停，且上界可算。
      监测门（第二道）  `runFuel` 的燃料 —— 熔断返回 `none`，可执行、可观测；
                         `countdown_needs_more_than_4` 演示熔断真的会发生。

    还有一处必须诚实写明，否则这套说法会显得比它实际做到的强：
    **可判的只有结构那一半。** 燃料计数、覆盖形状、变式值域，这些是
    `Bool`，自动且便宜；而「每轮真的变小」这条义务要对全体状态量化，
    它不是 `Bool` 判定，是**内核逐条检查的证明项**——机械、局部、便宜，
    但不是「算一下就有答案」。21.14 说这是**证书关系，不是判定关系**，
    在机器上就是这个区别。把它说成「自动判定」，是夸大。
-/

/-! # 七、数值自测（编译时执行）

    上界 17 步够、4 步不够，两条都是机器算出来的，不是估的。 -/

#eval runFuel countdownLoop.guard countdownLoop.body 17 17   -- some 0
#eval runFuel countdownLoop.guard countdownLoop.body 4 17    -- none
#eval runFuel countdownLoop.guard countdownLoop.body 0 0     -- some 0（条件本就是假）

end FoldingNaming
