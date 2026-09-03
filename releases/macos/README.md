# macOS 平台打包

## 构建最小版本

```bash
./build_minimal.sh
```

产物：`dist/imgsearch-minimal/`（~2GB，内置 ViT-B-32 模型）

## 运行方式

### 方式 1：双击运行
- 解压后双击 `imgsearch.app`
- 或双击 `run.command`

### 方式 2：命令行运行
```bash
./launch.sh
```

## 图标制作

```bash
python3 make_icon.py
```

生成 `imgsearch.icns` 用于打包
