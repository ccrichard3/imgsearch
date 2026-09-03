# 模型下载指南

imgsearch 支持多个 CLIP/SigLIP2 模型，默认内置最小模型 ViT-B-32。

---

## 📦 内置模型

**ViT-B-32** - 最快最轻（~340MB）
- 已打包在可执行文件/Docker 镜像中
- 首次启动即可使用，无需下载
- 适合快速体验和日常使用

---

## 🎯 可选模型

| 模型 | 大小 | 速度 | 精度 | 多语言 | 推荐场景 |
|------|------|------|------|--------|---------|
| ViT-B-32 ⭐ | 340MB | ★★★★★ | ★★★☆☆ | ★★★☆☆ | 日常使用（已内置） |
| ViT-B-16-SigLIP2-256 🔥 | 350MB | ★★★★☆ | ★★★★☆ | ★★★★★ | 推荐，中文友好 |
| ViT-L-16-SigLIP2-384 | 1.2GB | ★★★☆☆ | ★★★★★ | ★★★★★ | 高精度需求 |
| ViT-SO400M-16-SigLIP2-384 | 1.8GB | ★★☆☆☆ | ★★★★★ | ★★★★★ | 专业/商业 |
| ViT-L-14 | 890MB | ★★★☆☆ | ★★★★☆ | ★★★☆☆ | CLIP 经典（英文强） |

---

## 🌐 下载方式

### 方式 1：网页自动下载（推荐）

1. 启动 imgsearch
2. 打开网页 `http://localhost:57860`
3. 点击右上角「设置」⚙️
4. 选择想要的模型
5. 点击「切换模型」
6. 自动下载并加载（国内自动使用镜像加速）

**首次切换模型会下载，后续秒切**

---

### 方式 2：命令行下载

#### macOS / Linux

**可执行文件版本：**
```bash
./download_models.sh
```

**Python 环境版本：**
```bash
# 设置国内镜像（可选）
export HF_ENDPOINT=https://hf-mirror.com

# 下载指定模型
python3 -c "
import open_clip
model, _, preprocess = open_clip.create_model_and_transforms(
    'ViT-B-16-SigLIP2-256',  # 模型名
    pretrained='webli'        # 预训练权重
)
print('✓ 下载完成')
"
```

#### Windows

**可执行文件版本：**
```cmd
双击运行 download_models.bat
```

**Python 环境版本：**
```powershell
# 设置国内镜像（可选）
$env:HF_ENDPOINT="https://hf-mirror.com"

# 下载指定模型
python -c "import open_clip; model, _, preprocess = open_clip.create_model_and_transforms('ViT-B-16-SigLIP2-256', pretrained='webli'); print('✓ 下载完成')"
```

---

### 方式 3：Docker 环境

模型会在首次切换时自动下载到 volume `huggingface-cache` 中。

**查看下载进度：**
```bash
docker logs -f imgsearch
```

**预下载所有模型：**
```bash
docker exec -it imgsearch python3 -c "
import open_clip

models = [
    ('ViT-B-16-SigLIP2-256', 'webli'),
    ('ViT-L-16-SigLIP2-384', 'webli'),
    ('ViT-SO400M-16-SigLIP2-384', 'webli'),
    ('ViT-L-14', 'dfn2b'),
]

for model_name, pretrained in models:
    print(f'下载 {model_name}...')
    model, _, preprocess = open_clip.create_model_and_transforms(model_name, pretrained=pretrained)
    print(f'✓ {model_name} 完成')
"
```

---

## 🚀 国内加速（重要）

### 自动加速

**Docker 版本**：已默认配置 `HF_ENDPOINT=https://hf-mirror.com`

**可执行文件版本**：自动检测网络并使用镜像

### 手动配置

如果下载很慢或失败，手动设置镜像：

```bash
# macOS / Linux
export HF_ENDPOINT=https://hf-mirror.com

# Windows PowerShell
$env:HF_ENDPOINT="https://hf-mirror.com"

# Windows CMD
set HF_ENDPOINT=https://hf-mirror.com
```

**永久生效（可选）：**

```bash
# macOS / Linux
echo 'export HF_ENDPOINT=https://hf-mirror.com' >> ~/.bashrc
source ~/.bashrc

# Windows (系统环境变量)
setx HF_ENDPOINT "https://hf-mirror.com"
```

---

## 📁 模型存放位置

### 本地环境

- **macOS/Linux**: `~/.cache/huggingface/hub/`
- **Windows**: `%USERPROFILE%\.cache\huggingface\hub\`

**目录结构：**
```
~/.cache/huggingface/hub/
├── models--timm--ViT-B-16-SigLIP2-256/
│   └── snapshots/<hash>/
│       ├── open_clip_model.safetensors  (~350MB)
│       └── open_clip_config.json
├── models--timm--ViT-L-16-SigLIP2-384/
└── ...
```

### Docker 环境

存储在 Docker volume `huggingface-cache` 中

**查看位置：**
```bash
docker volume inspect huggingface-cache
```

**导出模型：**
```bash
docker run --rm -v huggingface-cache:/data -v $(pwd):/backup \
  alpine tar czf /backup/models.tar.gz -C /data .
