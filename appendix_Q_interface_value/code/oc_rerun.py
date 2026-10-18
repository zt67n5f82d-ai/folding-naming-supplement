#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Re-run specific (model, task, arm) cells, e.g. ones that timed out under
load. Appends to the same results file; the analyser keeps the LAST record
per cell, so a successful re-run supersedes the earlier failure.

Usage:
  python oc_rerun.py --out oc_hard_results.jsonl --cells "model|task|arm,..."
or  python oc_rerun.py --out oc_hard_results.jsonl --from-failures
"""
import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from oc_ab import one_run, all_tasks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--cells", default="")
    ap.add_argument("--from-failures", action="store_true")
    ap.add_argument("--include-hard", action="store_true")
    ap.add_argument("--workers", type=int, default=2)
    args = ap.parse_args()

    pool = {t["id"]: t for t in all_tasks(True)}
    cells = []
    if args.from_failures:
        seen = {}
        for line in open(args.out, encoding="utf-8"):
            r = json.loads(line)
            seen[(r["model"], r["task"], r["arm"])] = r
        for (m, t, a), r in seen.items():
            if not r.get("ok"):
                cells.append((m, t, a))
    for spec in args.cells.split(","):
        spec = spec.strip()
        if spec:
            m, t, a = spec.split("|")
            cells.append((m.strip(), t.strip(), a.strip()))

    jobs = [(m, pool[t], a) for m, t, a in cells]
    print("re-running %d cells" % len(jobs)); sys.stdout.flush()
    with open(args.out, "a", encoding="utf-8") as fh, ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(one_run, m, t, a): (m, t["id"], a) for m, t, a in jobs}
        for fut in as_completed(futs):
            rec = fut.result()
            rec["rerun"] = True
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n"); fh.flush()
            print("  %-42s %-16s %s  ok=%s h=%s/%s %ss"
                  % (rec["model"], rec["task"], rec["arm"], rec.get("ok"),
                     rec.get("hidden_pass"), rec.get("hidden_total"), rec.get("elapsed")))
            sys.stdout.flush()


if __name__ == "__main__":
    main()
