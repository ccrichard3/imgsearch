#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
imgsearch —— 本地「以图搜图」工具（Apple Silicon 原生，无需 Docker）

特性
- 向量检索：以图搜图 + 文字搜图（CLIP / SigLIP2 模型，MPS 加速）
- 可切换模型：默认 SigLIP2（检索强、原生多语言），可切到旗舰或轻量档
- 支持图片：JPG/JPEG/PNG/TIF/TIFF/BMP/GIF/WEBP/PSD/PSB/HEIC/HEIF/AVIF/ICO/PPM/PGM/PBM/PNM/TGA/DDS/JP2
- 增量索引：按 路径+mtime+size 记录，只处理新增/改动，自动剔除已删除
- 每个模型独立索引：换模型不会互相覆盖，换回来无需重建
- 多库根目录，网页 GUI，全程本地，图片不外传

数据存放在 ~/.imgsearch/：
  config.json          库根目录列表 + 当前模型
  cache__<model>.pkl   每个模型一份索引
  thumbs/              缩略图缓存
"""

from __future__ import annotations

import hashlib
import json
import os
import pickle
import re
import socket
import subprocess
import sys
import threading
from pathlib import Path

import numpy as np
from PIL import Image, ImageFile

# 大图/损坏图容错
Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True


# --------------------------------------------------------------------------- #
# 离线/无网可用（关键）
#   - 权重与 tokenizer 首次需联网下载，之后应完全离线可用。
#   - transformers 5.x 在离线时无法用「仓库名」解析 SigLIP2 的 tokenizer
#     （模型 config.json 的 404 不会命中本地负缓存），必须改用本地快照目录加载。
#   - 无网时强制 HF 离线模式：缓存秒开，绝不卡在网络超时上。
# --------------------------------------------------------------------------- #
def _has_network(host: str = "huggingface.co", port: int = 443,
                 timeout: float = 1.5) -> bool:
    """快速探测能否连到 HuggingFace（用于决定是否进入离线模式）。"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


# 默认模型的 HF 仓库；用于「缓存优先」的离线判断（见 setup_ml_env）。
DEFAULT_HF_REPO = "timm/ViT-B-16-SigLIP2-256"


def _hf_cache_root() -> Path:
    """HF Hub 缓存根目录（尊重 HF_HUB_CACHE / HUGGINGFACE_HUB_CACHE / HF_HOME）。"""
    v = os.environ.get("HF_HUB_CACHE") or os.environ.get("HUGGINGFACE_HUB_CACHE")
    if v:
        return Path(v)
    home = os.environ.get("HF_HOME")
    if home:
        return Path(home) / "hub"
    return Path.home() / ".cache" / "huggingface" / "hub"


def _weights_cached_for_repo(repo_id: str) -> bool:
    """本地 HF 缓存里是否已存在该仓库的 open_clip 权重（safetensors 或 bin）。
    纯文件系统判断：不触网、不导入 torch/hf，很快，可在启动早期调用。"""
    snaps = _hf_cache_root() / f"models--{repo_id.replace('/', '--')}" / "snapshots"
    if not snaps.is_dir():
        return False
    try:
        snap_dirs = list(snaps.iterdir())
    except OSError:
        return False
    for snap in snap_dirs:
        for name in ("open_clip_model.safetensors", "open_clip_pytorch_model.bin"):
            f = snap / name
            try:
                if f.exists() and f.stat().st_size > 1_000_000:  # 排除半截/空文件
                    return True
            except OSError:
                pass
    return False


