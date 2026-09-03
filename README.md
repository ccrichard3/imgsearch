# imgsearch 最小版本

轻量级本地图片搜索工具 —— 以图搜图 + 文字搜图

## ✨ 特性

- 🔍 **向量检索**：CLIP/SigLIP2 模型，支持以图搜图和文字搜图
- 🌍 **原生多语言**：中英日韩等，无需翻译
- 🚀 **增量索引**：只处理新增/改动图片，自动剔除已删除
- 📦 **最小版本**：内置轻量模型（~340MB），其他模型按需下载
- 🌐 **国内加速**：自动检测并使用 HuggingFace 镜像
- 🖼️ **格式全面**：JPG/PNG/HEIC/PSD/WEBP 等 20+ 格式
- 🔒 **完全本地**：图片不外传，数据存本地

---

## 📥 快速开始

### 方式 1：Docker（推荐，一行命令）

```bash
docker run -d \
  --name imgsearch \
  -p 57860:57860 \
  -v /你的图片路径:/library:ro \
  -v imgsearch-data:/root/.imgsearch \
  -e HF_ENDPOINT=https://hf-mirror.com \
  ghcr.io/你的用户名/imgsearch:minimal
```

访问 `http://localhost:57860`

### 方式 2：Docker Compose

```bash
# 1. 下载配置文件
curl -O https://raw.githubusercontent.com/你的用户名/imgsearch/main/docker-compose.minimal.yml

# 2. 修改图片路径
vim docker-compose.minimal.yml
# 改为: - /你的图片路径:/library:ro

# 3. 启动
docker-compose -f docker-compose.minimal.yml up -d
```

### 方式 3：NAS 一键部署

```bash
# 下载并运行部署脚本
curl -fsSL https://raw.githubusercontent.com/你的用户名/imgsearch/main/deploy_nas_minimal.sh | bash
```

### 方式 4：下载可执行文件（免 Python 环境）

