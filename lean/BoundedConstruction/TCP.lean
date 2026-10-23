/-
  折叠与命名 · 第 19 章「验证 TCP/IP」的机器复算

  书内位置：
    19.1  RFC 793 的 11 个状态
    19.2  按连接阶段划分等价类（表 34）
    19.3  第一次失败：rcv_ack 的双重含义
    19.4  第二次失败：RST 兜底不成立
    19.5  被验证的属性（安全性 / 活跃性 / 不变量 / 精化）

  ⚠ 口径先说清楚（19.6 的规矩）：
    下面这个转移表是**按书内 19.1–19.5 的文字重建的教学模型**，
    不是 RFC 793 全文，也不是作者当年那个脚本的原件。
    它与书里印出来的东西在结构上对齐：11 个状态、书内点名的那几个事件、
    19.3 与 19.4 那两次失败的具体形态、19.5 的四条属性。
    结论只对这个重建模型成立——这是复算，不是原件存档。

  为什么值得做：
    19.5 最后一条「精化（simulation）」是全书方法论的核心，
    但它是四条属性里唯一一条**没有说清口径**的。
    这里把它拆成强弱两种，一条证伪、一条证明——
    差别不是修辞，是「抽象允不允许停步」。
-/

set_option linter.unusedVariables false

namespace FoldingNaming

/-! # 一、具体系统：11 个状态、9 个事件（19.1） -/

inductive TcpState where
  | CLOSED | LISTEN | SYN_SENT | SYN_RECEIVED | ESTABLISHED
  | FIN_WAIT_1 | FIN_WAIT_2 | CLOSE_WAIT | LAST_ACK | CLOSING | TIME_WAIT
  deriving DecidableEq, Repr

inductive TcpEvent where
  | app_connect | app_close
  | rcv_syn | rcv_syn_ack | rcv_ack | rcv_fin | rcv_rst
  | timeout
  | app_data
  deriving DecidableEq, Repr

/-! # 二、19.4 的对照：补全前 vs 补全后

    `stepV1` 是补全前的版本：RST 只在部分状态下有定义。
    `stepV2` 是补全后的版本：**全函数**——任何 (状态, 事件) 都有明确规定，
    非法事件的行为是「忽略」（自环），不是「未定义」。

    「连不可预测的事件本身，也是一个需要被建模的状态」`[2259]`，
    在类型上是这么落地的：全函数没有 `none` 这个出口。
-/

/-- 补全后：全函数。默认分支是自环，即「该事件在此状态下被忽略」。 -/
def stepV2 : TcpState → TcpEvent → TcpState
  | .CLOSED, .app_connect => .SYN_SENT
  | .CLOSED, .rcv_syn => .SYN_RECEIVED
  | .LISTEN, .rcv_syn => .SYN_RECEIVED
  | .LISTEN, .app_close => .CLOSED
  | .LISTEN, .rcv_rst => .CLOSED
  | .SYN_SENT, .rcv_syn_ack => .ESTABLISHED
  | .SYN_SENT, .rcv_syn => .SYN_RECEIVED
  | .SYN_SENT, .rcv_rst => .CLOSED
  | .SYN_SENT, .app_close => .CLOSED
  | .SYN_RECEIVED, .rcv_ack => .ESTABLISHED
  | .SYN_RECEIVED, .rcv_rst => .CLOSED
  | .SYN_RECEIVED, .app_close => .CLOSED
  | .ESTABLISHED, .app_close => .FIN_WAIT_1
  | .ESTABLISHED, .rcv_fin => .CLOSE_WAIT
  | .ESTABLISHED, .rcv_rst => .CLOSED
  | .FIN_WAIT_1, .rcv_ack => .FIN_WAIT_2
  | .FIN_WAIT_1, .rcv_fin => .CLOSING
  | .FIN_WAIT_1, .rcv_rst => .CLOSED
  | .FIN_WAIT_2, .rcv_fin => .TIME_WAIT
  | .FIN_WAIT_2, .rcv_rst => .CLOSED
  | .CLOSE_WAIT, .app_close => .LAST_ACK
  | .CLOSE_WAIT, .rcv_rst => .CLOSED
  | .LAST_ACK, .rcv_ack => .CLOSED
  | .LAST_ACK, .rcv_rst => .CLOSED
  | .CLOSING, .rcv_ack => .TIME_WAIT
  | .CLOSING, .rcv_rst => .CLOSED
  | .TIME_WAIT, .timeout => .CLOSED
  | s, _ => s

