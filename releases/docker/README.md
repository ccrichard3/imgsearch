# Docker 部署

## 最小版本（推荐）

```bash
docker run -d \
  --name imgsearch \
  -p 57860:57860 \
  -v /你的图片路径:/library:ro \
  -v imgsearch-data:/root/.imgsearch \
  -e HF_ENDPOINT=https://hf-mirror.com \
  ghcr.io/ccrichard3/imgsearch:minimal
```

## Docker Compose 部署

```bash
# 修改 docker-compose.minimal.yml 中的图片路径
docker-compose -f docker-compose.minimal.yml up -d
```

## 构建镜像

```bash
# 最小版本
docker build -f Dockerfile.minimal -t imgsearch:minimal .

# 完整版本
docker build -f Dockerfile -t imgsearch:latest .
```

## 镜像说明

- **minimal**: ~2GB，内置 ViT-B-32 模型
- **latest**: ~500MB，首次启动时下载模型

访问 `http://localhost:57860` 使用
