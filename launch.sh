#!/bin/bash
# imgsearch 启动脚本：建/复用虚拟环境 → 后台启动服务 → 端口就绪后开浏览器。
# 由 imgsearch.app 的 applet 在后台调用（applet 秒返回，不卡死、可从 dock 退出）。
# 服务为 FastAPI（gui.py），前端不自动开浏览器；只在这里开一次页面。
set -uo pipefail

PROJ="/Users/cc/程序/imgsearch"
cd "$PROJ" || exit 1
mkdir -p "$HOME/.imgsearch"
LOG="$HOME/.imgsearch/app.log"

# 端口：从 ~/.imgsearch/config.json 读取（用户可在「设置」里改，下次启动生效）；读不到用默认
CFG="$HOME/.imgsearch/config.json"
PORT=$(/usr/bin/python3 -c "import json;print(int(json.load(open('$CFG')).get('port',57860)))" 2>/dev/null || echo 57860)
[ -z "$PORT" ] && PORT=57860
URL="http://127.0.0.1:$PORT"

# 已在运行：直接开浏览器，退出
if /usr/bin/nc -z 127.0.0.1 "$PORT" >/dev/null 2>&1; then
    /usr/bin/open "$URL"
    exit 0
fi

# 首次：创建虚拟环境并安装依赖
if [ ! -d .venv ]; then
    /opt/homebrew/bin/python3.11 -m venv .venv
    ./.venv/bin/python -m pip install --upgrade pip >>"$LOG" 2>&1
    ./.venv/bin/python -m pip install -r requirements.txt >>"$LOG" 2>&1
fi

# 后台启动服务（gui.py 启动时先做一次「带阈值」的增量索引，再开端口）
nohup ./.venv/bin/python gui.py >>"$LOG" 2>&1 &

# 等端口就绪后开浏览器；首次要建 venv/装依赖或大量索引时可能较久，最多等 10 分钟
for _ in $(seq 1 1200); do
    if /usr/bin/nc -z 127.0.0.1 "$PORT" >/dev/null 2>&1; then
        break
    fi
    sleep 0.5
done
/usr/bin/open "$URL"
