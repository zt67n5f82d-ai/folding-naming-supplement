#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Experiment 2 -- invariant-driven rollback repair.

The book claims the third component of the interface triple is
"不变量：违反即回滚". In a SINGLE-SHOT setting a rollback instruction has
no executable meaning (there is no second round to roll back to), which is
why the single-shot arms C and B came out indistinguishable. The third
component can only be tested inside a loop.

Protocol:
  Round 1  every model gets the BARE prompt (arm A) so that failures
           actually occur -- using the full contract in round 1 leaves
           almost nothing to repair and the comparison has no power.
  Gate     run the VISIBLE oracle
  Round 2  only for failures. BOTH arms receive *identical information*
           (the failing assertions AND the full pi/alpha contract); they
           differ ONLY in framing:
             R-raw : "your code failed these assertions -> fix it"
             R-inv : "invariant violated -> re-derive from the contract and
                      REWRITE wholesale, do not patch locally"
  Score    HIDDEN oracle after the repair (held out the whole time)

Information is matched between the two repair arms on purpose: otherwise
the comparison would again conflate information with framing.
"""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import oc_client as oc
from oc_tasks import TASKS, build_prompt
from oc_tasks_hard import HARD
from oc_ab import extract_code, run_assertions, SCRATCH

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oc_repair_results.jsonl")

_SPEC = ("以下是本题的完整规格：\n函数签名：{sig}\n返回值约定：{ret}\n约束：{alpha}")

RAW_TPL = ("你上一版的实现没有通过下列断言：\n{fails}\n\n" + _SPEC + "\n\n"
           "请修正实现，只输出一个完整的 Python 代码块，不要任何解释。")

INV_TPL = ("【不变量 I 被违反｜必须回退重写】\n"
           "上一版实现违反了下列不变量：\n{fails}\n\n" + _SPEC + "\n\n"
           "请依据上行契约 π 从零重新推导整个实现并整体重写"
           "（不要在原实现上做局部补丁），只输出一个完整的 Python 代码块，不要任何解释。")


def _run_round(sid, text, task, max_wait=900):
    oc.prompt(sid, text)
    oc.wait(sid, timeout=max_wait)
    msgs = oc.messages(sid)["data"]
    text_out, rounds, tokens = "", 0, {}
    for m in msgs:
        if m.get("type") == "assistant":
            rounds += 1
            for c in m.get("content", []):
                if c.get("type") == "text":
                    text_out += c.get("text", "")
            t = m.get("tokens") or {}
            for k in ("input", "output", "reasoning"):
                tokens[k] = tokens.get(k, 0) + t.get(k, 0)
    return text_out, rounds, tokens


def one(model, task, arm):
    """arm in {'R-raw','R-inv'}; each arm gets its own fresh session so the
    only difference is the repair framing."""
    rec = {"model": model, "task": task["id"], "repair": arm}
    t0 = time.time()
    try:
        sid = oc.create_session("rep-%s-%s-%s" % (task["id"], arm, model.split("/")[-1]),
                                model, cwd=SCRATCH)
        txt1, r1, tk1 = _run_round(sid, build_prompt(task, "A"), task)
        code1 = extract_code(txt1)
        vp1, vt1, vf1 = run_assertions(code1, task, task["visible"])
        hp1, ht1, _ = run_assertions(code1, task, task["hidden"])
        rec.update(dict(round1_visible="%d/%d" % (vp1, vt1),
                        round1_hidden="%d/%d" % (hp1, ht1),
                        round1_visible_all=(vp1 == vt1),
                        out1=tk1.get("output", 0), rounds1=r1))
        if vp1 == vt1:
            rec.update(dict(needs_repair=False, final_hidden="%d/%d" % (hp1, ht1),
                            final_hidden_all=(hp1 == ht1), out2=0))
        else:
            fails = "\n".join("- " + f for f in vf1)
            msg = (INV_TPL.format(fails=fails, sig=task["sig"], ret=task["ret"],
                                  alpha=task["alpha"])
                   if arm == "R-inv" else RAW_TPL.format(fails=fails))
            txt2, r2, tk2 = _run_round(sid, msg, task)
            code2 = extract_code(txt2)
            vp2, vt2, _ = run_assertions(code2, task, task["visible"])
            hp2, ht2, _ = run_assertions(code2, task, task["hidden"])
            rec.update(dict(needs_repair=True,
                            round2_visible="%d/%d" % (vp2, vt2),
                            final_hidden="%d/%d" % (hp2, ht2),
                            final_hidden_all=(hp2 == ht2),
                            out2=tk2.get("output", 0), rounds2=r2))
        rec.update(dict(ok=True, elapsed=round(time.time() - t0, 1)))
    except Exception as e:
        rec.update(dict(ok=False, err=type(e).__name__ + ": " + str(e)[:200],
                        elapsed=round(time.time() - t0, 1)))
    return rec


def main():
    global OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True)
    ap.add_argument("--tasks", default="")
    ap.add_argument("--arms", default="R-raw,R-inv")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--include-hard", action="store_true")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()
    OUT = args.out
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    pool = TASKS + HARD if args.include_hard else TASKS
    tasks = [t for t in pool if (not args.tasks or t["id"] in args.tasks.split(","))]
    arms = args.arms.split(",")
    jobs = [(m, t, a) for m in models for t in tasks for a in arms]
    print("jobs=%d" % len(jobs)); sys.stdout.flush()
    done = 0
    with open(OUT, "a", encoding="utf-8") as fh, ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(one, m, t, a): (m, t, a) for m, t, a in jobs}
        for fut in as_completed(futs):
            rec = fut.result(); fh.write(json.dumps(rec, ensure_ascii=False) + "\n"); fh.flush()
            done += 1
            print("[%2d/%2d] %-40s %-16s %-6s r1v=%-5s r1h=%-5s final=%s"
                  % (done, len(jobs), rec["model"], rec["task"], rec["repair"],
                     rec.get("round1_visible"), rec.get("round1_hidden"),
                     rec.get("final_hidden")))
            sys.stdout.flush()
    print("done ->", OUT)


if __name__ == "__main__":
    main()
