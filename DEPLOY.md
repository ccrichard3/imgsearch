# imgsearch 部署指南

## 📦 三种部署方式

### 1️⃣ 无 Python 环境（PyInstaller 打包）

**适用：** 需要分发给其他用户，目标机器无 Python 环境

#### macOS / Linux
```bash
cd /Users/cc/程序/imgsearch
./build_standalone.sh
```

产物：`dist/imgsearch/`（3-4GB），包含所有依赖

**迁移到目标机：**
```bash
# 拷贝程序
tar czf imgsearch.tar.gz dist/imgsearch/
scp imgsearch.tar.gz 目标机:/path/to/

# 目标机解压运行
tar xzf imgsearch.tar.gz
cd imgsearch
./imgsearch
```

**可选：预装模型和索引**
```bash
# 拷贝模型缓存（~2GB，免首次联网下载）
scp -r ~/.cache/huggingface/ 目标机:~/.cache/

# 拷贝已有索引（免重建）
scp -r ~/.imgsearch/ 目标机:~/
```

#### Windows
参见 `DEPLOY_WINDOWS.md` 中的方案 A

---

### 2️⃣ NAS / 服务器（Docker）

**适用：** NAS（Synology/QNAP）、VPS、家庭服务器

#### 快速部署
```bash
cd /Users/cc/程序/imgsearch

# 一键部署（会提示输入图片库路径）
./deploy_nas.sh
```

#### 手动部署
```bash
# 1. 修改 docker-compose.yml 中的图片库路径
vim docker-compose.yml
# 改为: - /你的图片路径:/library:ro

# 2. 构建并启动
docker-compose up -d

# 3. 查看日志
docker-compose logs -f

# 4. 访问服务
# http://<NAS_IP>:57860
```

**持久化数据：**
- 索引：`./data/imgsearch/`
- 模型缓存：`./data/huggingface/`
- 容器重启数据不丢失

**资源限制：**
- 默认限制 4 核 CPU + 8GB 内存
- 可在 docker-compose.yml 中调整

---

### 3️⃣ Windows 桌面（直接运行）

**适用：** Windows 个人电脑，有 Python 环境

#### 方式 A：双击启动（推荐）
1. 确保已安装 Python 3.11+
2. 双击 `启动.bat`
3. 首次运行自动安装依赖（3-5 分钟）
4. 浏览器自动打开

#### 方式 B：命令行
```powershell
cd imgsearch
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-windows.txt
python gui.py
```

详见 `DEPLOY_WINDOWS.md`

---

## 🎯 部署对比

| 方式 | 优点 | 缺点 | 适用场景 |
|------|------|------|---------|
| **PyInstaller** | 免 Python 环境，开箱即用 | 包体积大（3-4GB） | 分发给非技术用户 |
| **Docker** | 环境隔离，易管理，跨平台 | 需 Docker 环境 | NAS / 服务器 / 多用户 |
| **直接运行** | 灵活，易调试，占用小 | 需配置 Python | 开发 / 个人使用 |

---

## 📊 性能说明

- **macOS (MPS):** 最快，Apple Silicon 原生加速
- **Linux (CUDA):** 次快，需 NVIDIA GPU
- **Windows (CPU):** 较慢，纯 CPU 推理
- **NAS (CPU):** 最慢，但适合 7×24 运行

**索引速度参考：**
- 1 万张图：macOS ~5 分钟，NAS ~20 分钟
- 搜索响应：macOS ~0.5 秒，NAS ~2 秒

---

## 🔧 高级配置

### 修改端口
编辑 `gui.py`：
```python
DEFAULT_PORT = 57860  # 改为你的端口
```

### 配置 HuggingFace 镜像（国内加速）
```bash
export HF_ENDPOINT=https://hf-mirror.com
```

### 多图库支持
启动后在网页「设置」中添加多个库根目录

### GPU 加速（Windows/Linux）
```bash
# NVIDIA GPU（CUDA 12.1）
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

---

## 📁 文件说明

```
imgsearch/
├── app.py                  # 核心搜索引擎
├── gui.py                  # FastAPI Web 服务
├── web/                    # 前端静态文件
│   ├── index.html
│   ├── app.js
│   └── app.css
├── requirements.txt        # macOS/Linux 依赖
├── requirements-windows.txt # Windows 依赖
├── build_standalone.sh     # PyInstaller 打包脚本
├── Dockerfile              # Docker 镜像
├── docker-compose.yml      # Docker Compose 配置
├── deploy_nas.sh           # NAS 一键部署
├── 启动.bat                # Windows 启动脚本
├── DEPLOY_WINDOWS.md       # Windows 详细文档
└── README.md               # 本文档
```

---

## ❓ 常见问题

### Q: 端口被占用？
A: 修改 `gui.py` 中的 `DEFAULT_PORT` 或启动时加参数 `--port 8080`

### Q: 模型下载很慢？
A: 国内使用 HuggingFace 镜像：`export HF_ENDPOINT=https://hf-mirror.com`

### Q: NAS 上太慢？
A: 
1. 减少并发：修改 docker-compose.yml 中的 CPU 限制
2. 使用更小的模型：在网页设置中切换模型
3. 预先索引：在性能强的机器上索引后拷贝 `~/.imgsearch`

### Q: Docker 容器启动失败？
A: 查看日志 `docker-compose logs`，常见原因：
- 图片库路径不存在
- 内存不足（至少 4GB 可用）
- 端口被占用

### Q: Windows HEIC 格式不支持？
A: 安装 `pillow-heif` 需要系统 libheif 库，可通过 MSYS2 安装或使用预编译包