def setup_ml_env() -> bool:
    """在导入 torch/transformers 之前设置环境变量。返回「界面显示用」的离线判断。

    离线策略改为「按模型」在加载时决定（见 _apply_hf_offline / ClipEngine.ensure_loaded），
    而不是全局一刀切：
      · 本地已缓存该模型权重 → 离线加载（本地秒开、免疫 HF 的 503/限流、绝不重下）；
      · 未缓存（例如切到新模型）→ 允许联网下载一次，下完即缓存，此后同样离线。
    这里只做幂等的环境默认值设置，并返回一个用于状态徽标的粗略判断。"""
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "False")  # 残留无害
    if _USER_FORCED_OFFLINE:
        return True
    # 默认模型已缓存 → 本地秒开、根本不做网络探测（尊重「本地有就别每次检测」）。
    if _weights_cached_for_repo(DEFAULT_HF_REPO):
        return True
    # 未缓存才探测网络：有网则联网下载，无网则离线（快速失败不卡超时）。
    return not _has_network()


def _hf_repo_for_model(model_name: str, pretrained: str) -> str | None:
    """解析某模型权重所在的 HF 仓库名（形如 'timm/ViT-B-16-SigLIP2-256'）。
    读 open_clip 的预训练配置里的 hf_hub 字段；解析不到返回 None。"""
    try:
        from open_clip.pretrained import get_pretrained_cfg
        cfg = get_pretrained_cfg(model_name, pretrained) or {}
        hf = cfg.get("hf_hub") or ""
        parts = hf.strip("/").split("/")
        if len(parts) >= 2:
            return parts[0] + "/" + parts[1]
    except Exception:
        pass
    return None


def _model_weights_cached(model_name: str, pretrained: str) -> bool:
    """该模型的权重是否已在本地 HF 缓存。"""
    repo = _hf_repo_for_model(model_name, pretrained)
    return bool(repo) and _weights_cached_for_repo(repo)


def _apply_hf_offline(flag: bool) -> None:
    """运行时切换 HF/transformers 的离线开关（本版本 huggingface_hub 在每次请求时
    读 constants.HF_HUB_OFFLINE，故运行时修改即时生效）。用户显式离线时恒为离线。"""
    flag = flag or _USER_FORCED_OFFLINE
    val = "1" if flag else "0"
    os.environ["HF_HUB_OFFLINE"] = val
    os.environ["TRANSFORMERS_OFFLINE"] = val
    try:
        import huggingface_hub.constants as _c
        _c.HF_HUB_OFFLINE = flag
    except Exception:
        pass
    try:
        import transformers.utils.hub as _h
        _h._is_offline_mode = flag
    except Exception:
        pass


# 用户是否在启动前就显式要求离线（HF_HUB_OFFLINE=1）；若是则全程离线，绝不联网。
_USER_FORCED_OFFLINE = os.environ.get("HF_HUB_OFFLINE") == "1"

OFFLINE = setup_ml_env()


def _resolve_local_hf_dir(repo_id: str) -> str | None:
    """把 HF 仓库名解析到本地已缓存的快照目录（含 tokenizer 文件）；未缓存返回 None。
    用于绕开 transformers 离线「用仓库名」解析的 bug（改从本地目录直接加载）。

    先用文件系统直接扫 HF 缓存快照（最可靠，不依赖 hf_hub 的缓存 API），
    再回退到 try_to_load_from_cache。"""
    # 1) 直接扫 HF 缓存的 snapshots 目录，找同时含 tokenizer_config.json + tokenizer.json 的快照
    snaps = _hf_cache_root() / f"models--{repo_id.replace('/', '--')}" / "snapshots"
    try:
        if snaps.is_dir():
            for snap in sorted(snaps.iterdir()):
                if (snap / "tokenizer_config.json").exists() and (snap / "tokenizer.json").exists():
                    return str(snap)
    except OSError:
        pass
    # 2) 回退：huggingface_hub 缓存 API
    try:
        from huggingface_hub import try_to_load_from_cache
        for fn in ("tokenizer_config.json", "tokenizer.json"):
            try:
                p = try_to_load_from_cache(repo_id, fn)
            except Exception:
                p = None
            if isinstance(p, str) and os.path.exists(p):
                return str(Path(p).parent)
    except Exception:
        pass
    return None

