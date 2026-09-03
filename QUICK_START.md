# 🚀 快速开始

## 🐳 Docker 一键部署（推荐）

```bash
docker run -d \
  --name imgsearch \
  -p 57860:57860 \
  -v /你的图片路径:/library:ro \
  -v imgsearch-data:/root/.imgsearch \
  -v huggingface-cache:/root/.cache/huggingface \
  ghcr.io/ccrichard3/imgsearch:minimal
```

访问 `http://localhost:57860`

---

## 📦 NAS 一键部署

```bash
curl -fsSL https://raw.githubusercontent.com/ccrichard3/imgsearch/main/deploy_nas_minimal.sh | bash
```

---

## 💻 本地运行

### macOS / Linux

```bash
# 下载可执行文件
wget https://github.com/ccrichard3/imgsearch/releases/latest/download/imgsearch-minimal-$(uname -s)-$(uname -m).tar.gz

# 解压运行
tar xzf imgsearch-minimal-*.tar.gz
cd imgsearch-minimal
./imgsearch-minimal
```

### Windows

1. 下载 [imgsearch-minimal-Windows-x86_64.zip](https://github.com/ccrichard3/imgsearch/releases/latest)
2. 解压后双击 `imgsearch-minimal.exe`
3. 浏览器访问 `http://localhost:57860`

---

## 🎯 内置模型

**ViT-B-32** (~340MB) - 最快最轻，开箱即用

## 📥 下载其他模型

### 方式 1：网页切换（推荐）
设置 → 选择模型 → 自动下载

### 方式 2：命令行
```bash
# 可执行文件版本
./download_models.sh  # macOS/Linux
download_models.bat   # Windows

# Docker 版本
docker exec imgsearch python3 -c "
import open_clip
model, _, _ = open_clip.create_model_and_transforms('ViT-B-16-SigLIP2-256', pretrained='webli')
print('✓ 下载完成')
"
```

详见 [MODELS.md](./MODELS.md)

---

## 🌐 国内加速

自动使用 hf-mirror.com 镜像加速

手动配置：
```bash
export HF_ENDPOINT=https://hf-mirror.com
```

---

## 📚 完整文档

- [README.md](./README.md) - 完整说明
- [MODELS.md](./MODELS.md) - 模型下载指南
- [DEPLOY_WINDOWS.md](./DEPLOY_WINDOWS.md) - Windows 部署