/-- 补全前：RST 在中间态没有定义。 -/
def stepV1 (s : TcpState) (e : TcpEvent) : Option TcpState :=
  match s, e with
  | .FIN_WAIT_1, .rcv_rst => none
  | .FIN_WAIT_2, .rcv_rst => none
  | .CLOSE_WAIT, .rcv_rst => none
  | .LAST_ACK,   .rcv_rst => none
  | .CLOSING,    .rcv_rst => none
  | s, e => some (stepV2 s e)

/-- 19.4 那个失败的精确形态：`FIN_WAIT_1` 收到 `rcv_rst`，补全前是**未定义**。 -/
theorem v1_rst_undefined : stepV1 .FIN_WAIT_1 .rcv_rst = none := rfl

/-- 补全是保守的：原来有定义的地方，补全后行为不变。 -/
theorem v1_eq_some_v2 (s : TcpState) (e : TcpEvent) (h : (stepV1 s e).isSome) :
    stepV1 s e = some (stepV2 s e) := by
  cases s <;> cases e <;> simp [stepV1] at h ⊢

/-! # 三、19.2 的折叠：按连接阶段分三类（表 34）

    closed = {CLOSED}
    handshaking = {LISTEN, SYN_SENT, SYN_RECEIVED}
    active = {ESTABLISHED, FIN_WAIT_1, FIN_WAIT_2, CLOSE_WAIT, LAST_ACK, CLOSING, TIME_WAIT}

    压缩比 11 / 3 ≈ 3.67。 -/

inductive Abs where
  | closed | handshaking | active
  deriving DecidableEq, Repr

def alpha3 : TcpState → Abs
  | .CLOSED => .closed
  | .LISTEN | .SYN_SENT | .SYN_RECEIVED => .handshaking
  | _ => .active

/-! # 四、精化：强模拟与弱模拟，差在「抽象能不能停步」

    **强模拟**要求具体走一步，抽象必须走一步，而且目标类对得上。
    这是最直觉的口径，也是书里 19.3 那次失败默认的口径。

    抽象的转移表这样定：对每个 (类, 事件)，看类内各状态**跨类**的目标类；
    唯一则照写，全都留在类内则自环。 -/

def absStep3 : Abs → TcpEvent → Abs
  | .closed, .app_connect => .handshaking
  | .closed, .rcv_syn => .handshaking
  | .closed, _ => .closed
  | .handshaking, .app_close => .closed
  | .handshaking, .rcv_syn_ack => .active
  | .handshaking, .rcv_ack => .active
  | .handshaking, .rcv_rst => .closed
  | .handshaking, _ => .handshaking
  | .active, .rcv_ack => .closed
  | .active, .rcv_rst => .closed
  | .active, .timeout => .closed
  | .active, _ => .active

/-- **强模拟不成立。** 见证：`ESTABLISHED` 收到 `rcv_ack`。
    具体系统里它是数据确认，状态不变（还在 active）；
    抽象系统里 `rcv_ack` 却必须移到 closed——因为 `LAST_ACK` 收到 `rcv_ack`
    是关闭确认，而 `LAST_ACK` 也在 active 类里。

    这就是 19.3 那次失败的精确形状：**同一个事件名在同一个等价类里有两个目标**。
    书里只点了两种语义（握手确认、数据确认），这里是第三种：关闭确认。 -/
theorem strong_simulation_fails :
    ∃ s e, alpha3 (stepV2 s e) ≠ absStep3 (alpha3 s) e :=
  ⟨.ESTABLISHED, .rcv_ack, by decide⟩

/-- **弱（stuttering）模拟成立。** 放宽一件事：具体走一步时，
    抽象允许**停在原地**——折叠丢掉了状态细节，具体系统的每一步
    不一定在抽象里有对应步，这是投影的正常代价，不是错误。

    这条是 19.5 最后一条「抽象不遗漏任何具体行为」的正确形式：
    不遗漏 ≠ 一一对应。 -/
theorem stuttering_simulation (s : TcpState) (e : TcpEvent) :
    alpha3 (stepV2 s e) = alpha3 s ∨ alpha3 (stepV2 s e) = absStep3 (alpha3 s) e := by
  cases s <;> cases e <;> decide

/-! # 五、19.5 的四条属性

    安全性、活跃性、不变量两条。每条都落成一个全称定理，
    不是抽样、不是「跑过没出错」。 -/

/-! ## 安全性：□(¬Connected → ¬DataSent) -/

/-- 这个状态上是否真的会发出数据：只有 ESTABLISHED 会。 -/
def sendsData : TcpState → Bool
  | .ESTABLISHED => true
  | _ => false

