# imgsearch 迁移到其它设备

核心事实：这套程序 = **代码**（几十 KB）+ **依赖**（torch/transformers 等，按平台/架构不同）+ **模型权重缓存**（约 1.4 GB）+ **你的索引**（`~/.imgsearch`）。
其中「代码 / 模型缓存 / 索引」是跨平台可直接拷贝的；只有「依赖（torch 等）」必须按目标平台重装或重新打包——**没有一个包能通吃所有系统**。

下面按目标设备给方案。

---

## 可直接拷贝的「数据」（所有方案通用，省去重新下载/重建）

| 内容 | 路径 | 作用 |
|---|---|---|
| 程序代码 | `/Users/cc/程序/imgsearch`（除 `.venv/`） | 主程序 |
| 模型权重缓存 | `~/.cache/huggingface/hub/models--timm--ViT-B-16-SigLIP2-256` | 免联网重下（1.4G） |
| 模型（手动目录，二选一） | `~/.imgsearch/models/ViT-B-16-SigLIP2-256/` | 手动放模型时用，见下节 |
| 索引 + 配置 | `~/.imgsearch/` | 免重建索引；含库目录列表、缩略图 |

> 注意：`~/.imgsearch/config.json` 里的 `roots` 是**绝对路径**。换机后若图库路径变了，进设置删掉旧的、加新的即可。
> 索引缓存 `cache__*.pkl` 里也存了绝对路径——图库路径变化后需要重建索引。

---

## ★ 手动下载模型（免联网 / 网络受限首选）

模型较大（默认档权重 1.4 GB），或目标机连不上 HuggingFace（如国内网络、之前的 `503` 报错），
可以**手动下载模型文件**放进程序会自动识别的目录，全程免联网。放好后启动即用，无需 HF 缓存那套结构。

### 需要哪些文件（默认档 SigLIP2-B = `ViT-B-16-SigLIP2-256`）

| 文件 | 大小 | 作用 |
|---|---|---|
| `open_clip_model.safetensors` | ~1.4 GB | 模型权重（**必需**） |
| `tokenizer.json` | ~33 MB | **文字**搜图需要 |
| `tokenizer_config.json` | ~48 KB | **文字**搜图需要 |
| `special_tokens_map.json` | ~4 KB | **文字**搜图需要 |

> 只用「以图搜图」的话，其实只要 `open_clip_model.safetensors` 一个文件；要「文字搜图」则四个都放。

### 从哪里下载

- 官方页面：<https://huggingface.co/timm/ViT-B-16-SigLIP2-256/tree/main>
- 直链（右键另存 / wget / aria2）：`https://huggingface.co/timm/ViT-B-16-SigLIP2-256/resolve/main/<文件名>`
- **国内 / HF 打不开**：把域名换成镜像 `hf-mirror.com` 即可。

在任意能联网的机器上批量下载：
```bash
BASE=https://hf-mirror.com/timm/ViT-B-16-SigLIP2-256/resolve/main   # 能直连HF就把域名换回 huggingface.co
for f in open_clip_model.safetensors tokenizer.json tokenizer_config.json special_tokens_map.json; do
  curl -L -o "$f" "$BASE/$f"
done
```

### 放到哪个文件夹

放进以下**任一**目录（程序按此顺序查找），目录名必须是模型名 `ViT-B-16-SigLIP2-256`：

1. `~/.imgsearch/models/ViT-B-16-SigLIP2-256/`  ← **推荐**
2. `<程序目录>/models/ViT-B-16-SigLIP2-256/`（想跟程序一起迁移时）
3. `$IMGSEARCH_MODELS/ViT-B-16-SigLIP2-256/`（设了该环境变量时，优先级最高）

最终结构：
```
~/.imgsearch/models/ViT-B-16-SigLIP2-256/
├── open_clip_model.safetensors
├── tokenizer.json
├── tokenizer_config.json
└── special_tokens_map.json
```

启动程序即自动从该目录本地加载，全程不联网。

### 其它模型档的仓库名（要换模型时）

目录名 = 设置里模型的开发名（括号前那串）；下载仓库对应关系：

