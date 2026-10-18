#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Smoke-test every free model on the local OpenCode server."""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import oc_client as oc

PROMPT = ("Output exactly this JSON and nothing else: "
          '{"ok":true,"n":7}')


def one(model):
    t0 = time.time()
    try:
        r = oc.run_once(model, PROMPT, cwd="D:/Temp/oc/scratch",
                        title="smoke", max_wait=180)
        msgs = r["raw"]["data"]
        text = ""
        tokens = {}
        rounds = 0
        for m in msgs:
            if m.get("type") == "assistant":
                rounds += 1
                for c in m.get("content", []):
                    if c.get("type") == "text":
                        text += c.get("text", "")
                tokens = m.get("tokens", tokens)
        return {"model": model, "ok": True, "elapsed": round(time.time() - t0, 1),
                "rounds": rounds, "text": text.strip()[:120], "tokens": tokens}
    except Exception as e:
        return {"model": model, "ok": False, "elapsed": round(time.time() - t0, 1),
                "err": str(e)[:200]}


if __name__ == "__main__":
    models = oc.list_models()
    print("smoke-testing %d models" % len(models))
    with ThreadPoolExecutor(max_workers=5) as ex:
        for r in ex.map(one, models):
            print(json.dumps(r, ensure_ascii=False))
    sys.stdout.flush()
