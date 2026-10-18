# 《折叠与命名》随书材料

> 书里凡是写了「随书提供」的地方，代码和原始记录都在这。
>
> 这是**材料仓库**，不含书稿、PDF、插图源文件。

- 书：**《折叠与命名》**（简体中文印刷版，2026）
- 作者：翟志广（Zhai Zhiguang）· [ORCID 0009-0006-9497-0084](https://orcid.org/0009-0006-9497-0084)
- 本仓库版本：`v1.0.0`（2026-10-18）

---

## 一、覆盖了书里哪三处承诺

| # | 书内位置 | 原话 | 本仓库兑现位置 |
|---|---------|------|---------------|
| 1 | 附录 O.4（表 68 前） | 「脚本与结果文件随书提供，固定随机种子，四万个样本」 | `appendix_O_roundtrip/` |
| 2 | 附录 O.9 本章边界 | 「脚本与结果都随书提供，可自行改参数复现」 | `appendix_O_roundtrip/`（带 `--M/--n-tasks/--seed`） |
| 3 | 附录 Q.7 本章边界 | 「本轮全部脚本、逐次运行的原始记录与复现步骤见随书材料；判定器自测脚本可独立运行，输出"全部通过"方可信任上述任何数字」 | `appendix_Q_interface_value/` |

书里其余出现「实跑」「验证」的地方，凡是**没有**留下材料的，正文都写明了「脚本与输出未随书保留」（第 16.4 节、第 19.5 节、第 19.6 节、附录 C 的 L3，以及前言那四条贡献的第 4 条）。本仓库同样不含那些东西——不是漏了，是那批东西**确实没有留下来**，书里已经这么交代。

---

## 二、三十秒验完（离线，不需要模型、不需要 API key）

需要 Python 3.8+（实测 3.13.12），只用标准库，无需 `pip install`。

```bash
# 1) 附录 O 的表 68：跑一遍，与存档输出比
python appendix_O_roundtrip/invariant_math.py --out /tmp/o.txt
diff /tmp/o.txt appendix_O_roundtrip/invariant_math_results.txt

# 2) 附录 Q 的判定器：尺子自己先过一遍
python appendix_Q_interface_value/code/oc_oracle_selftest.py

# 3) 附录 Q 的四张表：从 241 条原始记录逐格重算，与书里比对
python appendix_Q_interface_value/code/rescore.py
```

期望输出三行：

```
（diff 无输出 —— 说明表 68 的三个数与书中那次运行逐行一致）
oracle self-test: ALL PASS
✓ 表 74–77 全部与书中数字一致（241 条原始记录 → 四张表，逐格重算）
```

三条都过，等于把「附录 O 那一个数」和「附录 Q 那四张表」从原材料重新算了一遍。任何一条不过，请当作真问题报给作者，不要当成排版误差。

---

## 三、目录

```
appendix_O_roundtrip/            附录 O.4：接口的往返缺陷（表 68）
├── invariant_math.py            生成脚本，单文件、只用标准库
├── invariant_math_results.txt   书中那次运行的原始输出
└── README.md                    模型、两个接口、三个数怎么来的

appendix_Q_interface_value/      附录 Q：接口价值的分解测量（表 73–77）
├── code/                        当时跑的脚本（12 个）+ rescore.py
├── results/                     241 条原始记录（JSONL）+ 运行日志
├── findings/                    设计说明 + 三份实验结论
└── README.md                    四臂设计、复现步骤、四条数据边界
```

原始记录是 **JSONL**，一行一次生成：模型、任务、臂、是否成功、耗时、token 数、逐条断言的通过情况。可以直接用 `grep`/`jq` 查，也可以自己写脚本重算——`rescore.py` 就是干这个的，它不调用当时的汇总脚本，独立算一遍再比对，免得「用同一段代码证明同一段代码」。

---

## 四、读数字之前，请先看这四条

1. **书里的表是算出来的，不是抄的。** 表 74–77 全部可由 `results/` 里 241 条记录重算，逐格不差（含相关系数 −0.949）。这是本仓库最主要的用途。
2. **模型是免费小模型，端点是 2026 年 10 月那几天的。** 现在多半已改名或下线，重跑数字会漂。定稿依据是原始记录，不是重跑的结果。
3. **数据有一处口径不齐：** `nemotron-3-ultra` 只跑了易档八题，另外三个模型跑了十二题。因此表 77 中它那一行的基线是 8 题口径。书里写了「只有四个点、容易被单个点拉动」，但没写这一格口径不同——这一条在 `appendix_Q_interface_value/README.md` 里逐格交代了。
4. **实验 3（α 单独消融）是主轮之后补做的**，144 条记录单独放在 `results/oc_alpha_results.jsonl`，不在表 74–77 的统计范围内。它的结论（α 边际约 +4 个百分点、π 才是主项）与书里 Q.6 第一条一致。

---

## 五、许可与引用

- 代码（`*.py`）：**MIT**，见 `LICENSE`
- 文档与实验记录（`*.md`、`*.txt`、`*.jsonl`、`*.log`）：**CC BY 4.0**，见 `LICENSE-docs`

引用格式见 `CITATION.cff`。若是为了核对数字而引用，请连**版本号**一起引——记录不会变，但重跑会。

---

## English

Companion materials for the book *Folding and Naming* (Chinese, 2026) by Zhai Zhiguang.

Everywhere the book says "scripts and results are provided with the book", they are here — nothing more, nothing less:

- `appendix_O_roundtrip/` — the round-trip-defect experiment behind Table 68 (40,000 samples, fixed seed, pure standard library).
- `appendix_Q_interface_value/` — the full four-arm LLM experiment behind Tables 73–77: 12 scripts, 241 raw run records (JSONL), run logs, and three written findings.

Verify offline in three commands (see §2): the O experiment reproduces its stored output line by line; the grader's self-test prints `ALL PASS`; `rescore.py` recomputes Tables 74–77 from the 241 raw records and matches every cell, including the correlation coefficient −0.949.

What is **not** here: the manuscript, the PDF, artwork sources, and the FSM verification scripts of Chapters 16–17 — those were never kept, and the book says so explicitly (§16.4, §19.5, Appendix C L3).

Code: MIT. Records and documents: CC BY 4.0.
