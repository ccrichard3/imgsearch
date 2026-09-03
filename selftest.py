#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""imgsearch 自测：在「强制离线」下走完整链路（含离线加载 SigLIP2 tokenizer）。
用法： HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 ./.venv/bin/python selftest.py
"""
import io
import os
import time

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import app
import gui
from starlette.testclient import TestClient


def line(t):
    print("\n=== " + t + " ===")


line("import / env")
print("app.OFFLINE =", app.OFFLINE, "| threshold =", app.AUTO_INDEX_THRESHOLD)

roots = app.load_config().get("roots", [])
t = time.time()
pend = app.pending_summary(app.DEFAULT_MODEL, roots)
print("pending_summary =", pend, "in", round(time.time() - t, 2), "s (must be <1s, no model)")

client = TestClient(gui.APP)

line("static + index html")
for path in ["/", "/static/app.css", "/static/app.js", "/static/tokens.css"]:
    r = client.get(path)
    print(f"{path:22} -> {r.status_code} {r.headers.get('content-type','')[:30]}")

line("/api/state")
st = client.get("/api/state").json()
print("model:", st["model"]["label"], "| offline:", st["offline"],
      "| roots:", len(st["roots"]), "| pending.todo:", st["pending"]["todo"])

line("TEXT SEARCH — offline model + tokenizer load (the critical test)")
t = time.time()
r = client.post("/api/search/text",
                json={"query": "红色的汽车 a red car", "top_k": 6, "min_sim": 0.0}).json()
print("ok =", r["ok"], "| results =", len(r.get("results", [])),
      "| loaded in", round(time.time() - t, 1), "s")
print("msg:", r["msg"][:80])
top = None
if r.get("results"):
    top = r["results"][0]
    print("top hit:", top["sim"], top["name"])
    tr = client.get(top["thumb"])
    print("thumb   ->", tr.status_code, tr.headers.get("content-type"))
    fr = client.get(top["file"])
    print("file    ->", fr.status_code, fr.headers.get("content-type"))

line("IMAGE SEARCH — encode a real library image and search")
cache = app.load_cache(app.DEFAULT_MODEL)
jpg = next((k for k in cache
            if k.lower().endswith((".jpg", ".jpeg", ".png")) and os.path.exists(k)), None)
if jpg:
    with open(jpg, "rb") as f:
        data = f.read()
    r = client.post("/api/search/image",
                    files={"file": ("q.jpg", data, "image/jpeg")},
                    data={"top_k": "5", "min_sim": "0"}).json()
    print("ok =", r["ok"], "| results =", len(r.get("results", [])),
          "| self-match sim =", (r["results"][0]["sim"] if r.get("results") else "n/a"))
else:
    print("(no jpg/png in cache to test image search)")

line("PATH SAFETY — disallowed path must be 403")
print("/file /etc/passwd  ->", client.get("/file", params={"path": "/etc/passwd"}).status_code)
print("/thumb /etc/hosts  ->", client.get("/thumb", params={"path": "/etc/hosts"}).status_code)

line("REINDEX (min_new=0, already-indexed → should finish fast without re-encoding)")
r = client.post("/api/reindex").json()
print("reindex kick:", r.get("ok"), "| running:", r.get("index", {}).get("running"))
for _ in range(20):
    stt = client.get("/api/index/status").json()
    if not stt["running"]:
        break
    time.sleep(0.5)
print("final index msg:", client.get("/api/index/status").json()["msg"][:90])

print("\nALL TESTS DONE")
