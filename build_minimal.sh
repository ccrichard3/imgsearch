#!/bin/bash
# 打包「最小可用版本」—— 仅内置 ViT-B-32 轻量模型（~340MB）
# 其他模型由用户按需下载（提供国内镜像加速指南）
set -euo pipefail
cd "$(dirname "$0")"

PY=./.venv/bin/python
[ -x "$PY" ] || { echo "!! 未找到 .venv，请先运行 ./run.command"; exit 1; }

echo "==> 预下载最小模型 ViT-B-32（~340MB，打包后免首次联网）"
"$PY" -c "
import open_clip
model, _, preprocess = open_clip.create_model_and_transforms('ViT-B-32', pretrained='laion2b_s34b_b79k')
print('✓ 模型已缓存到 ~/.cache/huggingface')
"

echo "==> 安装 pyinstaller"
"$PY" -m pip install --upgrade pyinstaller >/dev/null

EXTRA=()
if "$PY" -c "import torchvision" 2>/dev/null; then EXTRA+=(--collect-all torchvision); fi

echo "==> 打包中（最小版本，产物 ~2GB）"
"$PY" -m PyInstaller \
  --noconfirm --clean \
  --name imgsearch-minimal \
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

# 创建模型下载脚本
cat > dist/imgsearch-minimal/download_models.sh <<'SCRIPT'
#!/bin/bash
# 下载其他模型到本地缓存
set -e

echo "imgsearch 模型下载工具"
echo "======================="
echo ""
echo "可用模型："
echo "  1. ViT-B-32 (已内置，~340MB，最快)"
echo "  2. ViT-B-16-SigLIP2-256 (推荐，~350MB，快速+多语言)"
echo "  3. ViT-L-16-SigLIP2-384 (~1.2GB，精度高)"
echo "  4. ViT-SO400M-16-SigLIP2-384 (~1.8GB，最强)"
echo "  5. ViT-L-14 (~890MB，CLIP 经典)"
echo ""
read -p "选择下载 [2-5]，留空跳过: " choice

case "$choice" in
  2) MODEL="ViT-B-16-SigLIP2-256"; PRETRAINED="webli" ;;
  3) MODEL="ViT-L-16-SigLIP2-384"; PRETRAINED="webli" ;;
  4) MODEL="ViT-SO400M-16-SigLIP2-384"; PRETRAINED="webli" ;;
  5) MODEL="ViT-L-14"; PRETRAINED="dfn2b" ;;
  "") echo "跳过下载"; exit 0 ;;
  *) echo "无效选择"; exit 1 ;;
esac

# 检测网络环境
echo "检测网络环境..."
if curl -s --connect-timeout 3 https://huggingface.co >/dev/null 2>&1; then
    echo "✓ 直连 HuggingFace"
    export HF_ENDPOINT=""
else
    echo "⚠ 无法直连，使用国内镜像 hf-mirror.com"
    export HF_ENDPOINT=https://hf-mirror.com
fi

echo ""
echo "开始下载模型: $MODEL ($PRETRAINED)"
python3 -c "
import open_clip
model, _, preprocess = open_clip.create_model_and_transforms('$MODEL', pretrained='$PRETRAINED')
print('✓ 下载完成，已缓存到 ~/.cache/huggingface')
"
SCRIPT

chmod +x dist/imgsearch-minimal/download_models.sh

cat > dist/imgsearch-minimal/README.txt <<'README'
imgsearch 最小版本
==================

内置模型：ViT-B-32 (最快，~340MB)

运行：
  macOS/Linux:  ./imgsearch-minimal
  Windows:      imgsearch-minimal.exe

下载其他模型：
  ./download_models.sh  (macOS/Linux)
  或访问 https://github.com/你的用户名/imgsearch

模型存放位置：
  macOS/Linux:  ~/.cache/huggingface/hub/
  Windows:      %USERPROFILE%\.cache\huggingface\hub\

国内镜像加速：
  export HF_ENDPOINT=https://hf-mirror.com  (设置后自动使用镜像)

手动下载模型（国内用户）：
  1. 访问 https://hf-mirror.com/timm/ViT-B-16-SigLIP2-256
  2. 下载 open_clip_model.safetensors
  3. 放到 ~/.cache/huggingface/hub/models--timm--ViT-B-16-SigLIP2-256/snapshots/<hash>/
     (程序首次运行会自动创建此目录)

索引数据：
  ~/.imgsearch/  (可删除后重建)
README

cat <<EOF

==> 完成：dist/imgsearch-minimal/

产物说明：
  · 大小：~2GB（仅含最小模型 ViT-B-32）
  · 测试：./dist/imgsearch-minimal/imgsearch-minimal
  · 其他模型：运行 ./download_models.sh 或启动后在网页中切换（自动下载）

分发：
  tar czf imgsearch-minimal-$(uname -s)-$(uname -m).tar.gz dist/imgsearch-minimal/

迁移到目标机：
  1. 解压运行即可使用最小模型
  2. 联网环境：切换模型时自动下载
  3. 离线环境：运行 download_models.sh 提前下载
  4. 国内用户：自动检测并使用 hf-mirror.com 加速
EOF
