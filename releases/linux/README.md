# Linux 平台部署

## 方式 1：Docker 部署（推荐）

参考 [Docker 部署说明](../docker/README.md)

```bash
docker run -d \
  --name imgsearch \
  -p 57860:57860 \
  -v /你的图片路径:/library:ro \
  -v imgsearch-data:/root/.imgsearch \
  -e HF_ENDPOINT=https://hf-mirror.com \
  ghcr.io/ccrichard3/imgsearch:minimal
```

## 方式 2：直接运行

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行

```bash
python3 app.py
```

访问 `http://localhost:57860`

## 系统要求

- Python 3.8+
- 推荐 8GB+ 内存
- 支持 CUDA/ROCm 可启用 GPU 加速

