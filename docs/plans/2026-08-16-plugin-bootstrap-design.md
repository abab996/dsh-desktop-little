# DSH Desktop 插件自动引导设计（2026-08-16）

## 背景与目标

dsh-desktop 是 DeepSeek Harness 的桌面启动器（Python + pywebview）。当前它只负责「装 DSH 本体 → 启动服务 → 开窗口」，不管理任何插件。

本次改造目标：每次启动桌面端时，按顺序自动保证运行环境与两个插件就绪：

1. **Node.js**（含 npm）缺失 → 自动安装（双选项交互）
2. **DSH 本体**（`@deepseek-ai/dsh`）缺失 → 自动安装（现有逻辑）
3. **dsh-remote-gateway 插件**（手机远程访问）缺失 → 自动安装
4. **dsh-market 插件**（DSH 内置插件市场，包名 `dshmarket`）缺失 → 自动安装

顺序严格：Node.js → DSH → 插件（插件安装依赖 pnpm，pnpm 依赖 Node.js；`dsh plugin` 依赖 DSH CLI）。

## 现状分析（dsh_launcher.py，250 行）

- 启动链：`main()` → `is_dsh_installed()` 分支
  - 已装：`prepare_server()`（HTTP GET / 探测 `is_server_up()`，未起则 `start_server()` 子进程 `dsh web --host 127.0.0.1 --port 3080`）→ `webview.create_window(URL)` → `webview.start()`
  - 未装：弹 `INSTALLING_HTML` 小窗（460×320）→ 后台线程 `install_dsh()`（`npm install -g @deepseek-ai/dsh`，900s 超时）→ `prepare_server()` → `window.evaluate_js` 跳转 URL
- 退出清理：`_started_by_us` 为真时 `taskkill /F /T` 杀进程树；复用已有实例则不动
- 无配置文件；唯一配置是环境变量 `DSH_HOST` / `DSH_PORT`
- 无任何插件管理逻辑（本次为全新功能）

## 目标启动流程

```
main()
├─ 第 1 步【新增】is_node_installed() 检查 node + npm
│    └─ 未装 → Node.js 安装窗（双选项交互，见下）→ 装好后继续
├─ 第 2 步：is_dsh_installed()（现有逻辑，依赖 Node.js 就绪）
│    └─ 未装 → INSTALLING_HTML 窗 → npm install -g @deepseek-ai/dsh
├─ 第 3 步【新增】插件检查与安装（DSH 就绪后）
│    ├─ 检测：~/.dsh/profiles/web/package.json dependencies 是否含
│    │        dsh-remote-gateway、dshmarket
│    ├─ 未装 → 插件安装窗（进度/失败可跳过）→ 逐个安装
│    └─ 失败 → 窗口内提示，可选「重试」或「仍然继续」
├─ 第 4 步：prepare_server()（现有，启动 dsh web）
└─ 第 5 步：create_window 打开界面（现有）
```

采用「先装后启」：插件在服务启动前装好，装完直接启动服务，无需额外重启动作。

## 第 1 步：Node.js 检测与安装

### 检测

```python
def is_node_installed():
    return bool(shutil.which("node")) and bool(shutil.which("npm") or shutil.which("npm.cmd"))
```

### 双选项安装窗（用户指定交互）

`webview.create_window(APP_NAME, html=NODE_INSTALL_HTML, width=520, height=400, resizable=False)`

窗口内两个按钮：

1. **「用 winget 自动安装」**
   - 执行 `winget install OpenJS.NodeJS.LTS --silent --accept-package-agreements --accept-source-agreements`
   - 后台子进程 + 超时管理；期间窗口显示进度文案
   - 完成后重新检测 node/npm；失败则窗口内提示错误 + 允许重试或切到 MSI 路径
   - winget 不可用（`shutil.which("winget")` 为空）时该按钮禁用并说明

2. **「手动安装 (MSI)」**
   - 用 `webbrowser.open("https://nodejs.org")` 打开官网
   - 用户安装完成后回到窗口点击「我已安装」按钮
   - 程序自动检测 node/npm：通过 → 继续后续流程；未通过 → 窗口内提示「未检测到 Node.js，请确认安装完成」+ 允许重试或切换到 winget 路径
   - 期间可随时点击 winget 按钮切换

安装窗关闭后回到主流程第 2 步。整个安装交互期间 GUI 事件循环运行（`webview.start(callback)` 模式，回调在后台线程）。

### 实现要点

