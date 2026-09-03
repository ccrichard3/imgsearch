#!/bin/bash
# NAS 部署脚本（支持 Debian / Ubuntu / Synology / QNAP）
set -euo pipefail

echo "==> imgsearch NAS 部署"

# 检查 Docker
if ! command -v docker &>/dev/null; then
    echo "!! 未安装 Docker，请先安装：https://docs.docker.com/engine/install/"
    exit 1
fi

# 检查 docker-compose
if ! command -v docker-compose &>/dev/null && ! docker compose version &>/dev/null; then
    echo "!! 未安装 docker-compose，安装中..."
    pip3 install docker-compose || {
        echo "!! 安装失败，请手动安装 docker-compose"
        exit 1
    }
fi

# 创建数据目录
mkdir -p data/imgsearch data/huggingface

# 修改 docker-compose.yml 中的图片库路径
read -p "图片库路径（默认 /vol1/photo）: " LIBRARY_PATH
LIBRARY_PATH=${LIBRARY_PATH:-/vol1/photo}

if [ ! -d "$LIBRARY_PATH" ]; then
    echo "!! 路径不存在: $LIBRARY_PATH"
    exit 1
fi

# 替换路径
sed -i.bak "s|/vol1/photo|$LIBRARY_PATH|g" docker-compose.yml
rm docker-compose.yml.bak

# 构建并启动
echo "==> 构建镜像（首次较慢，需下载 ~2GB 模型）"
docker-compose build

echo "==> 启动服务"
docker-compose up -d

echo "==> 等待服务就绪..."
sleep 10

if docker ps | grep -q imgsearch; then
    IP=$(hostname -I | awk '{print $1}')
    echo ""
    echo "✓ 部署完成！"
    echo "  访问地址: http://$IP:57860"
    echo "  日志查看: docker-compose logs -f"
    echo "  停止服务: docker-compose down"
else
    echo "!! 启动失败，查看日志: docker-compose logs"
    exit 1
fi
