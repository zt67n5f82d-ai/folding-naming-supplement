#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Run the 4-arm x N-task x M-model experiment against the local OpenCode server.

Scoring is mechanical: the extracted code is exec'd and run against
(a) the visible contract assertions and (b) a held-out hidden oracle.
No LLM judge is involved anywhere.
"""
import argparse
import json
import os
import re
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

import oc_client as oc
from oc_tasks import TASKS, ARMS, HELPERS, build_prompt
from oc_tasks_hard import HARD

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oc_ab_results.jsonl")
SCRATCH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_scratch")
os.makedirs(SCRATCH, exist_ok=True)


def all_tasks(include_hard):
    return TASKS + HARD if include_hard else TASKS


def extract_code(text):
    if not text:
        return ""
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", text, re.S)
    if blocks:
        return "\n\n".join(b for b in blocks)
    return text


def run_assertions(code, task, asserts):
    """Return (passed, total, failures)."""
    ns = {}
    ok, fail = 0, []
    try:
        exec(HELPERS, ns)
        if task.get("prep"):
            exec(task["prep"], ns)
        exec(code, ns)
    except Exception:
        return 0, len(asserts), ["EXEC: " + traceback.format_exc(limit=1).strip()[-200:]]
    for a in asserts:
        try:
            if bool(eval(a, ns)):
                ok += 1
            else:
                fail.append(a + "  -> False")
        except Exception as e:
            fail.append(a + "  -> " + type(e).__name__ + ": " + str(e)[:80])
    return ok, len(asserts), fail


def one_run(model, task, arm, max_wait=900):
    t0 = time.time()
    rec = {"model": model, "task": task["id"], "arm": arm}
    try:
        sid = oc.create_session("ab-%s-%s-%s" % (task["id"], arm, model.split("/")[-1]),
                                model, cwd=SCRATCH)
        oc.prompt(sid, build_prompt(task, arm))
        oc.wait(sid, timeout=max_wait)
        msgs = oc.messages(sid)["data"]
        text, rounds, tokens = "", 0, {}
        for m in msgs:
            if m.get("type") == "assistant":
                rounds += 1
                for c in m.get("content", []):
                    if c.get("type") == "text":
                        text += c.get("text", "")
                if m.get("tokens"):
                    t = m["tokens"]
                    tokens = {k: tokens.get(k, 0) + t.get(k, 0)
                              for k in ("input", "output", "reasoning")}
        code = extract_code(text)
        vp, vt, vfails = run_assertions(code, task, task["visible"])
        hp, ht, hfails = run_assertions(code, task, task["hidden"])
        rec.update(dict(ok=True, elapsed=round(time.time() - t0, 1), rounds=rounds,
                        tokens=tokens, code_len=len(code),
                        visible_pass=vp, visible_total=vt, visible_fail=vfails[:3],
                        hidden_pass=hp, hidden_total=ht, hidden_fail=hfails[:4],
                        visible_all=(vp == vt), hidden_all=(hp == ht)))
    except Exception as e:
        rec.update(dict(ok=False, elapsed=round(time.time() - t0, 1),
                        err=type(e).__name__ + ": " + str(e)[:200]))
    return rec


def main():
    global OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True, help="comma-separated model ids")
    ap.add_argument("--tasks", default="", help="comma-separated task ids (default all)")
    ap.add_argument("--arms", default="A,B,C,D")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--include-hard", action="store_true")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    OUT = args.out

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    pool = all_tasks(args.include_hard)
    tasks = [t for t in pool if (not args.tasks or t["id"] in args.tasks.split(","))]
    arms = args.arms.split(",")

    jobs = [(m, t, a, r) for m in models for t in tasks for a in arms
            for r in range(args.reps)]
    print("jobs=%d  models=%d tasks=%d arms=%d reps=%d"
          % (len(jobs), len(models), len(tasks), len(arms), args.reps))
    sys.stdout.flush()

    done = 0
    with open(OUT, "a", encoding="utf-8") as fh, ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(one_run, m, t, a): (m, t, a) for m, t, a, _ in jobs}
        for fut in as_completed(futs):
            rec = fut.result()
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            done += 1
            print("[%3d/%3d] %-42s %-16s %s  h=%s/%s v=%s/%s  %ss  out=%s"
                  % (done, len(jobs), rec["model"], rec["task"], rec["arm"],
                     rec.get("hidden_pass"), rec.get("hidden_total"),
                     rec.get("visible_pass"), rec.get("visible_total"),
                     rec.get("elapsed"), rec.get("tokens", {}).get("output")))
            sys.stdout.flush()
    print("done ->", OUT)


if __name__ == "__main__":
    main()
