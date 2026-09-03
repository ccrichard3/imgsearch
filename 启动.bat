@echo off
chcp 65001 >nul
title imgsearch 图片搜索服务

cd /d "%~dp0"

echo ======================================
echo   imgsearch 本地图片搜索
echo ======================================
echo.

REM 检查 Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.11+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 首次运行：创建虚拟环境并安装依赖
if not exist .venv (
    echo [首次运行] 正在创建虚拟环境...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [错误] 创建虚拟环境失败
        pause
        exit /b 1
    )

    echo [首次运行] 正在安装依赖（需 3-5 分钟）...
    call .venv\Scripts\activate
    python -m pip install --upgrade pip >nul
    pip install -r requirements-windows.txt
    if %errorlevel% neq 0 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
    echo.
    echo [完成] 环境配置完成
    echo.
)

REM 激活虚拟环境
call .venv\Scripts\activate

REM 配置 HuggingFace 镜像（国内加速）
set HF_ENDPOINT=https://hf-mirror.com

REM 启动服务
echo [启动] 正在启动服务...
echo [提示] 首次启动需下载模型（~2GB），请耐心等待
echo [提示] 浏览器将自动打开，或手动访问 http://127.0.0.1:57860
echo.

python gui.py

REM 异常退出时暂停
if %errorlevel% neq 0 (
    echo.
    echo [错误] 服务异常退出，错误码: %errorlevel%
    pause
)
