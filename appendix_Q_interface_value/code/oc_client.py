#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OpenCode local-server client.

Auth: HTTP Basic, username "opencode", password from
      ~/.config/opencode/service.json   (原为作者本机绝对路径，发布时改成了 ~)
Server: http://127.0.0.1:49374  (opencode-cli.exe background service, v2.0.23)

        读者若用别的端点：改 SERVER 环境变量，并把 _password() 换成读你自己的口令即可。
        实验逻辑（提示词、断言、判定）不依赖任何特定厂商。

Public API (all via the local server, free models under provider "opencode"):
    list_models()                     -> list of "opencode/<id>"
    run_once(model, text, cwd=None)   -> dict(result text, tokens, steps, elapsed)
"""
import base64
import json
import os
import time
import urllib.request
import urllib.error

SERVER = os.environ.get("OPENCODE_SERVER", "http://127.0.0.1:49374")
CONFIG = os.path.expanduser("~/.config/opencode/service.json")


def _password():
    with open(CONFIG, "r", encoding="utf-8") as f:
        return json.load(f)["password"]


def _auth_header():
    tok = base64.b64encode(("opencode:" + _password()).encode()).decode()
    return "Basic " + tok


def _req(method, path, body=None, timeout=120):
    url = SERVER + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", _auth_header())
    req.add_header("Content-Type", "application/json")
    # bypass any proxy for localhost
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        raise RuntimeError("HTTP %s %s -> %s" % (e.code, path, raw[:400]))


def list_models():
    d = _req("GET", "/api/model")
    out = []
    for m in d.get("data", d if isinstance(d, list) else []):
        pid = m.get("providerID")
        mid = m.get("id")
        if pid and mid:
            out.append("%s/%s" % (pid, mid))
    return out


def create_session(title, model, cwd=None):
    body = {"title": title,
            "model": {"providerID": model.split("/")[0],
                      "id": "/".join(model.split("/")[1:])}}
    if cwd:
        body["location"] = {"directory": cwd}
    d = _req("POST", "/api/session", body)
    return d["data"]["id"]


def prompt(session_id, text, timeout=120):
    return _req("POST", "/api/session/%s/prompt" % session_id, {"text": text}, timeout=timeout)


def wait(session_id, timeout=600):
    return _req("POST", "/api/experimental/session/%s/wait" % session_id, {}, timeout=timeout)


def messages(session_id):
    return _req("GET", "/api/session/%s/message" % session_id)


def run_once(model, text, cwd=None, title="probe", max_wait=600):
    t0 = time.time()
    sid = create_session(title, model, cwd)
    prompt(sid, text)
    wait(sid, timeout=max_wait)
    msgs = messages(sid)
    return {"session": sid, "elapsed": time.time() - t0, "raw": msgs}


if __name__ == "__main__":
    print("models:", len(list_models()))
    for m in list_models():
        print("  ", m)