| 设置里的档位 | 目录名 / 下载仓库 | tokenizer |
|---|---|---|
| SigLIP2-B（默认） | `timm/ViT-B-16-SigLIP2-256` | 需要上面 3 个 tokenizer 文件 |
| SigLIP2-L | `timm/ViT-L-16-SigLIP2-384` | 同上 |
| SigLIP2-SO400M | `timm/ViT-SO400M-16-SigLIP2-384` | 同上 |
| CLIP ViT-L-14 | 仓库不同（apple/DFN 系），只需权重 | 内置，无需额外文件 |
| CLIP ViT-B-32 | 仓库不同（laion 系），只需权重 | 内置，无需额外文件 |

> 两个 CLIP 档用的是内置 BPE 分词器，手动放模型时**只需权重文件**、不需要 tokenizer 文件；但它们的权重仓库与 timm 不同，要换这两档再单独问我给链接。

---

## 方案 A：另一台 Apple Silicon Mac（M1/M2/M3/M4）

### A1. 目标机有/可装 Python（最简单）
1. 拷贝 `imgsearch` 文件夹（不含 `.venv`）。
2. 装 Homebrew + `brew install python@3.11`。
3. 双击 `run.command`：自动建 venv、装依赖、启动。
4. （可选）先把上面「模型缓存 + 索引」拷过去，免联网、免重建。

### A2. 目标机**没有也不想装** Python → 打独立包（免环境）
在**当前这台 Apple Silicon Mac** 上执行：
```bash
cd /Users/cc/程序/imgsearch
./build_standalone.sh
```
产出 `dist/imgsearch/`（自带 Python 运行时 + torch + 所有依赖，约 3–4 GB）。
把整个 `dist/imgsearch/` 目录拷到目标机，运行里面的 `imgsearch` 可执行文件即可，**目标机无需任何 Python**。
模型权重仍建议一并拷 `~/.cache/huggingface`（或首次联网自动下）。

> Apple Silicon 打的包**只能给 Apple Silicon**；Intel Mac 见方案 B。

---

## 方案 B：Intel Mac
架构不同，torch 二进制不一样，**不能用 Apple Silicon 的包/venv**。
- 在一台 Intel Mac 上按 A1 重建 venv（`brew install python@3.11` → `run.command`），或按 A2 在 Intel Mac 上 `./build_standalone.sh` 打 Intel 版包。
- 无 MPS，走 CPU，速度慢些；建议默认用最轻的 `CLIP ViT-B-32` 档。
- 模型缓存 / 索引可直接拷。

---

## 方案 C：Windows
代码本身跨平台（FastAPI + 纯 JS 前端），但需要 Windows 版 torch，且要在 **Windows 上**安装/打包（不能从 Mac 交叉打包）。
1. 装 Python 3.11（勾选 Add to PATH）。
2. 拷贝 `imgsearch` 文件夹，命令行：
   ```
   py -3.11 -m venv .venv
   .venv\Scripts\python -m pip install -r requirements.txt
   .venv\Scripts\python gui.py
   ```
   然后浏览器开 `http://127.0.0.1:57860`。
3. 免 Python 版：在 Windows 上 `pip install pyinstaller` 后用与 `build_standalone.sh` 相同的参数打 `.exe`（`--add-data "web;web"` 注意 Windows 用分号）。
4. 模型缓存放 `%USERPROFILE%\.cache\huggingface`，索引放 `%USERPROFILE%\.imgsearch`。

> 小提示：`app.py` 的「在访达中显示」在 Windows 上目前走 `xdg-open` 分支不生效，需要加一条 `explorer /select,` 分支（要的话我来加）。

---

## 方案 D：另一台 NAS / Linux 服务器
1. 该机装 Python 3.11 + `pip install -r requirements.txt`（x86 或 arm 各装各的 torch，pip 会自动选）。
2. `python gui.py`，浏览器通过局域网 IP 访问 `http://<NAS_IP>:57860`。
   - 默认只监听 `127.0.0.1`；要局域网访问，把 `gui.py` 末尾 `host="127.0.0.1"` 改成 `host="0.0.0.0"`。
3. 无桌面环境时「在访达中显示 / 打开文件」不可用，但搜索照常。
4. GPU：有 NVIDIA 卡则自动走 CUDA，否则 CPU。

---

## 最省事的建议
- **同为 Apple Silicon Mac** → 方案 A2 打独立包，拷过去双击即用，最省心。
- **跨平台（Win / Intel / x86 NAS）** → 目标机各自装一次 Python 依赖（方案 C/D），把**模型缓存 + 索引**拷过去避免重下重建。
- 需要我帮你：① 生成 Windows 的「在访达中显示」分支；② 局域网访问开关；③ 调 PyInstaller 打包——说一声即可。