# HEIC/HEIF/AVIF 支持（pillow-heif 注册后 PIL 可直接 open）
try:
    import pillow_heif  # noqa

    pillow_heif.register_heif_opener()
    try:
        pillow_heif.register_avif_opener()
    except Exception:
        pass
except Exception:
    pass

# --------------------------------------------------------------------------- #
# 常量与路径
# --------------------------------------------------------------------------- #
APP_DIR = Path(os.getenv("IMGSEARCH_HOME", str(Path.home() / ".imgsearch")))
CONFIG_PATH = APP_DIR / "config.json"

DEFAULT_PORT = 57860
FAILED_PATH = APP_DIR / "failed.json"   # 记住读取/编码失败的文件，避免每次启动反复重试
THUMB_DIR = APP_DIR / "thumbs"

# 图片格式：Pillow 原生 + psd-tools(PSD/PSB) + pillow-heif(HEIC/HEIF/AVIF)
IMAGE_EXT = {
    ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif", ".webp",
    ".psd", ".psb", ".heic", ".heif", ".avif", ".ico", ".ppm", ".pgm",
    ".pbm", ".pnm", ".tga", ".dds", ".jp2", ".j2k", ".jpf", ".jpx",
}
SUPPORTED_EXT = IMAGE_EXT

# 可选模型（中文档位说明 -> (open_clip 模型名, 预训练权重)）
MODEL_CHOICES = {
    "SigLIP2-B (较快·占用小)": ("ViT-B-16-SigLIP2-256", "webli"),
    "SigLIP2-L (精度/速度均衡)": ("ViT-L-16-SigLIP2-384", "webli"),
    "SigLIP2-SO400M (最强·较慢较大)": ("ViT-SO400M-16-SigLIP2-384", "webli"),
    "CLIP ViT-L-14 (经典·英文强)": ("ViT-L-14", "dfn2b"),
    "CLIP ViT-B-32 (最快·最轻)": ("ViT-B-32", "laion2b_s34b_b79k"),
}
DEFAULT_MODEL = "ViT-B-16-SigLIP2-256"
DEFAULT_PRETRAINED = "webli"

THUMB_MAX = 512   # 缩略图最长边

# 启动时的自动索引阈值：新增/改动的图片数 ≥ 此值才在启动时自动编码（会加载模型、较慢）；
# 低于此值则跳过（仅清理已删除项），把「秒启动」还给用户，随时可手动『重建索引』补上。
AUTO_INDEX_THRESHOLD = 100

APP_DIR.mkdir(parents=True, exist_ok=True)
THUMB_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
# 配置读写
# --------------------------------------------------------------------------- #
def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            cfg = json.loads(CONFIG_PATH.read_text())
            cfg.setdefault("roots", [])
            cfg.setdefault("model", DEFAULT_MODEL)
            cfg.setdefault("pretrained", DEFAULT_PRETRAINED)
            cfg.setdefault("port", DEFAULT_PORT)
            return cfg
        except Exception:
            pass
    return {"roots": [], "model": DEFAULT_MODEL, "pretrained": DEFAULT_PRETRAINED,
            "port": DEFAULT_PORT}


def save_config(cfg: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))


# --------------------------------------------------------------------------- #
# 失败文件记忆：{ abspath: {"mtime": float, "size": int} }
# 读取/编码失败的文件记在这里，只要文件没变动就不再反复重试（否则每次启动都会
# 因这些坏图进入待处理队列而触发一次模型加载，拖慢启动）。
# --------------------------------------------------------------------------- #
def load_failed() -> dict:
    if FAILED_PATH.exists():
        try:
            data = json.loads(FAILED_PATH.read_text())
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}


def save_failed(failed: dict) -> None:
    try:
        FAILED_PATH.write_text(json.dumps(failed, ensure_ascii=False, indent=2))
    except Exception:
        pass


