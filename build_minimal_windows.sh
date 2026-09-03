#!/bin/bash
# Windows 打包脚本 - 最小版本（需在 Windows 上运行）
# 仅内置 ViT-B-32 轻量模型

echo "Windows 最小版本打包"
echo "===================="
echo ""
echo "前置条件："
echo "  - Windows 10/11"
echo "  - Python 3.11"
echo "  - 已安装依赖 (pip install -r requirements-windows.txt)"
echo ""

# 检查 Python
if ! command -v python &>/dev/null; then
    echo "错误：未找到 Python"
    exit 1
fi

echo "==> 预下载最小模型 ViT-B-32"
python -c "
import open_clip
model, _, preprocess = open_clip.create_model_and_transforms('ViT-B-32', pretrained='laion2b_s34b_b79k')
print('✓ 模型已缓存')
"

echo ""
echo "==> 安装 PyInstaller"
python -m pip install --upgrade pyinstaller

echo ""
echo "==> 开始打包（需 10-15 分钟）"
python -m PyInstaller \
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
  --add-data "web;web" \
  gui.py

# 复制模型下载脚本
cp download_models.bat dist/imgsearch-minimal/

# 创建说明文件
cat > dist/imgsearch-minimal/README.txt <<'EOF'
imgsearch 最小版本 (Windows)
=============================

运行：
  双击 imgsearch-minimal.exe

内置模型：
  ViT-B-32 (最快，~340MB)

下载其他模型：
  双击 download_models.bat

模型存放位置：
  %USERPROFILE%\.cache\huggingface\hub\

国内加速：
  自动检测并使用 hf-mirror.com

访问地址：
  http://127.0.0.1:57860

问题反馈：
  https://github.com/你的用户名/imgsearch/issues
EOF

echo ""
echo "========================================="
echo "  打包完成"
echo "========================================="
echo ""
echo "产物：dist\imgsearch-minimal\"
echo "大小：约 2GB"
echo ""
echo "测试："
echo "  cd dist\imgsearch-minimal"
echo "  .\imgsearch-minimal.exe"
echo ""
echo "分发："
echo "  打包 dist\imgsearch-minimal\ 为 zip"
echo "  上传到 GitHub Releases"
echo ""
