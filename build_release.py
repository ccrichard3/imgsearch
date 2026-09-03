#!/usr/bin/env python3
"""
构建跨平台 Release 包
"""
import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path

def run(cmd):
    print(f"$ {cmd}")
    subprocess.run(cmd, shell=True, check=True)

def build_pyinstaller():
    """使用 PyInstaller 打包当前平台"""
    system = platform.system()
    machine = platform.machine()

    # 清理旧文件
    shutil.rmtree("build", ignore_errors=True)
    shutil.rmtree("dist/imgsearch", ignore_errors=True)

    print(f"\n🔨 构建 {system} {machine} 版本...")

    # PyInstaller 配置 - 精简打包，避免超过 2GB
    run(f"""pyinstaller --clean --noconfirm \
        --name imgsearch-minimal \
        --add-data "templates:templates" \
        --add-data "static:static" \
        --hidden-import open_clip \
        --hidden-import torch \
        --hidden-import torchvision \
        --hidden-import PIL \
        --hidden-import flask \
        --hidden-import flask_cors \
        --collect-submodules open_clip \
        --copy-metadata torch \
        --copy-metadata torchvision \
        --copy-metadata open-clip-torch \
        --exclude-module matplotlib \
        --exclude-module IPython \
        --exclude-module jupyter \
        --exclude-module notebook \
        --exclude-module pandas \
        --exclude-module scipy \
        --exclude-module pytest \
        app.py""")

    # 下载内置模型到 dist
    print("\n📦 下载内置模型...")
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

    download_script = """
import open_clip
model, _, preprocess = open_clip.create_model_and_transforms(
    'ViT-B-32', pretrained='laion2b_s34b_b79k'
)
print('✓ ViT-B-32 模型已缓存')
"""

    with open("_download_model.py", "w") as f:
        f.write(download_script)

    run("python _download_model.py")
    os.remove("_download_model.py")

    # 打包
    dist_name = f"imgsearch-minimal-{system}-{machine}"
    output_dir = f"dist/{dist_name}"

    os.rename("dist/imgsearch-minimal", output_dir)

    # 添加启动脚本
    if system == "Darwin" or system == "Linux":
        run_script = f"""{output_dir}/run.sh"""
        with open(run_script, "w") as f:
            f.write("#!/bin/bash\n")
            f.write(f'cd "$(dirname "$0")"\n')
            f.write("./imgsearch-minimal\n")
        os.chmod(run_script, 0o755)

    # 添加 README
    with open(f"{output_dir}/README.txt", "w") as f:
        f.write(f"imgsearch v1.0.0-minimal - {system} {machine}\n\n")
        if system == "Windows":
            f.write("双击 imgsearch-minimal.exe 启动\n")
        else:
            f.write("运行: ./run.sh\n")
        f.write("访问: http://localhost:57860\n\n")
        f.write("首次启动会初始化模型，稍等片刻\n")

    # 压缩
    print(f"\n📦 压缩...")
    if system == "Windows":
        archive = f"{dist_name}.zip"
        shutil.make_archive(f"dist/{dist_name}", "zip", "dist", dist_name)
    else:
        archive = f"{dist_name}.tar.gz"
        run(f"cd dist && tar -czf {archive} {dist_name}")

    final_path = Path("dist") / archive
    size_mb = final_path.stat().st_size / 1024 / 1024

    print(f"\n✅ 构建完成: {final_path} ({size_mb:.1f} MB)")
    return final_path

if __name__ == "__main__":
    build_pyinstaller()
