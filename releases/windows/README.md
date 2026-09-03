# Windows 平台打包

## 构建最小版本

在 WSL 或 Linux 环境下运行：

```bash
./build_minimal_windows.sh
```

产物：`dist/imgsearch-minimal-windows/`（~2GB，内置 ViT-B-32 模型）

## 运行方式

### 方式 1：双击运行
解压后双击 `启动.bat`

### 方式 2：命令行运行
```cmd
imgsearch-minimal.exe
```

## 模型下载

首次运行后，可使用 `download_models.bat` 下载其他模型

## 依赖说明

使用 PyInstaller 打包，已包含所有依赖，无需安装 Python 环境
