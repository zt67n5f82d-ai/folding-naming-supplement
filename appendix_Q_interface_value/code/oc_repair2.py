#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Experiment 2 (v2) -- invariant-driven rollback repair, PAIRED design.

Why v2 exists (v1 had two defects that made its conclusion unusable):

  Bug 1 (fatal): in `oc_repair.py` the R-raw branch called
      RAW_TPL.format(fails=fails)
  but RAW_TPL embeds _SPEC, which still contains the named fields
  {sig} {ret} {alpha}. So every R-raw unit that actually needed a repair
  raised KeyError('sig') and was written with ok=False. The analyser then
  filtered on r.get("ok") and silently dropped them -- which is exactly
  the survivorship bias that made R-raw look like "0% need repair".

  Bug 2 (design): round 1 was re-run independently for each arm, so the
  two arms almost never shared a failure. A paired comparison therefore
  had no pairs ("配对样本 = 0 对") and could not answer the question.

v2 fixes both:

  * round 1 is run ONCE per (model, task, repeat). Both repair arms are
    then fed the *same* round-1 failure, so every failure yields a real
    pair.
  * the R-raw branch passes the same named fields as R-inv.

Information is matched between the two repair arms on purpose: both get
the failing assertions AND the full pi/alpha contract. They differ ONLY in
framing:
    R-raw : "your code failed these assertions -> fix it"
    R-inv : "invariant violated -> re-derive from the contract and REWRITE
             wholesale, do not patch locally"

Scoring is on the HIDDEN oracle, held out the whole time.
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
from oc_ab import extract_code, run_assertions

# v1 hard-coded "D:/Temp/oc/scratch", which does not exist on every box.
SCRATCH = os.environ.get(
    "OC_SCRATCH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "_scratch"),
)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oc_repair2_results.jsonl")

_SPEC = ("以下是本题的完整规格：\n函数签名：{sig}\n返回值约定：{ret}\n约束：{alpha}")

RAW_TPL = ("你上一版的实现没有通过下列断言：\n{fails}\n\n" + _SPEC + "\n\n"
           "请修正实现，只输出一个完整的 Python 代码块，不要任何解释。")

INV_TPL = ("【不变量 I 被违反｜必须回退重写】\n"
           "上一版实现违反了下列不变量：\n{fails}\n\n" + _SPEC + "\n\n"
           "请依据上行契约 π 从零重新推导整个实现并整体重写"
           "（不要在原实现上做局部补丁），只输出一个完整的 Python 代码块，不要任何解释。")


def _spec_args(task, fails):
    return dict(fails=fails, sig=task["sig"], ret=task["ret"], alpha=task["alpha"])


MAX_WAIT = int(os.environ.get('OC_MAX_WAIT', '900'))


def _run_round(sid, text, max_wait=None):
    if max_wait is None:
        max_wait = MAX_WAIT
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


def _new_session(model, title):
    try:
        return oc.create_session(title, model, cwd=SCRATCH)
    except Exception:
        return oc.create_session(title, model)


def _repair_arm(model, task, fails, arm):
    """One repair attempt; arm in {'R-raw','R-inv'}."""
    tpl = INV_TPL if arm == "R-inv" else RAW_TPL
    msg = tpl.format(**_spec_args(task, fails))          # <- v1 forgot this for R-raw
    sid = _new_session(model, "rep2-%s-%s-%s" % (task["id"], arm, model.split("/")[-1]))
    txt, rounds, tokens = _run_round(sid, msg)
    code = extract_code(txt)
    vp, vt, _ = run_assertions(code, task, task["visible"])
    hp, ht, _ = run_assertions(code, task, task["hidden"])
    return dict(repair=arm,
                round2_visible="%d/%d" % (vp, vt),
                final_hidden="%d/%d" % (hp, ht),
                final_hidden_all=(hp == ht),
                out2=tokens.get("output", 0), rounds2=rounds)


def one(model, task, rep):
    """Paired unit: one round-1 attempt, then BOTH repair arms on the same failure."""
    t0 = time.time()
    rec = {"model": model, "task": task["id"], "repeat": rep}
    try:
        sid = _new_session(model, "rep2-r1-%s-%s-r%d" % (task["id"], model.split("/")[-1], rep))
        txt1, r1, tk1 = _run_round(sid, build_prompt(task, "A"))
        code1 = extract_code(txt1)
        vp1, vt1, vf1 = run_assertions(code1, task, task["visible"])
        hp1, ht1, _ = run_assertions(code1, task, task["hidden"])
        rec.update(dict(round1_visible="%d/%d" % (vp1, vt1),
                        round1_hidden="%d/%d" % (hp1, ht1),
                        round1_visible_all=(vp1 == vt1),
                        out1=tk1.get("output", 0), rounds1=r1))
        if vp1 == vt1:
            # nothing to repair: both arms are recorded as "no-op, final = round1"
            for arm in ("R-raw", "R-inv"):
                rec.setdefault("arms", {})[arm] = dict(
                    repair=arm, needs_repair=False,
                    final_hidden="%d/%d" % (hp1, ht1), final_hidden_all=(hp1 == ht1),
                    out2=0, rounds2=0)
        else:
            fails = "\n".join("- " + f for f in vf1)
            with ThreadPoolExecutor(max_workers=2) as ex:
                futs = {ex.submit(_repair_arm, model, task, fails, arm): arm
                        for arm in ("R-raw", "R-inv")}
                for fu in as_completed(futs):
                    d = fu.result()
                    d["needs_repair"] = True
                    rec.setdefault("arms", {})[d["repair"]] = d
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
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--include-hard", action="store_true")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()
    OUT = args.out
    os.makedirs(SCRATCH, exist_ok=True)
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    pool = TASKS + HARD if args.include_hard else TASKS
    tasks = [t for t in pool if (not args.tasks or t["id"] in args.tasks.split(","))]
    jobs = [(m, t, r) for m in models for t in tasks for r in range(1, args.repeats + 1)]
    print("jobs=%d (models=%d tasks=%d repeats=%d)" % (len(jobs), len(models), len(tasks), args.repeats))
    sys.stdout.flush()
    done = 0
    with open(OUT, "a", encoding="utf-8") as fh, ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(one, m, t, r): (m, t, r) for m, t, r in jobs}
        for fut in as_completed(futs):
            rec = fut.result()
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            done += 1
            arms = rec.get("arms", {})
            print("[%3d/%3d] %-34s %-16s r%-2d r1v=%-5s %s"
                  % (done, len(jobs), rec["model"].replace("opencode/", ""), rec["task"],
                     rec.get("repeat", 1), rec.get("round1_visible"),
                     " ".join("%s=%s" % (a, arms.get(a, {}).get("final_hidden", "-"))
                              for a in ("R-raw", "R-inv"))))
            sys.stdout.flush()
    print("done ->", OUT)


if __name__ == "__main__":
    main()
