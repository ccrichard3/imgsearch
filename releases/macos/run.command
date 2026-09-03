#!/bin/bash
# imgsearch 启动器 —— 双击即可运行（首次会自动建 venv 并装依赖）
set -euo pipefail

# 切到脚本所在目录（双击时工作目录不确定）
cd "$(dirname "$0")"

VENV=".venv"
# 优先用 brew 的 python3.11（对 torch/gradio wheel 兼容性最好），退回 python3
if [ -x /opt/homebrew/bin/python3.11 ]; then
  PY=/opt/homebrew/bin/python3.11
elif command -v python3.11 >/dev/null 2>&1; then
  PY=python3.11
else
  PY=python3
fi

if [ ! -d "$VENV" ]; then
  echo "==> 首次运行：创建虚拟环境（$PY）"
  "$PY" -m venv "$VENV"
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
  echo "==> 升级 pip"
  python -m pip install --upgrade pip
  echo "==> 安装依赖（首次较慢，需下载 torch 等，请耐心等待）"
  python -m pip install -r requirements.txt
else
  # shellcheck disable=SC1091
  source "$VENV/bin/activate"
fi

echo "==> 启动 imgsearch 网页界面…"

# 端口：从 ~/.imgsearch/config.json 读取（可在「设置」里改，下次启动生效）
CFG="$HOME/.imgsearch/config.json"
PORT=$(python -c "import json;print(int(json.load(open('$CFG')).get('port',57860)))" 2>/dev/null || echo 57860)
[ -z "$PORT" ] && PORT=57860
URL="http://127.0.0.1:$PORT"

echo "    浏览器将自动打开 $URL"
echo "    关闭本终端窗口即可停止服务。"

# gui.py 是 FastAPI 服务、不会自动开浏览器，这里在端口就绪后开一次页面
(
  for _ in $(seq 1 1200); do
    if /usr/bin/nc -z 127.0.0.1 "$PORT" >/dev/null 2>&1; then
      /usr/bin/open "$URL"; break
    fi
    sleep 0.5
  done
) &

exec python gui.py

