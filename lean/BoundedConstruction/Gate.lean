/-
  折叠与命名 · 第 21 章「有界构造公理」的机器验证
  第五部分：闸门 —— 一个最小的进出口（切口）

  这一部分是**接口**，不是定理堆。
  前面几个部分各自证了一件事，但读者拿不到一个「往里放东西、拿结果出来」的口子。
  这里立一个最小骨架，四样东西：

      入口   Claim    —— 一份不带证明的申请（纯数据，可 #eval 构造）
      证据   Evidence —— 唯一需要人手交的东西（递减证明）
      筛     screen   —— 可判、便宜、不要证据；能拒
      验     certify  —— 要证据、走内核；能收

  为什么切成两道工序，而不是一个函数：
    21.14 说「检查递减是自动的、便宜的、局部的」，又说「这是证书关系不是判定关系」。
    这两句话在接口上正好对应两个函数：
      能算的、不要证书就能判的那一半 → `screen`
      算不出来、必须交证明的那一半   → `certify`
    把它们合成一个函数，等于把"可判"和"不可判"混成一句话，那是 21.17 警告的夸大。

  怎么往里长（比如加第 19 章的 FSM 属性）：
    ① `Claim` 加一个构造子；
    ② `screen` 加一个分支；
    ③ `certify` 与两条可靠性定理各加一个 case。
    漏一个，编译器直接拒绝编译——不是我提醒你别漏，是类型不让你漏。
-/

import BoundedConstruction.Certificate

set_option linter.unusedVariables false

namespace FoldingNaming

/-! # 一、入口：一份不带证明的申请

    `Claim` 里**没有**递减证明。它只是数据：条件、循环体、变式。
    任何人都能构造，包括构造错的——这是入口该有的样子。

    变式放在入口这一侧，是因为 21.17 `[2594]`：公理不负责找变式，只负责验变式。
    找，是人的事。 -/

structure Claim where
  /-- 循环继续的条件 -/
  guard : Nat → Bool
  /-- 循环体（不含内层循环） -/
  body : Basic
  /-- 变式：那个「每轮严格变小、且有底」的量，由申请人给出 -/
  V : Nat → Nat

/-! # 二、证据：唯一需要人手交的东西

    整个接口里唯一一个依赖类型的字段。
    它不可判、不可算，只能由人（或别的证明器）交上来。 -/

structure Evidence (c : Claim) where
  dec : ∀ st, c.guard st = true → c.V (runBasic c.body st) < c.V st

/-! # 三、出口：判定，带理由

    不用 `Bool`：`Bool` 说不出「为什么拒」。
    免疫系统拒掉一个东西，必须能说出它违反了哪条——
    否则就是 21.17 说的那种「天天报警、等同于没有」的系统。 -/

inductive Verdict where
  | accepted (bound : Nat)
  | rejected (why : String)
  deriving Repr

/-! # 四、第一道工序：筛（可判的那一半）

    真话必须说全：可判的只有结构，不是「每轮真的变小」。
    下面这条是可判部分里唯一有实质的一条：

      变式在入口处已经是 0，而循环条件还是真。
      递减义务于是要求「某个自然数严格小于 0」——
      不必看循环体，也不必看将来，站在门口就能拒。

    这不是启发式，是定理（见 `screen_rejects_sound`）：拒得对。 -/

def Claim.impossible (c : Claim) (st : Nat) : Bool :=
  c.V st == 0 && c.guard st

/-- 拒绝理由做成常量：证明里要能指名道姓，不能留占位符。 -/
def zeroVariantMsg : String :=
  "变式在入口处已是 0 而循环条件为真：递减义务要求一个自然数小于 0"

/-- 结构筛。不要证据，只判结构。 -/
def screen (c : Claim) (st : Nat) : Verdict :=
  if c.impossible st then .rejected zeroVariantMsg else .accepted (c.V st)

