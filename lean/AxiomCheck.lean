/-
  折叠与命名 · 形式验证的诚实性检查

  这个文件不做证明，只做一件事：把每条主要定理的**公理依赖**打印出来。

  判据：
    · 输出 `depends on axioms: [propext, Classical.choice, Quot.sound]` —— 正常，
      这三条是 Lean 的标准公理，任何数学证明都可以用。
    · 出现 `sorryAx` —— 说明那条定理是假的证明（有未填的洞），必须修掉。
    · 什么都不依赖 —— 更好，纯构造性证明。

  跑法：lake build 之后 `lean AxiomCheck.lean`，或直接看 build 输出。
-/

import BoundedConstruction

open FoldingNaming

/-! ## Basic：良基序与变式 -/
#print axioms acc_no_descent
#print axioms no_infinite_descent
#print axioms variant_bounds_steps
#print axioms loop_terminates
#print axioms recursion_reduces_to_variant
#print axioms no_solution_unbounded_recursion

/-! ## Lexicographic：字典序变式 -/
#print axioms lex_acc
#print axioms lex_pair_wellFounded
#print axioms ack_step₁
#print axioms ack_step₂
#print axioms ack_step₃
#print axioms ack

/-! ## While：带变式的循环 -/
#print axioms runBasic
#print axioms runWhile
#print axioms countdown

/-! ## Certificate：把公理当判据用 -/
#print axioms fuel_enough
#print axioms Loop.stops
#print axioms admission_sound
#print axioms countdownLoop
#print axioms countdown_stops_in_17
#print axioms countdown_needs_more_than_4
#print axioms no_variant_identity
#print axioms no_variant_int_descent
#print axioms no_variant_growing_queue

/-! ## FSM：管理 FSM -/
#print axioms m_no_red_green
#print axioms m_closed_absorb
#print axioms m_red_entry
#print axioms m_resign_to_red
#print axioms m_green_reaches
#print axioms m_all_reach_closed

/-! ## FSM：横切 FSM -/
#print axioms x_closed_rejects_all
#print axioms x_escalated_entry
#print axioms x_to_closed
#print axioms x_idem_detect
#print axioms x_idem_contain
#print axioms x_idem_escalate
#print axioms x_idem_recover
#print axioms x_idem_review
#print axioms x_contain_outside
#print axioms x_idle_reaches
#print axioms x_all_reach_closed

/-! ## TCP：第 19 章的复算 -/
#print axioms v1_rst_undefined
#print axioms v1_eq_some_v2
#print axioms strong_simulation_fails
#print axioms stuttering_simulation
#print axioms no_data_before_established
#print axioms app_data_only_in_established
#print axioms established_entry
#print axioms time_wait_absorbs
#print axioms time_wait_exit
#print axioms handshake_reaches_established
#print axioms close_reaches_closed
#print axioms close_path_visits_time_wait

/-! ## Gate：闸门（进出口） -/
#print axioms screen_rejects_sound
#print axioms certify_sound
#print axioms certified_implies_screened
#print axioms claimStuck_has_no_evidence

/-! ## 压 缩 -/
#print axioms compress_trail
