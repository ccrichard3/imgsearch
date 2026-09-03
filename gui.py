#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
imgsearch 本地服务（FastAPI）+ 自研前端。

替代原来的 Gradio 界面：
- 完全本地、离线可用：不依赖任何 CDN / 字体服务 / 遥测（Gradio 会联网校验版本与统计）。
- 原生观感：系统字体（SF Pro / PingFang / SF Mono），OKLCH 配色，浅/深色自适应。
- 所有设置集中在一个「设置」抽屉里（模型 / 库文件夹 / 索引 / 端口 / 离线状态）。

启动：
    python gui.py
浏览器打开 http://127.0.0.1:<port>（由启动脚本在端口就绪后自动开）。
"""

from __future__ import annotations

import io
import os
import sys
import threading
from pathlib import Path
from urllib.parse import quote

from PIL import Image

import app as core

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import (FileResponse, HTMLResponse, JSONResponse,
                               PlainTextResponse)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# --------------------------------------------------------------------------- #
# 全局状态
# --------------------------------------------------------------------------- #
# web 目录：普通运行取脚本旁；PyInstaller 打包后取解包目录（sys._MEIPASS）。
if getattr(sys, "frozen", False):
    _BASE = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
else:
    _BASE = Path(__file__).parent
WEB_DIR = _BASE / "web"

CFG = core.load_config()
# 每次启动固定使用默认模型 SigLIP2-B（忽略上次切换保存的模型）
CFG["model"] = core.DEFAULT_MODEL
CFG["pretrained"] = core.DEFAULT_PRETRAINED
core.save_config(CFG)

ENGINE = core.ClipEngine(core.DEFAULT_MODEL, core.DEFAULT_PRETRAINED)
PORT = int(CFG.get("port", core.DEFAULT_PORT))

# 索引状态（后台线程更新；跑完 running=False）
_INDEX = {"running": False, "msg": "尚未索引。", "pct": 0.0}
_INDEX_LOCK = threading.Lock()


def _model_label_for(model_name: str) -> str:
    for label, (mn, _pt) in core.MODEL_CHOICES.items():
        if mn == model_name:
            return label
    return next(iter(core.MODEL_CHOICES))


# --------------------------------------------------------------------------- #
# 后台索引
# --------------------------------------------------------------------------- #
class _Progress:
    """喂给 core.reindex 的进度回调：更新 _INDEX 的百分比与文案。"""

    def __call__(self, frac, desc=None):
        try:
            _INDEX["pct"] = max(0.0, min(1.0, float(frac)))
        except (TypeError, ValueError):
            pass
        if desc:
            _INDEX["msg"] = desc


def _run_index(min_new: int):
    roots = CFG.get("roots", [])
    if not roots:
        _INDEX.update(running=False, pct=1.0,
                      msg="未配置库文件夹：在「设置 → 库文件夹」里添加即可。")
        return
    _INDEX.update(running=True, pct=0.0, msg="正在索引…")
    last = ""
    try:
        for line in core.reindex(ENGINE, roots, progress=_Progress(), min_new=min_new):
            last = line
            _INDEX["msg"] = last
    except Exception as e:  # noqa: BLE001
        _INDEX.update(running=False, msg=f"索引出错：{e}")
        return
    _INDEX.update(running=False, pct=1.0, msg=last or "索引完成。")


def start_index(min_new: int) -> None:
    """启动一次后台索引（若已在跑则忽略）。立即返回，不阻塞端口就绪。"""
    with _INDEX_LOCK:
        if _INDEX["running"]:
            return
        _INDEX["running"] = True   # 抢占标记，避免并发重复启动
    threading.Thread(target=_run_index, args=(min_new,), daemon=True).start()


# --------------------------------------------------------------------------- #
# 路径安全：只允许读取库根目录与缩略图目录下的文件
# --------------------------------------------------------------------------- #
def _allowed_bases() -> list[Path]:
    bases = [core.THUMB_DIR.resolve()]
    for r in CFG.get("roots", []):
        try:
            bases.append(Path(r).resolve())
        except Exception:  # noqa: BLE001
            pass
    return bases


def _is_allowed(path: Path) -> bool:
    try:
        rp = path.resolve()
    except Exception:  # noqa: BLE001
        return False
    for base in _allowed_bases():
        try:
            rp.relative_to(base)
            return True
        except ValueError:
            continue
    return False


# --------------------------------------------------------------------------- #
# 检索结果 -> JSON
# --------------------------------------------------------------------------- #
def _results_payload(results, min_sim: float) -> list[dict]:
    out = []
    for ap, sim in results:
        if sim < float(min_sim):
            continue
        out.append({
            "path": ap,
            "name": Path(ap).name,
            "sim": round(float(sim), 4),
            "thumb": "/thumb?path=" + quote(ap, safe=""),
            "file": "/file?path=" + quote(ap, safe=""),
        })
    return out


# --------------------------------------------------------------------------- #
# FastAPI 应用
# --------------------------------------------------------------------------- #
APP = FastAPI(title="imgsearch")

if WEB_DIR.is_dir():
    APP.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


@APP.get("/", response_class=HTMLResponse)
def index():
    idx = WEB_DIR / "index.html"
    if not idx.is_file():
        return HTMLResponse("<h1>imgsearch</h1><p>缺少 web/index.html</p>", status_code=500)
    return HTMLResponse(idx.read_text(encoding="utf-8"))


@APP.get("/api/state")
def api_state():
    roots = CFG.get("roots", [])
    return {
        "roots": roots,
        "model": {
            "key": ENGINE.key(),
            "label": _model_label_for(ENGINE.key()),
            "choices": list(core.MODEL_CHOICES.keys()),
        },
        "port": PORT,
        "offline": core.OFFLINE,
        "threshold": core.AUTO_INDEX_THRESHOLD,
        "pending": core.pending_summary(ENGINE.key(), roots),
        "index": _INDEX,
        "formats": ("JPG/PNG/TIF/BMP/GIF/WEBP · PSD·PSB · HEIC·HEIF·AVIF · "
                    "JP2/TGA/DDS 等"),
    }


@APP.get("/api/index/status")
def api_index_status():
    return _INDEX


@APP.post("/api/reindex")
def api_reindex():
    if not CFG.get("roots"):
        return JSONResponse({"ok": False, "msg": "请先添加至少一个库文件夹。"}, status_code=400)
    start_index(min_new=0)   # 手动重建：强制全量增量
    return {"ok": True, "index": _INDEX}


class TextQuery(BaseModel):
    query: str
    top_k: int = 24
    min_sim: float = 0.0


@APP.post("/api/search/text")
def api_search_text(q: TextQuery):
    text = (q.query or "").strip()
    if not text:
        return {"ok": False, "msg": "请输入描述文字。", "results": []}
    cache = core.load_cache(ENGINE.key())
    if not cache:
        return {"ok": False, "msg": "当前模型索引为空，请先在设置里添加库文件夹并重建索引。",
                "results": []}
    try:
        vec = ENGINE.encode_text(text)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "msg": f"文本编码失败：{e}", "results": []}
    results = core.search_by_vector(vec, cache, int(q.top_k))
    payload = _results_payload(results, q.min_sim)
    return {"ok": True, "msg": f"共 {len(payload)} 条结果。", "results": payload,
            "total": len(results)}


@APP.post("/api/search/image")
async def api_search_image(file: UploadFile = File(...),
                           top_k: int = Form(24),
                           min_sim: float = Form(0.0)):
    cache = core.load_cache(ENGINE.key())
    if not cache:
        return {"ok": False, "msg": "当前模型索引为空，请先在设置里添加库文件夹并重建索引。",
                "results": []}
    try:
        raw = await file.read()
        img = Image.open(io.BytesIO(raw))
        if img.mode != "RGB":
            img = img.convert("RGB")
        vec = ENGINE.encode_images([img])[0]
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "msg": f"查询图片编码失败：{e}", "results": []}
    results = core.search_by_vector(vec, cache, int(top_k))
    payload = _results_payload(results, min_sim)
    return {"ok": True, "msg": f"共 {len(payload)} 条结果。", "results": payload,
            "total": len(results)}


@APP.get("/thumb")
def api_thumb(path: str):
    p = Path(path)
    if not _is_allowed(p):
        raise HTTPException(status_code=403, detail="path not allowed")
    tp = core.ensure_thumb(str(p), p)
    fp = Path(tp)
    if not fp.is_file():
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(str(fp))


@APP.get("/file")
def api_file(path: str):
    p = Path(path)
    if not _is_allowed(p) or not p.is_file():
        raise HTTPException(status_code=403, detail="path not allowed")
    return FileResponse(str(p))


class PathBody(BaseModel):
    path: str


@APP.post("/api/reveal")
def api_reveal(b: PathBody):
    ok = core.reveal_in_finder(b.path)
    return {"ok": ok, "msg": (f"已在访达中显示：\n{b.path}" if ok
                              else f"文件不存在或无法打开：\n{b.path}")}


@APP.post("/api/open")
def api_open(b: PathBody):
    ok = core.open_with_default_app(b.path)
    return {"ok": ok, "msg": ("已用默认程序打开。" if ok else "文件不存在或无法打开。")}


class RootBody(BaseModel):
    path: str
    action: str = "add"   # add | remove


@APP.post("/api/roots")
def api_roots(b: RootBody):
    roots = CFG.setdefault("roots", [])
    path = (b.path or "").strip()
    if b.action == "remove":
        target = None
        for r in roots:
            if r == path or Path(r).name == path or r.endswith(path):
                target = r
                break
        if target is None:
            return {"ok": False, "msg": "未找到匹配的文件夹（可粘贴完整路径）。", "roots": roots}
        roots.remove(target)
        core.save_config(CFG)
        start_index(min_new=0)   # 清理该文件夹已索引的向量
        return {"ok": True, "msg": f"已移除：{target}", "roots": roots}

    # add
    p = Path(path).expanduser()
    note = ""
    if p.is_file():
        note = "（拖入的是文件，已取其所在目录）"
        p = p.parent
    if not p.is_dir():
        return {"ok": False, "msg": f"路径不存在或不是文件夹：{p}", "roots": roots}
    ap = str(p.resolve())
    if ap in roots:
        return {"ok": False, "msg": f"该文件夹已在列表中：{ap}", "roots": roots}
    roots.append(ap)
    core.save_config(CFG)
    start_index(min_new=0)   # 新增文件夹是明确动作，强制索引
    return {"ok": True, "msg": f"已添加：{ap}{note}\n已开始后台索引。", "roots": roots}


class ModelBody(BaseModel):
    label: str


@APP.post("/api/model", response_model=None)
def api_model(b: ModelBody):
    mn, pt = core.MODEL_CHOICES.get(b.label, (core.DEFAULT_MODEL, core.DEFAULT_PRETRAINED))
    ENGINE.switch(mn, pt)
    CFG["model"] = mn
    CFG["pretrained"] = pt
    core.save_config(CFG)
    start_index(min_new=0)   # 切换模型：为该模型强制补索引
    return {"ok": True, "msg": f"已切换到 {b.label}，正在后台为该模型更新索引。",
            "model": {"key": ENGINE.key(), "label": _model_label_for(ENGINE.key())}}


@APP.get("/api/model/paths")
def api_model_paths():
    """当前模型在本机的存放位置（自动适配 Mac/Windows/NAS）。"""
    return core.model_storage_info(ENGINE.key(), ENGINE.pretrained)


@APP.post("/api/model/reveal")
def api_model_reveal():
    """在文件管理器中打开模型存放目录；当前目录不存在则创建推荐的手动目录。"""
    info = core.model_storage_info(ENGINE.key(), ENGINE.pretrained)
    target = info["active"] or info["manual_dir"]
    try:
        Path(target).mkdir(parents=True, exist_ok=True)
    except Exception:  # noqa: BLE001
        pass
    ok = core.open_with_default_app(target)
    return {"ok": ok, "path": target,
            "msg": (f"已打开：{target}" if ok
                    else f"无法打开（该系统可能无桌面环境）。路径：\n{target}")}


class PortBody(BaseModel):
    port: int


@APP.post("/api/port")
def api_port(b: PortBody):
    p = int(b.port)
    if not (1024 <= p <= 65535):
        return {"ok": False, "msg": f"端口需在 1024–65535 之间，当前仍为 {PORT}。"}
    CFG["port"] = p
    core.save_config(CFG)
    if p == PORT:
        return {"ok": True, "msg": f"端口已设为 {p}（与当前一致，无需重启）。"}
    return {"ok": True, "msg": f"端口已保存为 {p}。下次启动生效（本次仍运行在 {PORT}）。"}


@APP.post("/api/quit", response_class=PlainTextResponse)
def api_quit():
    def _kill():
        import time
        time.sleep(0.5)
        os._exit(0)
    threading.Thread(target=_kill, daemon=True).start()
    return "quitting"


# --------------------------------------------------------------------------- #
# 入口
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    import uvicorn

    # 启动即在后台线程做一次「带阈值」的索引：变动少于阈值不会加载模型 → 秒启动。
    start_index(min_new=core.AUTO_INDEX_THRESHOLD)
    print(f"imgsearch 启动中… http://127.0.0.1:{PORT}  (offline={core.OFFLINE})", flush=True)
    uvicorn.run(APP, host="127.0.0.1", port=PORT, log_level="warning")