前往 [Releases](https://github.com/你的用户名/imgsearch/releases) 下载对应平台：

- **macOS (Apple Silicon)**: `imgsearch-minimal-Darwin-arm64.tar.gz`
- **macOS (Intel)**: `imgsearch-minimal-Darwin-x86_64.tar.gz`
- **Linux (x86_64)**: `imgsearch-minimal-Linux-x86_64.tar.gz`
- **Windows (x64)**: `imgsearch-minimal-Windows-x86_64.zip`

解压后直接运行：
```bash
# macOS/Linux
./imgsearch-minimal

# Windows
imgsearch-minimal.exe
```

---

## 🎯 内置模型

**ViT-B-32** - 最快最轻（~340MB）
- 首次启动即可使用
- 适合快速体验和日常使用
- 检索速度最快，内存占用最小

## 📊 可选模型（按需下载）

| 模型 | 大小 | 速度 | 质量 | 适用场景 |
|------|------|------|------|---------|
| **ViT-B-32** ⭐ | ~340MB | 最快 | 良好 | 日常使用（已内置） |
| **ViT-B-16-SigLIP2-256** 🔥 | ~350MB | 快 | 优秀 | 推荐，多语言强 |
| **ViT-L-16-SigLIP2-384** | ~1.2GB | 中 | 很强 | 高精度需求 |
| **ViT-SO400M-16-SigLIP2-384** | ~1.8GB | 慢 | 最强 | 专业用途 |
| **ViT-L-14** | ~890MB | 中 | 优秀 | CLIP 经典（英文强） |

### 下载其他模型

**方式 1：网页切换（推荐）**
1. 访问 `http://localhost:57860`
2. 点击「设置」
3. 选择模型并切换
4. 自动下载（国内自动使用镜像加速）

**方式 2：可执行文件版本**
```bash
# 运行附带的下载脚本
./download_models.sh
```

**方式 3：手动下载（离线环境）**
```bash
# 设置镜像（国内用户）
export HF_ENDPOINT=https://hf-mirror.com

# 下载指定模型
python3 -c "
import open_clip
model, _, preprocess = open_clip.create_model_and_transforms(
    'ViT-B-16-SigLIP2-256', 
    pretrained='webli'
)
print('✓ 下载完成')
"
```

---

## 🌐 国内网络优化

### 自动加速

Docker 版本默认启用镜像加速（`HF_ENDPOINT=https://hf-mirror.com`）

### 手动配置

```bash
# macOS/Linux
export HF_ENDPOINT=https://hf-mirror.com

# Windows (PowerShell)
$env:HF_ENDPOINT="https://hf-mirror.com"

# Windows (CMD)
set HF_ENDPOINT=https://hf-mirror.com
```

### 模型存放位置

- **macOS/Linux**: `~/.cache/huggingface/hub/`
- **Windows**: `%USERPROFILE%\.cache\huggingface\hub\`
- **Docker**: Volume `huggingface-cache`

可在机器间拷贝此目录以避免重复下载

---

## 🛠️ 常用命令

### Docker 管理

```bash
# 查看日志
docker logs -f imgsearch

# 重启服务
docker restart imgsearch

# 停止服务
docker stop imgsearch

# 删除容器（数据保留在 volume 中）
docker rm -f imgsearch

# 删除数据
docker volume rm imgsearch-data huggingface-cache
```

### Docker Compose 管理

```bash
# 查看日志
docker-compose logs -f

# 重启
docker-compose restart

# 停止
docker-compose stop

# 删除（保留数据）
docker-compose down

# 删除（含数据）
docker-compose down -v
```

---

## 📁 数据存储

- **索引数据**: `~/.imgsearch/cache__<模型名>.pkl`
- **缩略图**: `~/.imgsearch/thumbs/`
- **配置**: `~/.imgsearch/config.json`
- **模型缓存**: `~/.cache/huggingface/`

删除 `~/.imgsearch/` 可清空索引重建

---

## 🔧 从源码构建

### 最小版本打包（macOS）

```bash
git clone https://github.com/你的用户名/imgsearch.git
cd imgsearch
./build_minimal.sh
```

产物：`dist/imgsearch-minimal/`（~2GB）

### Docker 镜像构建

```bash
# 最小版本（~2GB 镜像）
docker build -f Dockerfile.minimal -t imgsearch:minimal .

# 推送到 GitHub Container Registry
docker tag imgsearch:minimal ghcr.io/你的用户名/imgsearch:minimal
docker push ghcr.io/你的用户名/imgsearch:minimal
```

---

## ❓ 常见问题

### Q: 首次启动很慢？
A: 内置模型已打包，启动秒开。切换其他模型时需联网下载一次。

### Q: 模型下载失败？
A: 国内用户确保已设置 `HF_ENDPOINT=https://hf-mirror.com`

### Q: 端口冲突？
A: 修改端口映射：`-p 8080:57860`（左侧改为你的端口）

### Q: Docker 镜像拉取慢？
A: 
```bash
# 配置 Docker 镜像加速
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<EOF
{
  "registry-mirrors": ["https://docker.mirrors.ustc.edu.cn"]
}
EOF
sudo systemctl restart docker
```

### Q: 如何切换模型？
A: 网页「设置」-> 选择模型 -> 切换（首次自动下载）

### Q: 离线环境如何使用？
A: 
1. 联网环境运行一次（自动缓存模型）
2. 拷贝 `~/.cache/huggingface/` 到离线机器
3. 离线机器正常使用

---

## 📊 性能参考

### 索引速度（1万张图片）

- macOS (Apple Silicon MPS): ~5 分钟
- Linux (NVIDIA GPU): ~8 分钟
- NAS (Intel CPU): ~20 分钟
- Windows (CPU): ~15 分钟

### 搜索响应

- macOS (MPS): ~0.5 秒
- Linux (CUDA): ~0.8 秒
- NAS/Windows (CPU): ~2 秒

---

## 🔗 相关链接

- [完整版 README](./README.full.md)（包含开发指南）
- [Windows 部署文档](./DEPLOY_WINDOWS.md)
- [模型详细说明](https://github.com/mlfoundations/open_clip)

---

## 📝 许可证

MIT License

---

## 🙏 致谢

- [OpenCLIP](https://github.com/mlfoundations/open_clip) - CLIP 模型实现
- [HuggingFace](https://huggingface.co/) - 模型托管
- [hf-mirror.com](https://hf-mirror.com/) - 国内镜像加速