/-- **拒得对**：被筛掉的申请，根本交不出证书。
    「不可能」不是我们的态度，是它的处境——这条定理把它钉死。 -/
theorem screen_rejects_sound (c : Claim) (st : Nat) (why : String)
    (h : screen c st = .rejected why) : Evidence c → False := by
  intro e
  cases hb : c.impossible st with
  | true =>
      have hh : c.V st = 0 ∧ c.guard st = true := by
        simpa [Claim.impossible, Bool.and_eq_true, beq_iff_eq] using hb
      have hlt := e.dec st hh.2
      omega
  | false => simp [screen, hb] at h

/-! # 五、第二道工序：验（要证书的那一半）

    `certify` 看上去什么都没做——它直接接受。
    这不是偷懒：**能拿到 `Evidence c` 这件事本身，就已经走完了内核检查**。
    拿不到的人（比如 `claimStuck`），根本构造不出这个参数，
    编译器在调用处就把他拦下来了。

    这正是「准入门」在语言层的形状：不是运行期判你，是类型不让你进门。 -/

def certify (c : Claim) (st : Nat) (_e : Evidence c) : Verdict :=
  .accepted (c.V st)

/-- **收得稳**：验过的，真的在 `bound` 步内停。
    整个接口唯一需要信任的一条定理——它把「闸门说 OK」和「程序真的停」焊在一起。 -/
theorem certify_sound (c : Claim) (st : Nat) (e : Evidence c) (b : Nat)
    (h : certify c st e = .accepted b) :
    (runFuel c.guard c.body b st).isSome = true := by
  change Verdict.accepted (c.V st) = Verdict.accepted b at h
  cases h
  exact fuel_enough c.guard c.body c.V e.dec (c.V st) st (Nat.le_refl _)

/-! # 六、两道工序的关系

    筛掉的，永远验不过；验过的，筛一定放行。
    这两条合起来说明：两道工序不是重复劳动，是同一件事的便宜近似与昂贵确认。 -/

/-- 能拿到证书，结构筛必然放行。 -/
theorem certified_implies_screened (c : Claim) (st : Nat) (e : Evidence c) :
    ∃ b, screen c st = .accepted b := by
  cases hb : c.impossible st with
  | false => exact ⟨c.V st, by simp [screen, hb]⟩
  | true =>
      exact absurd e
        (screen_rejects_sound c st zeroVariantMsg (by simp [screen, hb]))

/-! # 七、三个跑得起来的例子

    最小闭环的证据：同一个闸门，三种输入，三种出口。
    `#eval` 的输出就是"出口"，读者改个参数就能重跑。 -/

/-- 倒计时：变式就是 st 自身。 -/
def claimCountdown : Claim where
  guard := fun s => s > 0
  body := .assign (fun s => s - 1)
  V := fun s => s

/-- 它的证书只有三行——「便宜」不是形容词，是可以数的行数。 -/
def evCountdown : Evidence claimCountdown where
  dec := by
    intro st hs
    simp only [claimCountdown, decide_eq_true_eq] at hs
    simp [claimCountdown, runBasic]
    omega

/-- 恒真循环、循环体不动、变式恒 0：结构上就不可能。 -/
def claimStuck : Claim where
  guard := fun _ => true
  body := .assign id
  V := fun _ => 0

/-- 这个申请**交不出证书**——不是我们没找到，是它不存在。
    注意这是对「任意状态」的否定，不是对某一个初值。 -/
theorem claimStuck_has_no_evidence (st : Nat) : Evidence claimStuck → False := by
  intro e
  have h := e.dec st (by simp [claimStuck])
  simp [claimStuck, runBasic] at h

#eval screen claimCountdown 17      -- accepted 17
#eval screen claimCountdown 0       -- accepted 0（条件本就假）
#eval screen claimStuck 0           -- rejected（结构不可能）
#eval certify claimCountdown 17 evCountdown  -- accepted 17

end FoldingNaming