- 新增 `NODE_INSTALL_HTML`（样式复用 `INSTALLING_HTML` 的深色主题）+ 按钮样式
- 窗口交互通过 `window.evaluate_js` 注入/更新 DOM；按钮点击后由 Python 侧轮询检测结果并更新文案
- 需要一个「等待用户操作」的同步机制：后台线程用 `threading.Event` 等待用户点「我已安装」或 winget 完成
- Node.js 安装失败属于**硬阻塞**（后续 DSH 安装依赖 npm）→ 不提供「跳过」，只能重试或关闭窗口退出程序

## 第 2 步：DSH 本体（现有逻辑，不动）

仅前置条件变为「Node.js 已就绪」。

## 第 3 步：插件检查与安装（全新）

### 检测（profile = web，与 `dsh web` 一致）

```python
PROFILE_DIR = os.path.join(os.environ.get("DSH_HOME") or os.path.expanduser("~/.dsh"), "profiles", "web")

def is_plugin_installed(pkg_name):
    pkg_json = os.path.join(PROFILE_DIR, "package.json")
    if not os.path.exists(pkg_json):
        return False
    deps = json.load(open(pkg_json)).get("dependencies", {})
    return pkg_name in deps
```

检查两个包名：`dsh-remote-gateway`、`dshmarket`。

### 安装子流程（顺序执行，逐个）

1. **确保 pnpm**：`shutil.which("pnpm")` 为空 → `npm install -g pnpm`（900s 超时，失败抛错）
2. **安装 dsh-remote-gateway**：
   - 执行 `dsh plugin --profile web add github:Yari-tuber/dsh-remote-gateway`
   - git 托管依赖需要 allowBuilds（pnpm ≥10 默认禁止 prepare 构建脚本）：
     - 首次 add 失败且错误输出含 `allowBuilds` 字样 → 读取/创建 `PROFILE_DIR/pnpm-workspace.yaml`，在 `allowBuilds:` 段加入 `dsh-remote-gateway: true`（不存在则追加整个段），再重试一次
   - 重试仍失败 → 抛错
3. **安装 dshmarket**：`dsh plugin --profile web add dshmarket`（npm registry 包，无 git 前置；同样处理 allowBuilds 重试）
4. **验证**：重新读 `package.json`，确认两个包都在 dependencies
5. **失败处理**（用户已确认「可跳过」策略）：窗口内显示错误详情 + 「重试」/「仍然继续」按钮；「仍然继续」直接进入第 4 步启动服务（本地功能不受影响，仅远程访问/插件市场不可用）

### 插件安装窗

- 复用 `INSTALLING_HTML` 风格，新增进度文案区与按钮
- 标题：「正在安装远程访问组件…」/「正在安装插件市场…」
- 窗口 520×400，不可缩放

### 前置条件（自动安装的硬依赖）

| 依赖 | 缺失后果 | 处理 |
|---|---|---|
| pnpm | 插件安装无法执行 | 自动 `npm install -g pnpm` |
| git | dsh-remote-gateway（git 依赖）安装失败 | 安装窗内提示「需要 git」，可跳过继续（远程访问不可用）；dshmarket 走 npm registry 不受影响 |
| 网络 | 安装失败 | 可重试/跳过 |

## 安全与边界

- 只在服务启动前动 profile；插件装失败绝不阻塞本地主功能（可跳过）
- 检测基于本地文件（package.json），不额外查询远端
- 不修改 DSH 主服务监听地址（必须保持 127.0.0.1，见 dsh-remote-gateway 的 README 警告）
- 所有子进程沿用现有 `_NO_WINDOW` / 超时 / 日志模式

## 错误处理汇总

| 场景 | 行为 |
|---|---|
| Node.js 未装且安装失败 | 硬阻塞：窗口内提示，可重试/切 winget；关闭窗口 = 退出 |
| DSH 未装且安装失败 | 现有 `_show_install_failure`（窗口内错误 + 弹窗） |
| 插件安装失败 | 窗口内错误详情 + 重试/仍然继续 |
| 服务启动超时 | 现有逻辑（stop_server + 报错） |

## 测试计划

1. 单元级：`is_node_installed` / `is_plugin_installed` 用临时 `DSH_HOME` 目录 + 伪造 package.json 验证
2. `is_plugin_installed`：无 profile / 空 dependencies / 含包名 三种情况
3. pnpm-workspace.yaml 的 allowBuilds 追加逻辑（新建文件 / 已有其他段 / 已含该包）
4. 手动冒烟：真实机器上删掉 profile 里的插件 → 启动桌面端 → 观察自动安装 → 打开设置确认「远程访问」「插件市场」两个入口
5. 回归：DSH 已装 + 插件已装 → 正常直接进主界面（无安装窗）

## 涉及文件

- `dsh_launcher.py`（唯一改动文件）
- `docs/plans/2026-08-16-plugin-bootstrap-design.md`（本文档）
- README.md（可选：补充说明自动安装行为）
