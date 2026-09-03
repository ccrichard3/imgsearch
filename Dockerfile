# imgsearch Docker 镜像（支持 amd64 / arm64）
FROM python:3.11-slim

# 安装依赖（图片格式支持）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libheif1 libde265-0 libx265-199 libaom3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app.py gui.py ./
COPY web/ ./web/

# 数据目录（索引、缩略图、模型缓存）
VOLUME /root/.imgsearch
VOLUME /root/.cache/huggingface
VOLUME /library

# 默认端口
EXPOSE 57860

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s \
  CMD python -c "import socket; s=socket.socket(); s.connect(('127.0.0.1',57860)); s.close()"

# 启动服务
CMD ["python", "gui.py"]
