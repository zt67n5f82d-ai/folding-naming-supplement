# 《折叠与命名》随书材料

> 书里凡是写了「随书提供」的地方，代码、原始记录和运行输出都在这。
>
> 这是**材料仓库**，不含书稿、PDF、插图源文件。

- 书：**《折叠与命名》**（简体中文印刷版，2026）
- 作者：翟志广（Zhai Zhiguang）· [ORCID 0009-0006-9497-0084](https://orcid.org/0009-0006-9497-0084)
- 本仓库版本：`v1.1.0`（2026-10-18）

---

## 一、覆盖了书里哪五处

| # | 书内位置 | 原话 | 本仓库兑现位置 |
|---|---------|------|---------------|
| 1 | 附录 O.4（表 68 前） | 「脚本与结果文件随书提供，固定随机种子，四万个样本」 | `appendix_O_roundtrip/` |
| 2 | 附录 O.9 本章边界 | 「脚本与结果都随书提供，可自行改参数复现」 | `appendix_O_roundtrip/`（带 `--M/--n-tasks/--seed`） |
| 3 | 16.4（表 31 后）、19.6、附录 C 的 L3、前言第 4 条 | 「两个 FSM 各跑 5000 条随机轨迹 × 20 步，无一例未定义转移；测试套件 19 / 19 通过」「幂等压缩 11 → 8 步」 | `chapter_16_17_fsm/` |
| 4 | 附录 Q.7 本章边界 | 「本轮全部脚本、逐次运行的原始记录与复现步骤见随书材料；判定器自测脚本可独立运行，输出"全部通过"方可信任上述任何数字」 | `appendix_Q_interface_value/` |
| 5 | 21.12 有界构造公理、21.14（**下一版书里印**） | 公理①「每处重复控制流都是带良基变式的循环」的机器验证 | `lean/` |

**第 3 项要特别说明**：那两个 FSM 的原始验证脚本没有留下来。本仓库里的是**按书里表 30、表 31、图 18、表 32、以及 17.4 那条 11 步轨迹重建**的脚本，2026-10-18 重跑，24 / 24、42 / 42、19 / 19、5000 条 × 20 步 0 例未定义转移、11 → 8 全部复现。它**不是原件，是复算**——证据强度不同，所以不合并表述。

**第 5 项是 2026-10-22 新增的**，和前面四项性质不同：前面四项是「跑过，没出错」，这一项是**证明**。同一批 FSM 性质，Python 脚本给的是穷举加抽样，Lean 给的是对全部状态与事件的**全称**结论，且可以用 `#print axioms` 逐条核对有没有偷用 `sorry`。当前 40 条，零 `sorryAx`。

这一项里还有一组不一样的定理：**把公理当判据用**（`lean/BoundedConstruction/Certificate.lean`）。它不满足于证明「变式存在 ⇒ 终止」这个数学事实，而是真的拿公理去查程序：给一个不带任何终止性假设的执行器，证明「通过准入检查的程序，从任何初始状态出发都在 `V st` 步内停」——上界可算、不是存在性断言；再对 21.13 的三个反例证明「**这样的证书不存在**」（不是「我们没找到」）。这三件事合起来是免疫系统准入门的完整形态：**可靠、有界、能拒**。「可靠」用的是书里 18 章那个词（sound）：方向只有一个，上近似不漏。

**仍然没有运行记录的**：第 19 章 TCP 的 13 项属性验证、第 21 章 Agent 契约中「接口行为」那部分。它们在书里一直标着「设计目标、只有设计论证」。`lean/` 补的是**公理本身**（终止性的数学内容），不是 Agent 契约——后者要等系统真的跑起来才能验证，本仓库同样不含，不是漏了。

---

## 二、一分钟验完（离线，不需要模型、不需要 API key）

需要 Python 3.8+（实测 3.13），只用标准库，无需 `pip install`。

```bash
# 1) 第 16–17 章的两个 FSM：19 项检查 + 5000×20 随机压力 + 幂等压缩
python chapter_16_17_fsm/fsm_verify.py --out /tmp/fsm.txt
diff /tmp/fsm.txt chapter_16_17_fsm/fsm_verify_output.txt

# 2) 附录 O 的表 68：跑一遍，与存档输出比
python appendix_O_roundtrip/invariant_math.py --out /tmp/o.txt
diff /tmp/o.txt appendix_O_roundtrip/invariant_math_results.txt

# 3) 附录 Q 的判定器：尺子自己先过一遍
python appendix_Q_interface_value/code/oc_oracle_selftest.py

# 4) 附录 Q 的四张表：从 241 条原始记录逐格重算，与书里比对
python appendix_Q_interface_value/code/rescore.py

# 5) 第 21 章公理的机器验证（需要 Lean 4，无 mathlib）
cd lean && lake build && lean AxiomCheck.lean
```

期望输出四行：

```
（两次 diff 都无输出 —— 说明书里那些数与本次运行逐字一致）
oracle self-test: ALL PASS
✓ 表 74–77 全部与书中数字一致（241 条原始记录 → 四张表，逐格重算）
```

第 5 项期望：`Build completed successfully`，且 `AxiomCheck.lean` 打出的每一行
要么是 `does not depend on any axioms`，要么是 `depends on axioms: [propext, Quot.sound]`。
**只要出现 `sorryAx`，那条定理就是假的**。

四处都过，等于把书里三组数字（FSM 的四个数量、表 68 的三个数、表 74–77 的四张表）从原材料重新算了一遍。任何一处不过，请当作真问题报给作者，不要当成排版误差。

`fsm_verify.py` 与 `invariant_math.py` 都是**确定性**的：种子写死，跑两遍输出逐字节相同，所以 `diff` 能当验证手段——存档的那份输出可以被任何人重新生成并比对。

---

## 三、目录

```
chapter_16_17_fsm/               第 16–17 章：两个 FSM 的验证（表 31 / 图 18 / 表 32）
├── fsm_verify.py                验证器：19 项检查 + 5000×20 随机压力 + 11→8 幂等压缩
├── fsm_verify_output.txt        2026-10-18 那次运行的完整输出
└── README.md                    模型出处、19 项检查清单、重跑时发现的一处书内冲突

appendix_O_roundtrip/            附录 O.4：接口的往返缺陷（表 68）
├── invariant_math.py            生成脚本，单文件、只用标准库
├── invariant_math_results.txt   书中那次运行的原始输出
└── README.md                    模型、两个接口、三个数怎么来的

appendix_Q_interface_value/      附录 Q：接口价值的分解测量（表 73–77）
├── code/                        当时跑的脚本（12 个）+ rescore.py
├── results/                     241 条原始记录（JSONL）+ 运行日志
├── findings/                    设计说明 + 三份实验结论
└── README.md                    四臂设计、复现步骤、四条数据边界

lean/                            第 21 章：有界构造公理的机器验证（Lean 4，无 mathlib）
├── BoundedConstruction/Basic.lean          良基序与变式（公理①②、反例）
├── BoundedConstruction/Lexicographic.lean  字典序变式；Ackermann 终止
├── BoundedConstruction/While.lean          带变式的循环（无变式则写不出来）
├── BoundedConstruction/Certificate.lean    把公理当判据用（通过必停、上界可算、反例无证书）
├── BoundedConstruction/FSM.lean            16–17 章两个状态机
├── AxiomCheck.lean                         诚实性检查：逐条打印公理依赖
└── README.md                               对应书内位置、怎么跑、结果
```

原始记录是 **JSONL**，一行一次生成：模型、任务、臂、是否成功、耗时、token 数、逐条断言的通过情况。可以直接用 `grep`/`jq` 查，也可以自己写脚本重算——`rescore.py` 就是干这个的，它不调用当时的汇总脚本，独立算一遍再比对，免得「用同一段代码证明同一段代码」。

---

## 四、读数字之前，请先看这五条

1. **书里的表是算出来的，不是抄的。** 表 74–77 全部可由 `results/` 里 241 条记录重算，逐格不差（含相关系数 −0.949）；表 68 由 4 万样本重算；FSM 的 24 / 42 / 19 / 5000 / 11→8 由 `fsm_verify.py` 重算。这是本仓库最主要的用途。
2. **FSM 那份是重建后重跑的，不是原件。** 原件没留下来。重建依据是书里印出来的表；据它重算，数字与书里一致——这证明「书里那张矩阵确实是完备、安全、活跃、守不变量的」，不证明「当年那个脚本长这样」。
3. **附录 Q 的模型是免费小模型，端点是 2026 年 10 月那几天的。** 现在多半已改名或下线，重跑数字会漂。定稿依据是原始记录，不是重跑的结果。FSM 与附录 O 没有这个问题：它们是纯计算，不受模型影响。
4. **数据有一处口径不齐：** `nemotron-3-ultra` 只跑了易档八题，另外三个模型跑了十二题。因此表 77 中它那一行的基线是 8 题口径。已经查过影响面：在四臂齐全的格上重算（`python rescore.py --balanced`），四臂只动 0.1 个百分点（56.5 / 97.3 / 94.3 / 95.8），**表 74–76 的结论不受影响**；受影响的只有表 77 那一行的口径。书里原话只提了「只有四个点、容易被单个点拉动」，没提这一格，作者已在下一版正文补一句。
5. **Lean 那份证的是公理，不是你的系统。** 它证明的是「给定这个变式，这类程序终止」，以及「这两个 FSM 满足这四类属性」。它**不**证明任何具体系统的终止性——那要先把你的每一处循环找出变式，而**找变式不自动**。自动的只是「给定了变式之后，检查递减」这一步。这条界线书里 21.14 写得很清楚：证书不是判定。

---

## 五、许可与引用

- 代码（`*.py`）：**MIT**，见 `LICENSE`
- 文档与实验记录（`*.md`、`*.txt`、`*.jsonl`、`*.log`）：**CC BY 4.0**，见 `LICENSE-docs`

引用格式见 `CITATION.cff`。若是为了核对数字而引用，请连**版本号**一起引——记录不会变，但重跑会。

---

## English

Companion materials for the book *Folding and Naming* (Chinese, 2026) by Zhai Zhiguang.

Everywhere the book says "scripts and results are provided with the book", they are here:

- `chapter_16_17_fsm/` — the verifier behind the FSM numbers of Chapters 16–17: 19 checks (completeness, safety, liveness, invariants), 5,000 random walks × 20 steps per FSM, and the 11 → 8 idempotent-compression trace. **Rebuilt** from the transition tables printed in the book (the original script was not kept), re-run 2026-10-18; all published numbers reproduce. It is a recomputation, not the original artifact — the README says so in as many words.
- `appendix_O_roundtrip/` — the round-trip-defect experiment behind Table 68 (40,000 samples, fixed seed, pure standard library).
- `appendix_Q_interface_value/` — the full four-arm LLM experiment behind Tables 73–77: 12 scripts, 241 raw run records (JSONL), run logs, and three written findings.
- `lean/` — a Lean 4 formalization (no mathlib) of the Bounded Construction Axiom of Chapter 21: well-founded variants, the lexicographic variant behind the Ackermann ruling, a `while` language in which a loop without a decreasing variant **cannot be written at all**, an admission checker that turns the axiom into a decision procedure (a program that passes runs for at most `V st` steps — a computable bound; the three counterexamples of 21.13 get proofs that **no certificate exists**), and the two finite state machines of Chapters 16–17. Then the same properties the Python verifier checks by enumeration and sampling, proved for all states and events. `lake build` (≈40 s), then `lean AxiomCheck.lean` prints each theorem's axiom dependencies — currently 40 items, zero `sorryAx`.

Verify offline in four commands (see §2): both fixed-seed runs reproduce their stored output byte for byte; the grader's self-test prints `ALL PASS`; `rescore.py` recomputes Tables 74–77 from the 241 raw records and matches every cell, including the correlation coefficient −0.949.

Not here: the manuscript, the PDF, artwork sources, the TCP property checks of Chapter 19, and the interface-behaviour half of the Agent contract in Chapter 21 — those two remain design goals with no runtime record, and the book labels them that way. The Lean development proves the axiom itself (the mathematics of termination), not any particular system: finding the variant is still a human step.

Code: MIT. Records and documents: CC BY 4.0.
