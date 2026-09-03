#!/bin/bash
# NAS 一键部署脚本（最小版本，~2GB 镜像）
set -euo pipefail

echo "========================================"
echo "  imgsearch 最小版本 - NAS 一键部署"
echo "========================================"
echo ""
echo "内置模型：ViT-B-32 (最快，~340MB)"
echo "其他模型：启动后在网页中切换，自动下载"
echo ""

# 检测 Docker
if ! command -v docker &>/dev/null; then
    echo "❌ 未检测到 Docker，请先安装"
    exit 1
fi

# 输入图片库路径
read -p "图片库路径（如 /vol1/photo）: " PHOTO_PATH
if [ -z "$PHOTO_PATH" ] || [ ! -d "$PHOTO_PATH" ]; then
    echo "❌ 路径不存在：$PHOTO_PATH"
    exit 1
fi

# 输入用户名（用于镜像地址）
read -p "GitHub 用户名（用于拉取镜像）: " GITHUB_USER
if [ -z "$GITHUB_USER" ]; then
    echo "❌ 用户名不能为空"
    exit 1
fi

# 生成配置
cat > docker-compose.yml <<EOF
version: '3.8'

services:
  imgsearch:
    image: ghcr.io/${GITHUB_USER}/imgsearch:minimal
    container_name: imgsearch
    ports:
      - "57860:57860"
    volumes:
      - ${PHOTO_PATH}:/library:ro
      - imgsearch-data:/root/.imgsearch
      - huggingface-cache:/root/.cache/huggingface
    environment:
      - HF_ENDPOINT=https://hf-mirror.com
      - PYTHONUNBUFFERED=1
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 4G

volumes:
  imgsearch-data:
  huggingface-cache:
EOF

echo ""
echo "✓ 配置已生成到 docker-compose.yml"
echo ""

# 检测网络
echo "检测网络环境..."
if curl -s --connect-timeout 3 https://ghcr.io >/dev/null 2>&1; then
    echo "✓ 可访问 GitHub Container Registry"
else
    echo "⚠ 无法直连 ghcr.io，可能需要配置代理"
fi

echo ""
read -p "是否立即启动？[Y/n] " confirm
if [[ "$confirm" =~ ^[Nn] ]]; then
    echo "取消启动，稍后运行：docker-compose up -d"
    exit 0
fi

echo ""
echo "==> 拉取镜像（首次约 2GB，国内可能较慢）"
docker-compose pull

echo ""
echo "==> 启动容器"
docker-compose up -d

echo ""
echo "==> 查看日志"
docker-compose logs -f --tail 50 &
LOG_PID=$!

sleep 5
kill $LOG_PID 2>/dev/null || true

echo ""
echo "========================================"
echo "  部署完成"
echo "========================================"
echo ""
echo "访问地址：http://$(hostname -I | awk '{print $1}'):57860"
echo ""
echo "常用命令："
echo "  查看日志：docker-compose logs -f"
echo "  停止服务：docker-compose stop"
echo "  重启服务：docker-compose restart"
echo "  删除服务：docker-compose down"
echo ""
echo "数据位置："
echo "  索引数据：Docker volume 'imgsearch-data'"
echo "  模型缓存：Docker volume 'huggingface-cache'"
echo "  查看位置：docker volume inspect imgsearch-data"
echo ""
echo "切换模型："
echo "  1. 访问网页 -> 设置 -> 切换模型"
echo "  2. 首次使用新模型会自动下载（国内自动用镜像加速）"
echo "  3. 下载进度见日志：docker-compose logs -f"
echo ""