/-- **未握手绝不发数据。** 没有假设、没有前提，是对 11 个状态的全称。 -/
theorem no_data_before_established (s : TcpState) (h : sendsData s = true) :
    s = .ESTABLISHED := by
  cases s <;> simp [sendsData] at h ⊢

/-- 同一个事实的转移形式：非 ESTABLISHED 状态下，数据事件不改变任何东西。 -/
theorem app_data_only_in_established (s : TcpState) (h : s ≠ .ESTABLISHED) :
    stepV2 s .app_data = s := by
  cases s <;> simp [stepV2] at h ⊢

/-! ## 不变量一：ESTABLISHED 必经 SYN 交换 -/

/-- **从别处进 ESTABLISHED 只有两条路**：主动打开的 `rcv_syn_ack`、
    被动打开的 `rcv_ack`。没有第三条。

    前置条件 `s ≠ ESTABLISHED` 不能省：ESTABLISHED 对多数事件是自环，
    不排除它，命题就是假的。这个坑和第 16 章那个 RED 自环是同一个
    （见 `m_red_entry`）——「入口不变式」永远要先把自环摘出去。

    这是「必经 SYN 交换」在 FSM 上唯一能说准的形式——
    真正的「历史」不在状态里，所以只能证入口，不能证路径。 -/
theorem established_entry (s : TcpState) (e : TcpEvent) (hs : s ≠ .ESTABLISHED)
    (h : stepV2 s e = .ESTABLISHED) :
    (s = .SYN_SENT ∧ e = .rcv_syn_ack) ∨ (s = .SYN_RECEIVED ∧ e = .rcv_ack) := by
  revert h hs
  cases s <;> cases e <;> decide

/-! ## 不变量二：TIME_WAIT 必须等 2MSL -/

/-- **TIME_WAIT 吸收除 `timeout` 以外的一切事件**，包括 RST。
    「必须等 2MSL」在状态机上的落点就是这句：没有别的出口。

    注意这里有一处刻意的取舍：RFC 793 允许 TIME_WAIT 收到 RST 提前关闭，
    那会破坏这条不变量。这里选择让 RST 被吸收（RFC 1337 的做法），
    因为 19.5 把「必须等 2MSL」写成了不变量——两条不能同时成立，
    必须选一条。这个取舍必须写明，否则就是偷偷改了模型。 -/
theorem time_wait_absorbs (e : TcpEvent) (h : e ≠ .timeout) :
    stepV2 .TIME_WAIT e = .TIME_WAIT := by
  cases e <;> simp [stepV2] at h ⊢

/-- 反过来：从 TIME_WAIT 出去，只有 `timeout` 一条路。 -/
theorem time_wait_exit (e : TcpEvent) (h : stepV2 .TIME_WAIT e ≠ .TIME_WAIT) :
    e = .timeout := by
  cases e <;> simp [stepV2] at h ⊢

/-! ## 活跃性：给出路径，而不是断言存在 -/

def run : List TcpEvent → TcpState → TcpState
  | [], s => s
  | e :: es, s => run es (stepV2 s e)

/-- 握手 → ESTABLISHED：两步，`app_connect` 后 `rcv_syn_ack`。 -/
theorem handshake_reaches_established :
    run [.app_connect, .rcv_syn_ack] .CLOSED = .ESTABLISHED := rfl

/-- 关闭 → CLOSED，**并经过 FIN_WAIT_2 与 TIME_WAIT**。
    路径本身就是证明的一部分——活跃性在这个框架里是构造性的，
    不是「存在某个执行」，是「这条执行」。 -/
theorem close_reaches_closed :
    run [.app_close, .rcv_ack, .rcv_fin, .timeout] .ESTABLISHED = .CLOSED := rfl

/-- 同一条路径的中间站：这一步经过 TIME_WAIT，不是直跳。 -/
theorem close_path_visits_time_wait :
    run [.app_close, .rcv_ack, .rcv_fin] .ESTABLISHED = .TIME_WAIT := rfl

/-! # 六、数值自测 -/

#eval (11 : Nat)   -- 11 个状态
#eval (3 : Nat)    -- 3 个等价类
#eval (11.0 / 3.0) -- 压缩比 3.666…
#eval sendsData .ESTABLISHED   -- true
#eval sendsData .SYN_SENT      -- false
#eval stepV1 .FIN_WAIT_1 .rcv_rst   -- none（19.4 的缺口）
#eval stepV2 .FIN_WAIT_1 .rcv_rst   -- CLOSED（补全后）
#eval stepV2 .TIME_WAIT .rcv_rst    -- TIME_WAIT（吸收，保 2MSL）

end FoldingNaming
