/-
  折叠与命名 · 第 16–17 章两个 FSM 的机器验证
  第三部分：管理 FSM（表 30）与横切 FSM（图 18 + 表 32）

  无外部依赖，仅 Lean 4 core。

  与 chapter_16_17_fsm/fsm_verify.py 的关系：
    那份脚本用 Python 对同一批性质做 19 项检查（穷举 + 随机压力）。
    本文件用 Lean 对同一批性质做**证明**——不是抽样，是对所有状态与事件全称成立。

  两套方法对同四类属性（书内表 37）：
    完备性 / 安全性 / 活跃性 / 不变量

  一个直接的好处：脚本的前四项（完备性、目标合法 × 两个 FSM）在 Lean 里
  由类型系统免费给出——`mStep : MState → MEvent → Option MState` 是全函数，
  结果只可能是已声明状态或「拒绝」（`none`），不存在第三种情况。
  这四项在脚本里需要逐格填表再核对，在类型系统里是不可表达的非法状态。
-/

set_option linter.unusedVariables false

namespace FoldingNaming

/-! # 一、管理 FSM（书里表 30：4 状态 × 6 事件） -/

inductive MState where
  | GREEN | YELLOW | RED | CLOSED
  deriving DecidableEq, Repr

inductive MEvent where
  | escalation | member_resign | project_end | report_green | report_red | report_yellow
  deriving DecidableEq, Repr

/-- 转移函数。`some s'` = 允许的转移，`none` = 拒绝（书里表里的 REJECT）。
    与表 30 逐格对应。 -/
def mStep : MState → MEvent → Option MState
  | .CLOSED, .project_end => some .CLOSED
  | .CLOSED, _ => none
  | .GREEN, .escalation => none
  | .GREEN, .member_resign => some .RED
  | .GREEN, .project_end => some .CLOSED
  | .GREEN, .report_green => some .GREEN
  | .GREEN, .report_red => some .YELLOW
  | .GREEN, .report_yellow => some .YELLOW
  | .RED, .escalation => some .RED
  | .RED, .member_resign => some .RED
  | .RED, .project_end => none
  | .RED, .report_green => some .YELLOW
  | .RED, .report_red => some .RED
  | .RED, .report_yellow => some .RED
  | .YELLOW, .escalation => some .RED
  | .YELLOW, .member_resign => some .RED
  | .YELLOW, .project_end => some .CLOSED
  | .YELLOW, .report_green => some .GREEN
  | .YELLOW, .report_red => none
  | .YELLOW, .report_yellow => some .YELLOW

/-! ## 安全性 -/

/-- 脚本第 3 项：不存在 RED → GREEN 的捷径。 -/
theorem m_no_red_green (e : MEvent) : mStep .RED e ≠ some .GREEN := by
  cases e <;> simp [mStep]

/-- 脚本第 4 项：CLOSED 只接受「项目结束」这一个自环，其余全部拒绝。 -/
theorem m_closed_absorb (e : MEvent) :
    mStep .CLOSED e = none ∨ e = .project_end := by
  cases e <;> simp [mStep]

/-! ## 不变量 -/

/-- 脚本第 7 项：**首次**进入 RED 只可能由 escalation 或 member_resign 触发。
    （`hs` 排除 RED 自身的自环：`RED + report_red = RED` 是留在 RED，不是进入。） -/
theorem m_red_entry (s : MState) (e : MEvent) (hs : s ≠ .RED)
    (h : mStep s e = some .RED) : e = .escalation ∨ e = .member_resign := by
  cases s <;> cases e <;> simp [mStep] at h hs ⊢

/-- 脚本第 8 项：非 CLOSED 状态下，核心离职一律进 RED。 -/
theorem m_resign_to_red (s : MState) (h : s ≠ .CLOSED) :
    mStep s .member_resign = some .RED := by
  cases s <;> simp [mStep] at h ⊢

/-! ## 活跃性 -/

/-- 一条轨迹（事件序列）的执行。 -/
def runM : MState → List MEvent → Option MState
  | s, [] => some s
  | s, e :: es => (mStep s e).bind (fun s' => runM s' es)

/-- 脚本第 5 项：GREEN → CLOSED 可达。 -/
theorem m_green_reaches : runM .GREEN [.project_end] = some .CLOSED := rfl

/-- 脚本第 6 项（四个状态逐个给出路径）。
    「可达」在这里是构造性的：路径本身是证明的一部分，可以被执行。 -/
theorem m_all_reach_closed (s : MState) : ∃ es, runM s es = some .CLOSED := by
  cases s
  · exact ⟨[.project_end], rfl⟩
  · exact ⟨[.project_end], rfl⟩
  · exact ⟨[.report_green, .project_end], rfl⟩
  · exact ⟨[], rfl⟩

/-! # 二、横切 FSM（书里图 18 + 表 32：7 状态 × 6 事件） -/

inductive XState where
  | IDLE | DETECTED | CONTAINED | ESCALATED | RECOVERED | REVIEWED | CLOSED
  deriving DecidableEq, Repr

inductive XEvent where
  | detect | contain | escalate | recover | review | close
  deriving DecidableEq, Repr

