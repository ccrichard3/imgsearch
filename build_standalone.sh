#!/bin/bash
# 把 imgsearch 打包成「免 Python 环境」的独立程序（PyInstaller，onedir）。
#
# 重要：只能在与目标机【相同 OS + 相同 CPU 架构】上打包。
#   · Apple Silicon Mac 打的包 → 只能给 Apple Silicon Mac
#   · Intel Mac / Windows / Linux 各自在对应机器上打
#
# 产出：dist/imgsearch/  —— 整个目录拷到目标机，运行里面的 ./imgsearch 即启动服务。
# 模型权重（~/.cache/huggingface）建议一并拷到目标机，或首次联网自动下载一次。
set -euo pipefail
cd "$(dirname "$0")"

PY=./.venv/bin/python
[ -x "$PY" ] || { echo "!! 未找到 .venv，请先双击 run.command 建好环境再打包"; exit 1; }

echo "==> 安装 pyinstaller"
"$PY" -m pip install --upgrade pyinstaller >/dev/null

# torchvision 可能未安装：装了就一起收集
EXTRA=()
if "$PY" -c "import torchvision" 2>/dev/null; then EXTRA+=(--collect-all torchvision); fi

echo "==> 开始打包（首次较慢，产物 3-4 GB）"
"$PY" -m PyInstaller \
  --noconfirm --clean \
  --name imgsearch \
  --onedir --console \
  --collect-all torch \
  --collect-all open_clip \
  --collect-all timm \
  --collect-all transformers \
  --collect-all tokenizers \
  --collect-all safetensors \
  --collect-all sentencepiece \
  --collect-all huggingface_hub \
  --collect-all regex \
  --collect-all pillow_heif \
  --collect-all psd_tools \
  --collect-submodules uvicorn \
  --hidden-import uvicorn.logging \
  --hidden-import uvicorn.protocols.http.auto \
  --hidden-import uvicorn.protocols.websockets.auto \
  --hidden-import uvicorn.lifespan.on \
  "${EXTRA[@]}" \
  --add-data "web:web" \
  gui.py

cat <<EOF

==> 完成：dist/imgsearch/
    · 本机测试：  ./dist/imgsearch/imgsearch   然后浏览器开 http://127.0.0.1:57860
    · 迁移：      把整个 dist/imgsearch/ 目录拷到目标机运行（无需 Python）
    · 模型权重：  一并拷 ~/.cache/huggingface（免联网），索引拷 ~/.imgsearch
EOF