# --------------------------------------------------------------------------- #
# 每个模型独立的缓存文件
# 结构：{ abspath: {"path": str, "mtime": float, "size": int, "emb": np.float32[D]} }
# --------------------------------------------------------------------------- #
def _safe_model_tag(model_name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", model_name)


def cache_path_for_model(model_name: str) -> Path:
    return APP_DIR / f"cache__{_safe_model_tag(model_name)}.pkl"


def load_cache(model_name: str) -> dict:
    cp = cache_path_for_model(model_name)
    if cp.exists():
        try:
            with open(cp, "rb") as f:
                return pickle.load(f)
        except Exception:
            pass
    return {}


def save_cache(model_name: str, cache: dict) -> None:
    cp = cache_path_for_model(model_name)
    tmp = cp.with_suffix(".pkl.tmp")
    with open(tmp, "wb") as f:
        pickle.dump(cache, f, protocol=pickle.HIGHEST_PROTOCOL)
    tmp.replace(cp)


# --------------------------------------------------------------------------- #
# 手动模型目录（免联网 / 迁移用）
# 把模型文件手动放到 <models_root>/<模型名>/，即可完全本地加载，无需 HF 缓存那套
# blob/软链结构。查找顺序：$IMGSEARCH_MODELS > ~/.imgsearch/models > 代码旁 models/。
# 一个模型目录应含：
#   open_clip_model.safetensors      （权重，必需）
#   tokenizer.json / tokenizer_config.json / special_tokens_map.json （文字搜图需要）
# 例：~/.imgsearch/models/ViT-B-16-SigLIP2-256/open_clip_model.safetensors
# --------------------------------------------------------------------------- #
def _manual_model_roots() -> list[Path]:
    roots: list[Path] = []
    env = os.environ.get("IMGSEARCH_MODELS")
    if env:
        roots.append(Path(env).expanduser())
    roots.append(APP_DIR / "models")
    roots.append(Path(__file__).resolve().parent / "models")
    return roots


def _manual_model_dir(model_name: str) -> str | None:
    for root in _manual_model_roots():
        d = root / model_name
        try:
            if d.is_dir():
                return str(d)
        except OSError:
            pass
    return None


def _manual_weights_file(model_name: str) -> str | None:
    """手动模型目录里的权重文件路径（优先 safetensors）；没有返回 None。"""
    d = _manual_model_dir(model_name)
    if not d:
        return None
    for name in ("open_clip_model.safetensors", "open_clip_pytorch_model.bin"):
        f = Path(d) / name
        try:
            if f.exists() and f.stat().st_size > 1_000_000:
                return str(f)
        except OSError:
            pass
    return None


def _manual_tokenizer_dir(model_name: str) -> str | None:
    """手动模型目录若含 tokenizer 文件，返回该目录；否则 None。"""
    d = _manual_model_dir(model_name)
    if d and (Path(d) / "tokenizer_config.json").exists() and (Path(d) / "tokenizer.json").exists():
        return d
    return None


def _model_local_available(model_name: str, pretrained: str) -> bool:
    """该模型能否完全本地加载（手动目录有权重 或 HF 缓存已有）。"""
    return (_manual_weights_file(model_name) is not None
            or _model_weights_cached(model_name, pretrained))


def _os_label() -> str:
    if sys.platform == "darwin":
        return "macOS"
    if sys.platform.startswith("win"):
        return "Windows"
    return "Linux / NAS"


def model_storage_info(model_name: str, pretrained: str) -> dict:
    """当前系统下该模型的实际/推荐存放位置（供界面显示，自动适配 Mac/Win/NAS）。"""
    repo = _hf_repo_for_model(model_name, pretrained)
    manual_primary = str(APP_DIR / "models" / model_name)   # 推荐手动目录
    manual_roots = [str(r / model_name) for r in _manual_model_roots()]
    hf_cache = str(_hf_cache_root())
    hf_repo_dir = (str(_hf_cache_root() / f"models--{repo.replace('/', '--')}")
                   if repo else None)

    wf = _manual_weights_file(model_name)
    if wf:
        active, kind = str(Path(wf).parent), "manual"
    elif repo and _weights_cached_for_repo(repo):
        active, kind = hf_repo_dir, "hf-cache"
    else:
        active, kind = None, "absent"
    return {
        "os": _os_label(),
        "model_name": model_name,
        "repo": repo,
        "active": active,
        "active_kind": kind,          # manual | hf-cache | absent
        "manual_dir": manual_primary,
        "manual_roots": manual_roots,
        "hf_cache": hf_cache,
    }


# --------------------------------------------------------------------------- #
# 向量模型（延迟加载，支持 CLIP / SigLIP2）
# --------------------------------------------------------------------------- #
class ClipEngine:
    def __init__(self, model_name: str, pretrained: str):
        self.model_name = model_name
        self.pretrained = pretrained
        self.model = None
        self.preprocess = None
        self.tokenizer = None
        self.device = None
        self._lock = threading.RLock()   # 后台索引与前台搜索可能并发触发加载

    def key(self) -> str:
        return self.model_name

    def switch(self, model_name: str, pretrained: str):
        """切换模型：清空已加载的权重，下次用时按新模型加载。"""
        with self._lock:
            if model_name == self.model_name and pretrained == self.pretrained:
                return
            self.model_name = model_name
            self.pretrained = pretrained
            self.model = None
            self.preprocess = None
            self.tokenizer = None

    def ensure_loaded(self):
        if self.model is not None:
            return
        with self._lock:
            if self.model is not None:   # 双检锁：可能已被另一线程加载
                return
            import torch
            import open_clip

            if torch.backends.mps.is_available():
                self.device = "mps"
            elif torch.cuda.is_available():
                self.device = "cuda"
            else:
                self.device = "cpu"

            # 加载来源优先级：
            #   1) 手动模型目录里的权重文件（免联网、迁移友好）
            #   2) HF 缓存里的该模型（缓存优先离线，免疫 503）
            #   3) 都没有 → 联网下载一次（下完即缓存）
            wf = _manual_weights_file(self.model_name)
            local_ok = wf is not None or _model_weights_cached(self.model_name, self.pretrained)
            _apply_hf_offline(local_ok)
            pretrained_src = wf or self.pretrained

            model, _, preprocess = open_clip.create_model_and_transforms(
                self.model_name, pretrained=pretrained_src
            )
            self.model = model.eval().to(self.device)
            self.preprocess = preprocess
            # tokenizer 独立、按需加载（见 ensure_tokenizer）。
            # 以图搜图不需要 tokenizer；绝不能让 tokenizer 加载失败拖累图片编码。
            # （历史 bug：首图报「编码失败」、次图却成功——正是因为 tokenizer 在
            #   ensure_loaded 尾部抛错，而 self.model 已赋值，二次调用直接跳过。）

    def ensure_tokenizer(self):
        """按需加载 tokenizer（仅文字搜图需要）。与模型加载解耦，失败不影响以图搜图。"""
        if self.tokenizer is not None:
            return
        with self._lock:
            if self.tokenizer is not None:
                return
            # 文本编码可能先于任何图片编码触发，这里再保证一次离线开关正确
            _apply_hf_offline(_model_local_available(self.model_name, self.pretrained))
            self.tokenizer = self._load_tokenizer()

    def _load_tokenizer(self):
        """加载 tokenizer。SigLIP2 等 HF tokenizer 从本地缓存目录**强制离线**加载
        （transformers 5.x 离线用「仓库名」解析会挂，必须给本地目录 + local_files_only）。"""
        import open_clip
        from open_clip import factory
        # 注意：本版本 open_clip 未在顶层导出 HFTokenizer，需从子模块取。
        try:
            from open_clip.tokenizer import HFTokenizer
        except Exception:  # noqa: BLE001
            HFTokenizer = getattr(open_clip, "HFTokenizer", None)
        cfg = factory.get_model_config(self.model_name) or {}
        tcfg = (cfg.get("text_cfg") or {})
        hf_name = tcfg.get("hf_tokenizer_name")
        ctx = tcfg.get("context_length", 64)
        tkw = dict(tcfg.get("tokenizer_kwargs", {}))
        if hf_name and HFTokenizer is not None:
            # 优先手动模型目录，其次 HF 缓存快照
            local = _manual_tokenizer_dir(self.model_name) or _resolve_local_hf_dir(hf_name)
            if local:
                # 从本地快照目录加载：强制离线，绝不触网。
                last = None
                for extra in ({"local_files_only": True, "use_fast": True},
                              {"local_files_only": True},
                              {}):
                    try:
                        return HFTokenizer(local, context_length=ctx, **tkw, **extra)
                    except Exception as e:  # noqa: BLE001
                        last = e
                raise RuntimeError(
                    f"本地 tokenizer 加载失败（{local}）：{last}")
        # 无 hf tokenizer 名（纯 CLIP BPE）或未缓存：走默认（未缓存+有网时会联网下载一次）。
        return open_clip.get_tokenizer(self.model_name)

    def encode_images(self, pil_images: list) -> np.ndarray:
        """批量编码 PIL 图像 -> L2 归一化向量矩阵 (N, D)。"""
        import torch

        self.ensure_loaded()
        tensors = torch.stack([self.preprocess(im) for im in pil_images]).to(self.device)
        with torch.no_grad():
            feats = self.model.encode_image(tensors)
            feats = feats / feats.norm(dim=-1, keepdim=True)
        return feats.float().cpu().numpy()

    def encode_text(self, text: str) -> np.ndarray:
        import torch

        self.ensure_loaded()
        self.ensure_tokenizer()
        tokens = self.tokenizer([text]).to(self.device)
        with torch.no_grad():
            feats = self.model.encode_text(tokens)
            feats = feats / feats.norm(dim=-1, keepdim=True)
        return feats.float().cpu().numpy()[0]


# --------------------------------------------------------------------------- #
# 图片加载 + 缩略图
# --------------------------------------------------------------------------- #
def load_rgb_image(path: Path) -> Image.Image:
    """把任意支持的图片格式读成 RGB PIL 图像。PSD/PSB 走 psd-tools 合成。"""
    ext = path.suffix.lower()
    if ext in (".psd", ".psb"):
        from psd_tools import PSDImage

        psd = PSDImage.open(path)
        img = psd.composite()
        if img is None:
            raise ValueError("PSD composite 返回空")
    else:
        img = Image.open(path)
        img.load()
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def thumb_path_for(abspath: str) -> Path:
    h = hashlib.sha1(abspath.encode("utf-8")).hexdigest()
    return THUMB_DIR / f"{h}.jpg"


def save_thumb(abspath: str, pil_img: Image.Image) -> str:
    tp = thumb_path_for(abspath)
    try:
        img = pil_img.copy()
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.thumbnail((THUMB_MAX, THUMB_MAX))
        img.save(tp, "JPEG", quality=85)
        return str(tp)
    except Exception:
        return ""


def ensure_thumb(abspath: str, path: Path, pil_img: Image.Image | None = None) -> str:
    """返回缩略图路径（供浏览器显示）。已存在则复用。"""
    tp = thumb_path_for(abspath)
    if tp.exists():
        return str(tp)
    try:
        if pil_img is None:
            pil_img = load_rgb_image(path)
        r = save_thumb(abspath, pil_img)
        if r:
            return r
    except Exception:
        pass
    return str(path)


# --------------------------------------------------------------------------- #
# 扫描 + 增量索引
# --------------------------------------------------------------------------- #
def scan_files(roots: list[str]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        rp = Path(root).expanduser()
        if not rp.exists():
            continue
        for p in rp.rglob("*"):
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXT:
                if any(part.startswith(".") for part in p.parts):
                    continue
                files.append(p)
    return files


def compute_todo(model_name: str, roots: list[str]):
    """仅用 路径+mtime+size 做一次「便宜」扫描：算出需要（重新）编码的文件、
    以及已删除的条目。**不加载模型**，因此很快，可用于启动时决定是否值得自动索引。
    返回 (current, todo, removed, cache, failed)。"""
    cache = load_cache(model_name)
    current = scan_files(roots)
    current_set = {str(p) for p in current}
    removed = [k for k in list(cache.keys()) if k not in current_set]

    failed = load_failed()
    todo: list[Path] = []
    for p in current:
        ap = str(p)
        try:
            st = p.stat()
        except OSError:
            continue
        old = cache.get(ap)
        if (old and isinstance(old, dict)
                and old.get("mtime") is not None
                and abs(old["mtime"] - st.st_mtime) < 1e-6
                and old.get("size") == st.st_size):
            continue
        bad = failed.get(ap)
        if (bad and abs(bad.get("mtime", -1) - st.st_mtime) < 1e-6
                and bad.get("size") == st.st_size):
            continue   # 上次就失败、文件没变，跳过，避免每次启动都触发模型加载
        todo.append(p)
    return current, todo, removed, cache, failed


def pending_summary(model_name: str, roots: list[str]) -> dict:
    """给界面用的待办摘要（不加载模型）。"""
    current, todo, removed, cache, _ = compute_todo(model_name, roots)
    return {
        "indexed": len(cache),
        "total_files": len(current),
        "todo": len(todo),
        "removed": len(removed),
    }


def reindex(engine: ClipEngine, roots: list[str], batch_size: int = 16,
            progress=None, min_new: int = 0):
    """增量重建当前模型的索引。yield 进度字符串。

    min_new：当「新增/改动」数量 < min_new 时，跳过重编码（只清理已删除项、秒回）。
    启动时传 min_new=AUTO_INDEX_THRESHOLD 避免为几张图就加载模型；手动『重建索引』传 0（强制）。
    """
    model_name = engine.key()
    current, todo, removed, cache, failed = compute_todo(model_name, roots)

    # 删除已不存在的条目（很便宜，无需模型，任何情况下都做）
    for k in removed:
        cache.pop(k, None)

    total = len(todo)

    # 低于阈值：跳过重编码，但把删除清理落盘，保证搜索结果不含已删文件。
    if total < min_new:
        if removed:
            save_cache(model_name, cache)
        msg = (f"扫描到 {len(current)} 张；已清理 {len(removed)} 条已删除；"
               f"待索引 {total} 张（少于阈值 {min_new}，已跳过自动编码以加快启动）。"
               f"需要时到「库 / 索引」手动『重建索引』即可补上。")
        if progress is not None:
            progress(1.0, desc=msg)
        yield msg
        return

    msg = f"扫描到 {len(current)} 张图片；已删除 {len(removed)} 条；需处理 {total} 个新增/改动。"
    if progress is not None:
        progress(0.0, desc=msg)
    yield msg

    done = 0
    failed_n = 0
    batch: list[tuple[Path, Image.Image]] = []

    def mark_failed(p: Path):
        """把读取/编码失败的文件记进 failed（含 mtime+size），下次启动不再重试。"""
        try:
            st = p.stat()
            failed[str(p)] = {"mtime": st.st_mtime, "size": st.st_size}
        except OSError:
            pass

    def flush(force: bool = False):
        """按 batch_size 分块编码；force=False 时保留不足一块的尾巴。"""
        nonlocal done, failed_n
        while len(batch) >= batch_size or (force and batch):
            chunk = batch[:batch_size]
            del batch[:batch_size]
            imgs = [b[1] for b in chunk]
            try:
                embs = engine.encode_images(imgs)
            except Exception:
                failed_n += len(chunk)
                for (p, _img) in chunk:
                    mark_failed(p)
                continue
            for (p, img), emb in zip(chunk, embs):
                try:
                    st = p.stat()
                except OSError:
                    continue
                cache[str(p)] = {
                    "path": str(p),
                    "mtime": st.st_mtime,
                    "size": st.st_size,
                    "emb": emb.astype(np.float32),
                }
                failed.pop(str(p), None)   # 之前失败、这次成功 → 移出失败名单
                save_thumb(str(p), img)
            done += len(chunk)

    for i, p in enumerate(todo):
        try:
            img = load_rgb_image(p)
            batch.append((p, img))
        except Exception:
            failed_n += 1
            mark_failed(p)
        flush(force=False)

        if (i + 1) % 32 == 0:
            save_cache(model_name, cache)
            frac = (i + 1) / max(1, total)
            line = f"已处理 {i + 1}/{total}（成功编码 {done}，失败 {failed_n}）…"
            if progress is not None:
                progress(frac, desc=line)
            yield line

    flush(force=True)
    save_cache(model_name, cache)
    save_failed(failed)
    final = (f"索引完成：当前模型 [{model_name}] 库中共 {len(cache)} 张图"
             f"（本次新增/更新 {done}，失败 {failed_n}，删除 {len(removed)}）。")
    if progress is not None:
        progress(1.0, desc=final)
    yield final


# --------------------------------------------------------------------------- #
# 检索
# --------------------------------------------------------------------------- #
def build_matrix(cache: dict, dim: int | None = None):
    """把缓存里的向量堆成矩阵。dim 给定时只保留该维度的条目，
    自动跳过维度不一致的脏数据（历史上后台线程切模型可能写入过混维向量）。"""
    keys: list[str] = []
    vecs: list[np.ndarray] = []
    for k, v in cache.items():
        emb = v.get("emb") if isinstance(v, dict) else None
        if emb is None:
            continue
        emb = np.asarray(emb, dtype=np.float32).ravel()
        if dim is not None and emb.shape[0] != dim:
            continue
        keys.append(k)
        vecs.append(emb)
    if not vecs:
        return keys, None
    return keys, np.stack(vecs).astype(np.float32)


def search_by_vector(query_vec: np.ndarray, cache: dict, top_k: int):
    """返回 [(abspath, sim)]。只匹配与查询向量同维度的条目。"""
    query_vec = np.asarray(query_vec, dtype=np.float32).ravel()
    keys, mat = build_matrix(cache, dim=query_vec.shape[0])
    if mat is None:
        return []
    sims = mat @ query_vec  # 已归一化 -> 余弦相似度
    k = min(top_k, len(keys))
    idx = np.argpartition(-sims, k - 1)[:k]
    idx = idx[np.argsort(-sims[idx])]
    return [(keys[i], float(sims[i])) for i in idx]


# --------------------------------------------------------------------------- #
# 在 Finder 中定位文件（macOS）
# --------------------------------------------------------------------------- #
def reveal_in_finder(path: str) -> bool:
    """在访达/文件管理器中显示并选中该文件（macOS / Windows / Linux）。"""
    p = Path(path)
    if not p.exists():
        return False
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", "-R", str(p)], check=False)
        elif sys.platform.startswith("win"):
            # explorer /select 常返回非零退出码，属正常
            subprocess.run(["explorer", f"/select,{p}"], check=False)
        else:
            subprocess.run(["xdg-open", str(p.parent)], check=False)
        return True
    except Exception:
        return False


def open_with_default_app(path: str) -> bool:
    """用系统默认程序打开文件或文件夹（macOS: open；Windows: startfile；Linux: xdg-open）。"""
    p = Path(path)
    if not p.exists():
        return False
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", str(p)], check=False)
        elif sys.platform.startswith("win"):
            os.startfile(str(p))  # type: ignore[attr-defined]  # Windows-only
        else:
            subprocess.run(["xdg-open", str(p)], check=False)
        return True
    except Exception:
        return False
