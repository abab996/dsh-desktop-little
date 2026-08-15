# DeepSeek Harness 桌面版（DSH Desktop）

把 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) 的 Web UI 封装成**原生桌面应用**的启动器。双击即可使用，无需再手动敲命令行。

## ✨ 功能

- **自动安装**：启动时自动检测 DeepSeek Harness（`dsh`）是否已安装，未安装则先弹出「正在安装」窗口，执行 `npm install -g @deepseek-ai/dsh`，安装完成后再启动主界面。
- **一键启动**：自动拉起 `dsh web` 后端服务，并用 [pywebview](https://pywebview.flowrl.com/)（Windows 下基于 WebView2）以原生窗口加载 Web UI，体验接近桌面软件。
- **智能复用**：若检测到 DSH 已在运行（默认 `127.0.0.1:3080`），直接复用，不重复启动。
- **自动清理**：关闭窗口后，自动结束由本程序启动的后端进程（复用已有实例时则不影响它）。
- **官方鲸鱼图标**：内置圆角鲸鱼图标（取自官方 `favicon.svg`）。

## 📦 使用

### 方式一：直接运行 exe（推荐）

从 [Releases](../../releases) 下载 `DeepSeekHarness.exe`，双击运行即可。

> 前置条件：本机已安装 Node.js（含 `npm`）。首次启动会自动安装 `@deepseek-ai/dsh`（`dsh` 命令）。
> 后端日志写入 `%LOCALAPPDATA%\DeepSeekHarness\dsh-web.log`。

### 方式二：Python 源码运行

需要 Python 3.10+ 与 Node.js（含 `npm`，首次运行会自动安装 `dsh`）：

```bash
pip install -r requirements.txt
python dsh_launcher.py
```

Windows 下也可直接双击 `run.bat` 测试，支持指定端口：`run.bat 3090`。

## 🔨 构建 exe

**方式一：双击 `build.bat`（推荐）**——一键检查 Python/依赖，若检测到桌面版正在运行会提示是否先关闭（避免 exe 被占用导致打包失败），完成后输出 `dist\DeepSeekHarness.exe`。

**方式二：PowerShell 手动打包**

```powershell
pip install -r requirements.txt
.\build.ps1
```

产物输出到 `dist\DeepSeekHarness.exe`（PyInstaller 单文件、无控制台窗口、带鲸鱼图标）。

## ⚙️ 配置

可通过环境变量覆盖后端地址：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DSH_HOST` | `127.0.0.1` | DSH 后端绑定地址 |
| `DSH_PORT` | `3080` | DSH 后端端口 |

## 📁 项目结构

```
.
├── dsh_launcher.py       # 启动器主脚本
├── build.ps1             # 一键打包脚本
├── make_icon.py          # SVG 路径解析 + 鲸鱼蒙版渲染
├── make_icon_final.py    # 生成圆角图标 icon.png / icon.ico
├── favicon.svg           # 官方鲸鱼图标源文件
├── icon.png / icon.ico   # 圆角鲸鱼图标（16–256px）
└── requirements.txt      # 依赖
```

## 🖼️ 图标

图标为官方 DeepSeek Harness 的黑色鲸鱼 logo，透明底、圆角（squircle）裁剪。若需调整样式（如更换底色、颜色），修改 `make_icon_final.py` 后运行：

```bash
python make_icon_final.py
```

## 📄 许可证

[MIT](LICENSE)。DeepSeek Harness 本身版权归其作者所有。