def xStep : XState → XEvent → Option XState
  | .IDLE, .detect => some .DETECTED
  | .IDLE, _ => none
  | .DETECTED, .detect => some .DETECTED
  | .DETECTED, .contain => some .CONTAINED
  | .DETECTED, .escalate => some .ESCALATED
  | .DETECTED, _ => none
  | .CONTAINED, .contain => some .CONTAINED
  | .CONTAINED, .escalate => some .ESCALATED
  | .CONTAINED, .recover => some .RECOVERED
  | .CONTAINED, _ => none
  | .ESCALATED, .contain => some .CONTAINED
  | .ESCALATED, .escalate => some .ESCALATED
  | .ESCALATED, _ => none
  | .RECOVERED, .recover => some .RECOVERED
  | .RECOVERED, .review => some .REVIEWED
  | .RECOVERED, _ => none
  | .REVIEWED, .review => some .REVIEWED
  | .REVIEWED, .close => some .CLOSED
  | .REVIEWED, _ => none
  | .CLOSED, _ => none

/-! ## 安全性 -/

/-- 脚本第 12 项（更强）：CLOSED 之后所有事件全拒绝，不只是业务事件。 -/
theorem x_closed_rejects_all (e : XEvent) : xStep .CLOSED e = none := by
  cases e <;> rfl

/-! ## 不变量 -/

/-- 脚本第 15 项：ESCALATED 只能由 escalate 进入。 -/
theorem x_escalated_entry (s : XState) (e : XEvent)
    (h : xStep s e = some .ESCALATED) : e = .escalate := by
  cases s <;> cases e <;> simp [xStep] at h ⊢

/-- **比脚本更强的一条**：进入 CLOSED 只有一条路——
    必须从 REVIEWED 出发、且只有 close 事件。
    这就是「免疫系统走完全部检查站才允许关单」的机器版，
    也是整章「不变量」一词最实在的落点。 -/
theorem x_to_closed (s : XState) (e : XEvent)
    (h : xStep s e = some .CLOSED) : s = .REVIEWED ∧ e = .close := by
  cases s <;> cases e <;> simp [xStep] at h ⊢

/-- 脚本第 16 项：阶段内幂等，五处自环。 -/
theorem x_idem_detect : xStep .DETECTED .detect = some .DETECTED := rfl
theorem x_idem_contain : xStep .CONTAINED .contain = some .CONTAINED := rfl
theorem x_idem_escalate : xStep .ESCALATED .escalate = some .ESCALATED := rfl
theorem x_idem_recover : xStep .RECOVERED .recover = some .RECOVERED := rfl
theorem x_idem_review : xStep .REVIEWED .review = some .REVIEWED := rfl

/-- 脚本第 17 项：阶段外拒绝——contain 在 IDLE / RECOVERED / REVIEWED / CLOSED 全拒绝。 -/
theorem x_contain_outside :
    xStep .IDLE .contain = none ∧ xStep .RECOVERED .contain = none ∧
    xStep .REVIEWED .contain = none ∧ xStep .CLOSED .contain = none := by
  simp [xStep]

/-! ## 活跃性 -/

def runX : XState → List XEvent → Option XState
  | s, [] => some s
  | s, e :: es => (xStep s e).bind (fun s' => runX s' es)

/-- 脚本第 13 项：IDLE → CLOSED 可达。 -/
theorem x_idle_reaches :
    runX .IDLE [.detect, .contain, .recover, .review, .close] = some .CLOSED := rfl

/-- 脚本第 14 项：七个状态均可达 CLOSED。 -/
theorem x_all_reach_closed (s : XState) : ∃ es, runX s es = some .CLOSED := by
  cases s
  · exact ⟨[.detect, .contain, .recover, .review, .close], rfl⟩
  · exact ⟨[.contain, .recover, .review, .close], rfl⟩
  · exact ⟨[.recover, .review, .close], rfl⟩
  · exact ⟨[.contain, .recover, .review, .close], rfl⟩
  · exact ⟨[.review, .close], rfl⟩
  · exact ⟨[.close], rfl⟩
  · exact ⟨[], rfl⟩

/-! # 三、幂等压缩（脚本第 18 项：11 步 → 8 步）

    书里 17.4 那条轨迹有 3 处「同一阶段重复报告」。
    折叠把它们并成一个：这不是删除信息，是去掉上层不需要区分的重复。 -/

/-- 折叠连续重复的状态。累积器 `acc` 存的是**反序**结果（头部是最后一个状态）；
    两个分支都只对 `rest` 递归，所以是结构递归，Lean 自动接受。 -/
def compressAux : List XState → List XState → List XState
  | acc, [] => acc.reverse
  | [], s :: rest => compressAux [s] rest
  | t :: tl, s :: rest =>
      if t = s then compressAux (t :: tl) rest else compressAux (s :: t :: tl) rest

/-- 折叠连续重复的状态。 -/
def compress (l : List XState) : List XState := compressAux [] l

/-- 书里 17.4 那条 11 步轨迹。 -/
def trail : List XState :=
  [.IDLE, .DETECTED, .CONTAINED, .CONTAINED, .ESCALATED, .CONTAINED,
   .RECOVERED, .RECOVERED, .REVIEWED, .REVIEWED, .CLOSED]

/-- 压缩后的 8 步。 -/
def trailCompressed : List XState :=
  [.IDLE, .DETECTED, .CONTAINED, .ESCALATED, .CONTAINED, .RECOVERED, .REVIEWED, .CLOSED]

/-- 11 步 → 8 步，折掉的正是 3 处重复。用 `native_decide` 对整条轨迹求值比对。 -/
theorem compress_trail : compress trail = trailCompressed := by
  decide

/-- 两条轨迹的长度。 -/
theorem trail_len : trail.length = 11 := rfl
theorem trailCompressed_len : trailCompressed.length = 8 := rfl

end FoldingNaming
