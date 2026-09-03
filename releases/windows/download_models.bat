@echo off
chcp 65001 >nul
title imgsearch 最小版本 - 下载其他模型

echo ========================================
echo   imgsearch 模型下载工具
echo ========================================
echo.
echo 当前已安装模型：
echo   [✓] ViT-B-32 (已内置，最快)
echo.
echo 可下载模型：
echo   [1] ViT-B-16-SigLIP2-256 (推荐，~350MB，多语言强)
echo   [2] ViT-L-16-SigLIP2-384 (~1.2GB，高精度)
echo   [3] ViT-SO400M-16-SigLIP2-384 (~1.8GB，最强)
echo   [4] ViT-L-14 (~890MB，CLIP 经典)
echo   [0] 退出
echo.

set /p choice="请选择 [0-4]: "

if "%choice%"=="0" exit /b 0
if "%choice%"=="1" (
    set MODEL=ViT-B-16-SigLIP2-256
    set PRETRAINED=webli
)
if "%choice%"=="2" (
    set MODEL=ViT-L-16-SigLIP2-384
    set PRETRAINED=webli
)
if "%choice%"=="3" (
    set MODEL=ViT-SO400M-16-SigLIP2-384
    set PRETRAINED=webli
)
if "%choice%"=="4" (
    set MODEL=ViT-L-14
    set PRETRAINED=dfn2b
)

if not defined MODEL (
    echo [错误] 无效选择
    pause
    exit /b 1
)

echo.
echo [检测] 网络环境...

REM 检测能否连接 HuggingFace
curl -s --connect-timeout 3 https://huggingface.co >nul 2>&1
if %errorlevel% equ 0 (
    echo [✓] 可直连 HuggingFace
    set HF_ENDPOINT=
) else (
    echo [⚠] 无法直连，使用国内镜像 hf-mirror.com
    set HF_ENDPOINT=https://hf-mirror.com
)

echo.
echo [下载] 模型: %MODEL% (%PRETRAINED%)
echo [提示] 首次下载需要时间，请耐心等待...
echo.

REM 激活虚拟环境（如果存在）
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

python -c "import open_clip; model, _, preprocess = open_clip.create_model_and_transforms('%MODEL%', pretrained='%PRETRAINED%'); print('[✓] 下载完成')"

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo   下载成功
    echo ========================================
    echo.
    echo 模型已缓存到: %%USERPROFILE%%\.cache\huggingface
    echo 重启 imgsearch 后可在设置中切换使用
    echo.
) else (
    echo.
    echo [错误] 下载失败，请检查网络连接
    echo.
)

pause
