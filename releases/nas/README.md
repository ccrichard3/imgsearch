# NAS 一键部署

## 最小版本部署（推荐）

```bash
curl -fsSL https://raw.githubusercontent.com/ccrichard3/imgsearch/main/releases/nas/deploy_nas_minimal.sh | bash
```

或下载后运行：

```bash
wget https://raw.githubusercontent.com/ccrichard3/imgsearch/main/releases/nas/deploy_nas_minimal.sh
chmod +x deploy_nas_minimal.sh
./deploy_nas_minimal.sh
```

## 完整版本部署

```bash
curl -fsSL https://raw.githubusercontent.com/ccrichard3/imgsearch/main/releases/nas/deploy_nas.sh | bash
```

## 脚本功能

- 自动检测 Docker 环境
- 交互式配置图片路径
- 配置 HuggingFace 镜像加速
- 自动拉取并启动容器
- 提供访问地址

## 适用平台

- 群晖 NAS (Synology DSM)
- 威联通 NAS (QNAP QTS)
- 飞牛 OS (FnOS)
- 其他支持 Docker 的 NAS 系统
