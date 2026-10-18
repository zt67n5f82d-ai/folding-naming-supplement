# 附录 Q — 一次真实 LLM 实验：接口价值的分解测量（表 73–77）

对应书里一处：

> **Q.7** 这些数字的边界「（**本轮全部脚本、逐次运行的原始记录与复现步骤见随书材料**；判定器自测脚本可独立运行，输出"全部通过"方可信任上述任何数字。）」

## 目录

```
code/      当时跑实验用的脚本（与那一次运行逐字一致，只有一处本机路径改成了 ~）
results/   逐次运行的原始记录（jsonl）与运行日志（log）
findings/  当时写的设计说明与三份实验结论
```

| 文件 | 是什么 |
|------|--------|
| `code/oc_tasks.py` | 易档 8 题的任务定义：提示词构造、可见断言、隐藏断言 |
| `code/oc_tasks_hard.py` | 难档 4 题（`h_varint` / `h_evaluate` / `h_schedule` / `h_compose`） |
| `code/oc_client.py` | 连本机 OpenCode 服务的 HTTP 客户端（读出模型列表、发提示、取结果） |
| `code/oc_oracle_selftest.py` | **判定器自测**：用手写金标实现跑全部隐藏断言。必须 `ALL PASS`，否则尺子本身是坏的 |
| `code/oc_ab.py` | 四臂扫描主程序（`--arms A,B,C,D,D0`、`--include-hard`、`--out`） |
| `code/oc_analyze.py` | 当时出数的汇总脚本 |
| `code/rescore.py` | **发布时新加的**：不调 `oc_analyze.py`，独立把表 74–77 重算一遍并逐格比对书中数字 |
| `code/oc_repair.py` / `oc_repair2.py` | 实验 2：把不变量放进修复回路里测（阴性结果） |
| `code/oc_repair_analyze.py` / `oc_repair2_analyze.py` | 实验 2 的汇总 |
| `code/oc_rerun.py` / `oc_smoke.py` | 超时格隔离重跑、连通性冒烟测试 |
| `results/oc_all_results.jsonl` | **主轮**：易档 8 题 × 4 模型 × 4 臂的原始记录 |
| `results/oc_hard_results.jsonl` | **主轮**：难档 4 题的原始记录 |
| `results/oc_ab_results.jsonl` | 更早的一次扫描（127 条），主轮的前身 |
| `results/oc_repair_results.jsonl` / `oc_repair2_results.jsonl` | 实验 2 的原始记录（70 + 260 条） |
| `results/oc_alpha_results.jsonl` | 实验 3（α 单独消融，144 条），**在主轮之后补做**，不在表 74–77 的统计范围内 |
| `results/*.log` | 那几次运行的 stdout 日志 |
| `findings/README-实验说明.md` | 实验设计说明（四臂、两套判据、防自欺的三条） |
| `findings/实验1-四臂对照结论.md` | 主轮结论：A ≪ B ≈ C ≈ D |
| `findings/实验2-补样本结论-R45.md` | 实验 2：不变量 + 回滚 vs 通用改错，阴性 |
| `findings/实验3-α单独消融结论.md` | 实验 3：α 的净边际约 +4 个百分点，π 才是主项 |

## 三条离线命令（不需要模型、不需要网络）

```bash
cd code
python oc_oracle_selftest.py     # 期望最后一行：oracle self-test: ALL PASS
python rescore.py                # 期望最后一行：✓ 表 74–77 全部与书中数字一致
```

`rescore.py` 会把 241 条原始记录按「同一 (model, task, arm) 取最后一条、超时按失败计」重算，四张表逐格与书里对：

| 表 | 书的数字 | 重算结果 |
|----|---------|---------|
| 表 74 四臂通过率 | A 56.5 / D 97.4 / C 94.4 / B 95.9 | 一致 |
| 表 75 易档 | 64.6 / 98.9 / 97.2 / 98.9 | 一致 |
| 表 75 难档 | 40.2 / 94.3 / 88.5 / 89.7 | 一致 |
| 表 76 分解 | A→D +40.9、D→C −3.0、C→B +1.5、A→B +39.4 | 一致 |
| 表 77 逐模型 | 52.7 / 70.3 / 73.3 / 34.8，r = −0.949 | 一致 |

换句话说：**书里那四张表不是手抄的，是这 241 条记录算出来的，任何人在自己机器上都能算出同一个数。**

## 重新生成（可选，需要模型端点）

主轮跑的不是 API，是**本机的一个模型服务**（`opencode` 本地服务，用它的免费模型）。所以：

```bash
python oc_client.py                                   # 先确认能列出模型
python oc_ab.py --models <你的模型> --arms A,B,C,D --workers 5 --out new_run.jsonl
python oc_analyze.py new_run.jsonl
```

`oc_client.py` 连的是 `http://127.0.0.1:49374`，口令从 `~/.config/opencode/service.json` 读（原来写死成本机绝对路径，发布时改成了 `~`）。读者若有别的端点，改 `oc_client.py` 里 `SERVER` / `_password()` / 三个 API 路径即可——实验逻辑不依赖特定厂商。

**说清楚**：那几个免费模型是 2026 年 10 月那几天的端点，现在多半已经改名或下线。重跑出来的数字会漂，这不是 bug——**定稿依据是 `results/` 里的原始记录，不是重跑的结果**。

## 读数字之前，请先看这四条

1. **241 条记录，175 格。** 设计是 12 题 × 4 模型 × 4 臂 = 192 格；其中 17 格没有产出记录（`nemotron-3-ultra` 的 4 道难档 × 4 臂 = 16 格，加 `nemotron-3.5-lightning` 的 1 格）。所以 **表 77 里 nemotron-3-ultra 那一行的基线 73.3% 实际只覆盖 8 道易档**，另外三个模型覆盖 12 道题。这是这一版数据的一处口径不齐，书里没写明（作者已知，见下方"已知的那处不齐"）。
2. **24 条 `ok=false`（超时/报错）按失败计**，不剔除。剔除就是存活者偏差：超时集中在"要求输出最长"的那几个臂上。
3. **分母不完全相同**：A 臂 262 条断言，D / C / B 各 267 条——原因就是第 1 条那 17 个空格。
4. **实验 3 是补做的。** 书里 Q.7 说「α 这一轮没有单独消融」，指的是主轮（表 74–77 那一轮）。α 的消融是后来单独加的 D0 臂，144 条记录在 `oc_alpha_results.jsonl`，结论在 `findings/实验3-α单独消融结论.md`：α 的净边际约 +4 个百分点，π 才是主项——这正好是 Q.6 第一条的独立佐证，不是反证。

## 已知的那处不齐

`nemotron-3-ultra` 只跑了易档八题。表 77 的相关系数 −0.95 是四个点算的，四个点里有一个是"8 题口径"、三个是"12 题口径"。书里已经写了「只有四个点，容易被单个点拉动，方向可信，数值不可信」——但没写这一格口径不同。作者认可这是应当写明的一处，改动会落在下一版正文，不在本仓库里悄悄改。

## 许可

代码 MIT，记录与文档 CC BY 4.0。见仓库根目录 `LICENSE` / `LICENSE-docs`。
