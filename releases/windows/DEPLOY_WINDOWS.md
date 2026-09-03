# imgsearch Windows 部署指南

## 方案 A：PyInstaller 打包（推荐）

### 1. 在 Windows 机器上打包

**前置条件：** Windows 10/11 + Python 3.11

```powershell
# 克隆项目
git clone <repo_url> imgsearch
cd imgsearch

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 安装依赖
pip install -r requirements-windows.txt

# 安装 PyInstaller
pip install pyinstaller

# 打包
pyinstaller --noconfirm --clean --name imgsearch --onedir --console `
  --collect-all torch --collect-all open_clip --collect-all timm `
  --collect-all transformers --collect-all tokenizers --collect-all safetensors `
  --collect-all sentencepiece --collect-all huggingface_hub --collect-all regex `
  --collect-all pillow_heif --collect-all psd_tools `
  --collect-submodules uvicorn `
  --hidden-import uvicorn.logging `
  --hidden-import uvicorn.protocols.http.auto `
  --hidden-import uvicorn.protocols.websockets.auto `
  --hidden-import uvicorn.lifespan.on `
  --add-data "web;web" `
  gui.py
```

产物：`dist\imgsearch\imgsearch.exe`（3-4GB）

### 2. 运行

双击 `imgsearch.exe` 或命令行：
```powershell
cd dist\imgsearch
.\imgsearch.exe
```

浏览器自动打开 `http://127.0.0.1:57860`

---

## 方案 B：直接运行（需 Python 环境）

### 1. 安装 Python 3.11

下载：https://www.python.org/downloads/windows/

**重要：** 安装时勾选 "Add Python to PATH"

### 2. 安装依赖并运行

```powershell
cd imgsearch

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 安装依赖（Windows 版本）
pip install -r requirements-windows.txt

# 运行
python gui.py
```

---

## 方案 C：Docker Desktop（需 WSL2）

### 1. 安装 Docker Desktop

下载：https://www.docker.com/products/docker-desktop/

**前置：** 启用 WSL2（Windows 10 build 19041+ / Windows 11）

### 2. 部署

```powershell
cd imgsearch

# 修改 docker-compose.yml 中的图片库路径
# - D:/Photos:/library:ro

# 启动
docker-compose up -d

# 访问 http://localhost:57860
```

---

## 启动脚本（方案 B 快捷方式）

创建 `启动.bat`：

```batch
@echo off
cd /d "%~dp0"
if not exist .venv (
    echo 首次运行，创建虚拟环境...
    python -m venv .venv
    call .venv\Scripts\activate
    pip install -r requirements-windows.txt
)
call .venv\Scripts\activate
python gui.py
pause
```

双击运行即可。

---

## 性能说明

- **CPU:** Windows 版本只用 CPU（torch 默认），速度比 macOS MPS 慢 2-3 倍
- **GPU:** 若有 NVIDIA 显卡，安装 CUDA 版 PyTorch 可加速：
  ```powershell
  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
  ```
- **内存:** 建议 16GB+，单次搜索峰值 ~4GB

---

## 常见问题

### Q: 模型下载很慢？
A: 首次启动需下载 ~2GB 模型，国内可配置 HuggingFace 镜像：
```powershell
set HF_ENDPOINT=https://hf-mirror.com
```

### Q: 端口被占用？
A: 修改 `gui.py` 中的 `DEFAULT_PORT = 57860`

### Q: 无法识别 HEIC 格式？
A: Windows 需额外安装 HEIF 解码器：
```powershell
pip install pillow-heif
# 还需系统安装 libheif（通过 MSYS2 或预编译包）
```