```

**导入模型：**
```bash
docker run --rm -v huggingface-cache:/data -v $(pwd):/backup \
  alpine tar xzf /backup/models.tar.gz -C /data
```

---

## 🔄 迁移模型到其他机器

### 场景 1：同系统迁移（推荐）

直接拷贝缓存目录：

```bash
# 源机器打包
tar czf models.tar.gz ~/.cache/huggingface/

# 拷贝到目标机器
scp models.tar.gz user@target:/tmp/

# 目标机器解压
tar xzf /tmp/models.tar.gz -C ~
```

### 场景 2：Docker 容器间迁移

```bash
# 导出
docker run --rm -v huggingface-cache:/data -v $(pwd):/backup \
  alpine tar czf /backup/models.tar.gz -C /data .

# 拷贝 models.tar.gz 到目标机器后导入
docker volume create huggingface-cache
docker run --rm -v huggingface-cache:/data -v $(pwd):/backup \
  alpine tar xzf /backup/models.tar.gz -C /data
```

### 场景 3：离线部署

1. 在联网机器上下载所有需要的模型
2. 打包 `~/.cache/huggingface/`
3. 拷贝到离线机器并解压到相同位置
4. 离线机器正常运行（自动使用本地缓存）

---

## 🧪 验证模型

```python
import open_clip
import torch

# 列出可用模型
print(open_clip.list_pretrained())

# 测试加载
model, _, preprocess = open_clip.create_model_and_transforms(
    'ViT-B-16-SigLIP2-256',
    pretrained='webli'
)

print(f"✓ 模型加载成功")
print(f"参数量: {sum(p.numel() for p in model.parameters()) / 1e6:.1f}M")
```

---

## ❓ 常见问题

### Q: 下载速度很慢？

A: 确保已设置 `HF_ENDPOINT=https://hf-mirror.com`

### Q: 下载失败 Connection timeout？

A: 
1. 检查网络连接
2. 确认已设置国内镜像
3. 尝试手动下载（见下方）

### Q: 手动下载模型文件？

A: 访问镜像站下载：

1. 打开 https://hf-mirror.com/timm/ViT-B-16-SigLIP2-256
2. 点击 Files → 下载 `open_clip_model.safetensors`
3. 放到 `~/.cache/huggingface/hub/models--timm--ViT-B-16-SigLIP2-256/snapshots/<hash>/`
   - `<hash>` 为任意 40 位字符（可自己创建目录用随机值）

### Q: 切换模型后显示错误？

A: 
1. 查看日志：`docker logs imgsearch` 或终端输出
2. 删除缓存重新下载：`rm -rf ~/.cache/huggingface/hub/models--timm--<模型名>`
3. 重启 imgsearch

### Q: Docker 中模型占用空间太大？

A: 删除不用的模型：

```bash
docker exec -it imgsearch sh -c "
rm -rf /root/.cache/huggingface/hub/models--timm--ViT-SO400M-16-SigLIP2-384
"
```

### Q: 如何查看已下载的模型？

A: 
```bash
# 本地
ls -lh ~/.cache/huggingface/hub/models--timm--*/snapshots/*/open_clip_model.*

# Docker
docker exec imgsearch find /root/.cache/huggingface -name "open_clip_model.*" -exec ls -lh {} \;
```

---

## 📊 模型详细对比

### 检索精度（在 Flickr30k 上）

| 模型 | Text→Image R@1 | Image→Text R@1 |
|------|----------------|----------------|
| ViT-B-32 | 65.4% | 84.2% |
| ViT-B-16-SigLIP2-256 | 72.3% | 89.1% |
| ViT-L-16-SigLIP2-384 | 78.6% | 92.4% |
| ViT-SO400M-16-SigLIP2-384 | 82.1% | 94.2% |

### 多语言支持

- **SigLIP2 系列**：原生多语言，中日韩效果好
- **CLIP 系列**：英文优先，其他语言较弱

### 推理速度（Apple M2 Max）

| 模型 | 编码 1000 张图 | 单次搜索 |
|------|----------------|----------|
| ViT-B-32 | ~30s | ~0.3s |
| ViT-B-16-SigLIP2-256 | ~40s | ~0.4s |
| ViT-L-16-SigLIP2-384 | ~90s | ~0.8s |
| ViT-SO400M-16-SigLIP2-384 | ~180s | ~1.5s |

---

## 🔗 相关链接

- [OpenCLIP 项目](https://github.com/mlfoundations/open_clip)
- [SigLIP 论文](https://arxiv.org/abs/2303.15343)
- [HuggingFace 镜像站](https://hf-mirror.com/)
- [模型卡片](https://huggingface.co/timm)
