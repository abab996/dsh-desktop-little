# -*- coding: utf-8 -*-
"""DeepSeek Harness 桌面启动器 (DSH Desktop Launcher)

功能：
1. 启动时按顺序三阶引导：Node.js → DeepSeek Harness（dsh）→ 插件；
2. Node.js 缺失时弹出双选项安装窗（winget 自动安装 / 手动安装 MSI）；
3. DSH 缺失时自动全局安装 @deepseek-ai/dsh；
4. 插件（dsh-remote-gateway、dshmarket）缺失时在服务启动前自动安装（失败可跳过）；
5. 启动（或复用）dsh web 后端服务；
6. 用 pywebview 以原生窗口加载 WebUI，实现桌面软件体验；
7. 窗口关闭时自动清理由本程序启动的后端进程。
"""

import os
import re
import sys
import time
import json
import shutil
import threading
import webbrowser
import subprocess
import urllib.request

APP_NAME = "DeepSeek Harness"
HOST = os.environ.get("DSH_HOST", "127.0.0.1")
PORT = int(os.environ.get("DSH_PORT", "3080"))
URL = "http://{host}:{port}".format(host=HOST, port=PORT)

IS_WIN = os.name == "nt"
_NO_WINDOW = {"creationflags": subprocess.CREATE_NO_WINDOW} if IS_WIN else {}

# 服务守护参数
WATCHDOG_POLL_SEC = 2          # 守护线程探测间隔
WATCHDOG_GRACE_SEC = 8         # 服务掉线后等待插件自行重启的宽限期
WATCHDOG_STARTUP_TIMEOUT_SEC = 60  # 守护拉起服务的就绪超时

# 后端进程状态（跨线程共享）
_proc = None
_started_by_us = False

# 插件配置：profile 固定为 web（与 `dsh web` 别名一致）
PROFILE_DIR = os.path.join(
    os.environ.get("DSH_HOME") or os.path.expanduser("~/.dsh"),
    "profiles", "web",
)
PLUGINS = ["dsh-remote-gateway", "dshmarket"]

INSTALLING_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
  html, body { margin: 0; height: 100%; }
  body {
    display: flex; align-items: center; justify-content: center;
    background: #101319; color: #e8eaed;
    font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif;
    user-select: none; overflow: hidden;
  }
  .box { text-align: center; padding: 32px; }
  .spinner {
    width: 52px; height: 52px; margin: 0 auto 22px;
    border: 4px solid rgba(255,255,255,.12);
    border-top-color: #4d6bfe; border-radius: 50%;
    animation: spin 0.9s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  h1 { font-size: 17px; font-weight: 600; margin: 0 0 10px; }
  p { font-size: 13px; color: #9aa0a6; margin: 0; line-height: 1.6; }
</style>
</head>
<body>
  <div class="box">
    <div class="spinner"></div>
    <h1>正在安装 DeepSeek Harness</h1>
    <p>首次启动需要安装 dsh 命令，请稍候…</p>
  </div>
</body>
</html>"""

# Node.js 安装窗：深色主题（复用 INSTALLING_HTML 配色），双选项交互
NODE_INSTALL_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
  html, body { margin: 0; height: 100%; }
  body {
    display: flex; align-items: center; justify-content: center;
    background: #101319; color: #e8eaed;
    font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif;
    user-select: none; overflow: hidden;
  }
  .box { width: 440px; text-align: center; padding: 24px; }
  h1 { font-size: 17px; font-weight: 600; margin: 0 0 10px; }
  #status { font-size: 13px; color: #9aa0a6; margin: 0 0 20px; line-height: 1.6; min-height: 20px; }
  .btns { display: flex; flex-direction: column; gap: 10px; }
  .btn {
    display: block; width: 100%; padding: 11px 0;
    background: #23262e; color: #e8eaed; border: 1px solid #3a3f4b;
    border-radius: 8px; font-size: 14px; cursor: pointer;
    font-family: inherit;
  }
  .btn:hover:not(:disabled) { background: #2b2f39; }
  .btn:disabled { opacity: .45; cursor: not-allowed; }
  .btn.primary { background: #4d6bfe; border-color: #4d6bfe; font-weight: 600; }
  .btn.primary:hover:not(:disabled) { background: #5d78ff; }
  .spinner {
    width: 52px; height: 52px; margin: 0 auto 22px;
    border: 4px solid rgba(255,255,255,.12);
    border-top-color: #4d6bfe; border-radius: 50%;
    animation: spin 0.9s linear infinite;
  }
  .spinner.hidden { display: none; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .err { color: #e5484d; font-size: 13px; margin: 10px 0 0; white-space: pre-wrap; }
</style>
</head>
<body>
  <div class="box">
    <div class="spinner" id="spinner"></div>
    <h1>需要安装 Node.js</h1>
    <p id="status">DeepSeek Harness 依赖 Node.js 与 npm。请选择一种安装方式。</p>
    <div class="btns">
      <button class="btn primary" id="btn-winget">用 winget 自动安装</button>
      <button class="btn" id="btn-manual">手动安装 (MSI)</button>
      <button class="btn" id="btn-done" style="display:none">我已安装</button>
    </div>
    <div class="err" id="err"></div>
  </div>
</body>
</html>"""

# 插件安装窗：深色主题，进度文案 + 重试/仍然继续
PLUGIN_INSTALL_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
  html, body { margin: 0; height: 100%; }
  body {
    display: flex; align-items: center; justify-content: center;
    background: #101319; color: #e8eaed;
    font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif;
    user-select: none; overflow: hidden;
  }
  .box { width: 440px; text-align: center; padding: 24px; }
  h1 { font-size: 17px; font-weight: 600; margin: 0 0 10px; }
  #status { font-size: 13px; color: #9aa0a6; margin: 0 0 20px; line-height: 1.6; min-height: 20px;
            white-space: pre-wrap; }
  .btns { display: flex; flex-direction: column; gap: 10px; }
  .btn {
    display: block; width: 100%; padding: 11px 0;
    background: #23262e; color: #e8eaed; border: 1px solid #3a3f4b;
    border-radius: 8px; font-size: 14px; cursor: pointer;
    font-family: inherit;
  }
  .btn:hover:not(:disabled) { background: #2b2f39; }
  .btn.primary { background: #4d6bfe; border-color: #4d6bfe; font-weight: 600; }
  .btn.primary:hover:not(:disabled) { background: #5d78ff; }
  .btn:disabled { opacity: .45; cursor: not-allowed; }
  .spinner {
    width: 52px; height: 52px; margin: 0 auto 22px;
    border: 4px solid rgba(255,255,255,.12);
    border-top-color: #4d6bfe; border-radius: 50%;
    animation: spin 0.9s linear infinite;
  }
  .spinner.hidden { display: none; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .err { color: #e5484d; font-size: 12px; margin: 10px 0 0; white-space: pre-wrap; text-align: left; }
</style>
</head>
<body>
  <div class="box">
    <div class="spinner" id="spinner"></div>
    <h1 id="title">正在安装插件…</h1>
    <p id="status">请稍候…</p>
    <div class="btns" id="btns" style="display:none">
      <button class="btn primary" id="btn-retry">重试</button>
      <button class="btn" id="btn-continue">仍然继续</button>
    </div>
    <div class="err" id="err"></div>
  </div>
</body>
</html>"""


def log_dir():
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "DeepSeekHarness")
    os.makedirs(d, exist_ok=True)
    return d


def _detect_node():
    """检测 Node.js 与 npm 是否可用，并返回需要前插到 PATH 的目录。

    返回 (installed, dirs_to_prepend)：
      - installed：node 与 npm 是否同时可用；
      - dirs_to_prepend：新探测到的 node/npm 所在目录（通常为空，仅在
        winget 等安装后本进程 PATH 快照未刷新、通过常见安装目录兜底命中的
        场景非空），供调用方前插到 os.environ["PATH"]，使后续 resolve_dsh /
        install_dsh 也能找到 npm。

    探测顺序：先查 PATH（shutil.which，覆盖任何已加入 PATH 的安装），再兜底
    探测各平台 Node 常见安装目录（因为子进程安装后当前进程的 PATH 快照不会
    自动刷新）。
    """
    node_candidates = [shutil.which("node")]
    npm_candidates = [shutil.which("npm") or shutil.which("npm.cmd")]
    # 常见安装目录兜底（Windows：Program Files / LocalAppData；类 Unix：/usr/bin、/usr/local/bin 等由 which 覆盖）
    if IS_WIN:
        prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        local = os.environ.get("LOCALAPPDATA", "")
        win_dirs = [prog_files]
        if local:
            win_dirs.append(os.path.join(local, "Programs"))
        for d in win_dirs:
            nd = os.path.join(d, "nodejs", "node.exe")
            npmd = os.path.join(d, "nodejs", "npm.cmd")
            if os.path.exists(nd):
                node_candidates.append(nd)
            if os.path.exists(npmd):
                npm_candidates.append(npmd)

    def _existing_nonempty(cands):
        return [c for c in cands if c]

    # 去重候选目录，作为需要前插到 PATH 的目录（仅对真实存在的文件取目录）
    found = {}
    for cand in node_candidates + npm_candidates:
        if cand and os.path.exists(cand):
            d = os.path.dirname(cand)
            found.setdefault(d, True)
    installed = bool(_existing_nonempty(node_candidates)) and bool(
        _existing_nonempty(npm_candidates)
    )
    return installed, list(found)


def is_node_installed():
    """检测 Node.js 与 npm 是否已安装。

    node 与 npm（或 npm.cmd）必须同时可用才视为已安装。仅探测、不修改 PATH。
    """
    installed, _ = _detect_node()
    return installed


def resolve_dsh():
    """返回用于启动 dsh 的命令前缀（不含子命令/参数）。"""
    dsh = shutil.which("dsh") or shutil.which("dsh.cmd")
    if dsh:
        if dsh.lower().endswith((".cmd", ".bat")):
            return ["cmd", "/c", dsh]
        return [dsh]
    npx = shutil.which("npx")
    if npx:
        return [npx, "--yes", "@deepseek-ai/dsh"]
    raise RuntimeError("未找到 dsh 命令，请安装 @deepseek-ai/dsh 或将其加入 PATH")


def is_dsh_installed():
    """检查 DeepSeek Harness（dsh）是否已安装。"""
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if npm:
        try:
            r = subprocess.run(
                [npm, "ls", "-g", "@deepseek-ai/dsh", "--depth=0"],
                capture_output=True, timeout=20, **_NO_WINDOW,
            )
            out = (r.stdout + r.stderr).decode("utf-8", "ignore")
            if r.returncode == 0 and "@deepseek-ai/dsh" in out:
                return True
        except Exception:
            pass
    # 兜底：dsh 已在 PATH 上（例如手动加入 PATH）
    if shutil.which("dsh") or shutil.which("dsh.cmd"):
        return True
    return False


def install_dsh():
    """全局安装 @deepseek-ai/dsh。"""
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm:
        raise RuntimeError("未找到 npm，无法安装 DeepSeek Harness。请先安装 Node.js。")
    r = subprocess.run(
        [npm, "install", "-g", "@deepseek-ai/dsh"],
        capture_output=True, timeout=900, **_NO_WINDOW,
    )
    if r.returncode != 0:
        err = (r.stderr or r.stdout).decode("utf-8", "ignore").strip()
        raise RuntimeError("安装 DeepSeek Harness 失败：\n" + (err or "未知错误"))


def is_plugin_installed(pkg_name):
    """检测插件是否已在 web profile 中真实安装。

    需同时满足：
      1. PROFILE_DIR/package.json 的 dependencies 里声明了该包；
      2. PROFILE_DIR/node_modules/<pkg_name> 目录真实存在（避免 add 只写
         package.json 但安装/链接失败的半途状态被误判为已安装）。
    仅做本地文件判断，不查询远端。
    """
    pkg_json = os.path.join(PROFILE_DIR, "package.json")
    declared = False
    if os.path.exists(pkg_json):
        try:
            with open(pkg_json, "r", encoding="utf-8") as f:
                deps = json.load(f).get("dependencies", {}) or {}
            declared = pkg_name in deps
        except Exception:
            declared = False
    if not declared:
        return False
    return os.path.isdir(os.path.join(PROFILE_DIR, "node_modules", pkg_name))


def ensure_pnpm():
    """确保 pnpm 可用：缺失时用 npm 全局安装 pnpm（900s 超时）。"""
    if shutil.which("pnpm"):
        return
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm:
        raise RuntimeError("未找到 npm，无法安装 pnpm。")
    r = subprocess.run(
        [npm, "install", "-g", "pnpm"],
        capture_output=True, timeout=900, **_NO_WINDOW,
    )
    if r.returncode != 0:
        err = (r.stderr or r.stdout).decode("utf-8", "ignore").strip()
        raise RuntimeError("安装 pnpm 失败：\n" + (err or "未知错误"))
    if not shutil.which("pnpm"):
        raise RuntimeError("pnpm 已安装但未出现在 PATH，请重启后重试。")


def _allow_builds_section():
    """返回 pnpm-workspace.yaml 中的 allowBuilds 配置段。

    若文件不存在或没有 allowBuilds 段则返回空 dict。返回 (path, dict)。
    """
    ws_path = os.path.join(PROFILE_DIR, "pnpm-workspace.yaml")
    allow = {}
    if os.path.exists(ws_path):
        section = None
        with open(ws_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.rstrip("\n")
                if line.strip().startswith("allowBuilds:") and not line.lstrip().startswith("-"):
                    section = line
                    continue
                if section is not None and line.strip() and not line[0].isspace():
                    section = None
                if section is not None and ":" in line:
                    # 键可能含 @https:// 等带冒号的来源 URL，必须从最右侧切分
                    key, _, value = line.rpartition(":")
                    key = key.strip()
                    if key and not key.startswith("-"):
                        allow[key] = value.strip()
    return ws_path, allow


def add_allow_build(name):
    """在 PROFILE_DIR/pnpm-workspace.yaml 中设置 allowBuilds.<name>: true。

    保留文件原有内容；无 allowBuilds 段则在文件末尾追加一个。返回是否发生改动。
    段的定位统一以「行首 allowBuilds:」为准，避免命中注释/值里的子串。

    注意：pnpm 在检测到被忽略的构建脚本时，会自动向 allowBuilds 写入占位值
    `set this to true or false`。这里必须把占位值覆盖为 true，而不能因为
    「键已存在」就跳过——否则重试安装仍会被 ERR_PNPM_IGNORED_BUILDS 拒绝。
    """
    ws_path = os.path.join(PROFILE_DIR, "pnpm-workspace.yaml")
    os.makedirs(PROFILE_DIR, exist_ok=True)
    if not os.path.exists(ws_path) or not open(ws_path, encoding="utf-8").read().strip():
        existing = "packages:\n  - '**'\n\n"
    else:
        with open(ws_path, "r", encoding="utf-8") as f:
            existing = f.read()
    entry = "  " + name + ": true"
    lines = existing.split("\n")
    # 定位「行首 allowBuilds:」段；没找到就整体追加一段
    section_idx = None
    for i, ln in enumerate(lines):
        ls = ln.rstrip()
        if ls.startswith("allowBuilds:") and not ls.lstrip().startswith("-"):
            section_idx = i
            break
    if section_idx is None:
        new_content = existing.rstrip("\n") + "\n\nallowBuilds:\n" + entry + "\n"
    else:
        # 在段内寻找同名键行（键可能含 @https:// 等带冒号的来源 URL，
        # 因此从最右侧切分冒号来取键名）
        key_line_idx = None
        last_idx = section_idx
        for j in range(section_idx + 1, len(lines)):
            cur = lines[j]
            stripped = cur.strip()
            if not stripped:
                continue
            if not (cur.startswith("  ") or cur.startswith("\t")):
                break
            last_idx = j
            k, _, v = cur.rpartition(":")
            if k.strip() == name:
                key_line_idx = j
                if v.strip() == "true":
                    # 已生效（true），无需改动
                    return False
        if key_line_idx is not None:
            # 已有该键但值不是 true（如 pnpm 写入的占位值）：覆盖为 true
            lines[key_line_idx] = entry
        else:
            # 段内没有该键：追加到最后一个缩进行之后
            lines.insert(last_idx + 1, entry)
        new_content = "\n".join(lines).rstrip("\n") + "\n"
    with open(ws_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    return True


def _parse_allow_build_key(out):
    """从 pnpm 的报错输出中解析它要求的精确 allowBuilds 键。

    pnpm 对 git 托管依赖（tarball 形式）要求「精确键」：包名@完整来源URL
    （例如 `dsh-remote-gateway@https://codeload.github.com/.../tar.gz/<commit>`），
    简单包名键对其无效（实测确认）。报错文本末尾带示例：

        For example:
        allowBuilds:
          dsh-remote-gateway@https://...: true

    解析失败返回 None，由调用方回退到简单包名键。
    """
    m = re.search(r"allowBuilds:\s*\r?\n\s+([^\r\n]+?):\s*true", out)
    if m:
        key = m.group(1).strip()
        if key and not key.endswith(":"):
            return key
    return None


def _dsh_plugin_add(pkg_spec):
    """执行 `dsh plugin --profile web add <spec>`；失败抛出 RuntimeError。

    首次失败且输出含 allowBuilds 字样时，从输出解析 pnpm 要求的精确键并写入
    pnpm-workspace.yaml 的 allowBuilds 段，然后重试一次。
    返回该次 add 子进程的输出文本。
    """
    cmd = resolve_dsh() + ["plugin", "--profile", "web", "add", pkg_spec]

    def _run():
        return subprocess.run(
            cmd, capture_output=True, timeout=900, **_NO_WINDOW,
        )

    r = _run()
    if r.returncode == 0:
        return (r.stdout + r.stderr).decode("utf-8", "ignore")
    out = (r.stdout + r.stderr).decode("utf-8", "ignore")
    if "allowBuilds" in out:
        # 优先用 pnpm 给出的精确键（git 依赖必需）；解析不到则回退简单包名键
        key = _parse_allow_build_key(out) or (pkg_spec.split("/")[-1] or pkg_spec)
        add_allow_build(key)
        r = _run()
        if r.returncode == 0:
            return (r.stdout + r.stderr).decode("utf-8", "ignore")
        out = (r.stdout + r.stderr).decode("utf-8", "ignore")
    raise RuntimeError(
        "安装插件 {} 失败：\n{}".format(pkg_spec, out.strip() or "未知错误")
    )


def install_plugins():
    """顺序安装 WebUI 所需的插件：先保证 pnpm，再装 dsh-remote-gateway 与 dshmarket。"""
    ensure_pnpm()
    # git 托管依赖（github:...）需要本机 git；缺失时给出明确错误提示（插件窗会显示
    # 「重试 / 仍然继续」，用户可选继续）。dshmarket 走 npm registry，不受 git 缺失影响。
    if not shutil.which("git"):
        raise RuntimeError(
            "安装插件需要 git（dsh-remote-gateway 是 git 依赖）。"
            "请安装 Git 后重试，或选择「仍然继续」（远程访问将不可用，插件市场不受影响）。"
        )
    _dsh_plugin_add("github:Yari-tuber/dsh-remote-gateway")
    _dsh_plugin_add("dshmarket")
    missing = [p for p in PLUGINS if not is_plugin_installed(p)]
    if missing:
        raise RuntimeError("安装后仍缺少插件：" + ", ".join(missing))


def is_server_up(timeout=1.5):
    try:
        with urllib.request.urlopen(URL + "/", timeout=timeout) as resp:
            return resp.status < 500
    except Exception:
        return False


# Windows 控制台相关常量（数值与 win32 一致，避免依赖 pywin32）
_CREATE_NEW_CONSOLE = 0x00000010
_STARTF_USESHOWWINDOW = 0x00000001
_SW_HIDE = 0


def _popen_hidden_console(cmd, **kwargs):
    """以「隐藏控制台」方式启动子进程（仅 Windows）。

    dsh web 必须以带控制台的方式运行：DSH 的 agent 执行 bash 等命令时，
    子进程会继承父进程的控制台（不弹窗）；若父进程无控制台（CREATE_NO_WINDOW），
    子进程会新建一个可见的终端窗口。用 CREATE_NEW_CONSOLE + SW_HIDE 让
    dsh web 拥有一个隐藏控制台，既满足继承需求又不打扰用户。
    """
    if not IS_WIN:
        return subprocess.Popen(cmd, **kwargs)
    si = subprocess.STARTUPINFO()
    si.dwFlags = _STARTF_USESHOWWINDOW
    si.wShowWindow = _SW_HIDE
    return subprocess.Popen(
        cmd, creationflags=_CREATE_NEW_CONSOLE, startupinfo=si, **kwargs
    )


def start_server(logfile):
    cmd = resolve_dsh() + ["web", "--host", HOST, "--port", str(PORT)]
    with open(logfile, "ab") as logf:
        return _popen_hidden_console(
            cmd, stdout=logf, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
        )


def wait_until_up(timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_server_up():
            return True
        time.sleep(0.3)
    return False


def stop_server(proc):
    if proc is None:
        return
    try:
        if IS_WIN:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True, **_NO_WINDOW,
            )
        else:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
    except Exception:
        pass


def show_error(msg):
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, msg, APP_NAME, 0x10)
    except Exception:
        print(msg, file=sys.stderr)


def prepare_server(logfile):
    """确保后端已启动（必要时启动）。"""
    global _proc, _started_by_us
    if is_server_up():
        return
    _proc = start_server(logfile)
    _started_by_us = True
    if not wait_until_up():
        stop_server(_proc)
        _proc = None
        _started_by_us = False
        raise RuntimeError("DSH WebUI 启动超时，请查看日志：\n" + logfile)


def _show_install_failure(window, exc):
    msg = str(exc)
    updated = False
    try:
        # 错误文本是不可信输入：用 textContent 强制作为纯文本插入，绝不当作 HTML 解析
        window.evaluate_js(
            "document.body.innerHTML = "
            "'<div style=\"padding:40px;text-align:center;font-family:Segoe UI,Microsoft YaHei,sans-serif;\">"
            "<h2 style=\"color:#e5484d;font-size:18px;margin:0 0 16px;\">安装失败</h2>"
            "<pre id=\"dsh-err\" style=\"white-space:pre-wrap;font-size:12px;color:#9aa0a6;text-align:left;\"></pre>"
            "</div>';"
            "document.getElementById('dsh-err').textContent = " + json.dumps(msg) + ";"
        )
        updated = True
    except Exception:
        pass
    if not updated:
        show_error("DeepSeek Harness 安装失败：\n" + msg)



# ────────────── 启动引导窗（单窗口顺序切换） ──────────────
#
# 由于 pywebview 6.x 不支持反复调用 webview.start()，也不存在 webview.stop()，
# 所有阶段（Node.js → DSH → 插件 → 服务 → 主界面）都在**唯一一次**
# webview.start(_bootstrap, ...) 会话中完成：后台 _bootstrap 线程用同一个
# 引导窗口 window.load_html() 依次切换安装界面，最后新建主窗口并销毁引导窗。
# 若用户中途关闭引导窗（窗口数归零），webview.start() 返回、程序退出——这正是
# Node.js 硬阻塞期望的「不提供跳过」。


def _js_eval_safe(window, js):
    """静默执行一段 JS（忽略错误，避免窗口关闭后抛异常）。"""
    if window is None:
        return
    try:
        window.evaluate_js(js)
    except Exception:
        pass


class _BootApi:
    """引导窗的 js_api：同一窗口顺序承载不同阶段的按钮交互。

    各阶段按钮按名称区分，全部集中在此，通过事件与后台 _bootstrap 线程同步：
      - Node.js 阶段：use_winget / use_manual / already_installed → node_ready
      - 插件阶段：retry / continue_boot → plugin_retry / plugin_continue
    """

    def __init__(self):
        self.node_ready = threading.Event()
        self.plugin_retry = threading.Event()
        self.plugin_continue = threading.Event()
        self._winget_active = False

    # ---- 窗口定位（js_api 需找到承载自己的窗口才能 evaluate_js） ----
    def _window(self):
        import webview
        return next(
            (w for w in webview.windows if getattr(w, "js_api", None) is self), None
        )

    # ---- 通用窗口更新辅助 ----
    def _status(self, text):
        _js_eval_safe(self._window(), "document.getElementById('status').textContent=" + json.dumps(text) + ";")

    def _error(self, text):
        _js_eval_safe(self._window(), "document.getElementById('err').textContent=" + json.dumps(text) + ";")

    def _hide_spinner(self, hide):
        w = self._window()
        cls = "'spinner hidden'" if hide else "'spinner'"
        _js_eval_safe(w, "document.getElementById('spinner').className=" + cls + ";")

    def _show_done_btn(self, show):
        w = self._window()
        _js_eval_safe(w, "document.getElementById('btn-done').style.display=" + ("'block'" if show else "'none'") + ";")

    def _set_node_buttons(self, winget_disabled):
        w = self._window()
        _js_eval_safe(
            w,
            "document.getElementById('btn-winget').disabled=" + ("true" if winget_disabled else "false") + ";"
            "document.getElementById('btn-manual').disabled=false;"
            "document.getElementById('btn-done').style.display='none';",
        )

    def _show_plugin_buttons(self, show):
        w = self._window()
        _js_eval_safe(w, "document.getElementById('btns').style.display=" + ("'block'" if show else "'none'") + ";")

    # ---- Node.js 阶段按钮 ----
    def use_winget(self):
        """「用 winget 自动安装」：后台子进程安装，完成后重新检测。"""
        if self._winget_active:
            return
        self._winget_active = True
        threading.Thread(target=self._winget_worker, daemon=True).start()

    def _prepend_path(self, dirs):
        """把 node/npm 所在目录前插到 os.environ["PATH"]，供后续子进程使用。"""
        if not dirs:
            return
        added = [d for d in dirs if d]
        if not added:
            return
        cur = os.environ.get("PATH", "")
        parts = [p for p in cur.split(os.pathsep) if p]
        merged = list(added) + [p for p in parts if p not in added]
        os.environ["PATH"] = os.pathsep.join(merged)

    def _winget_worker(self):
        """后台线程：执行 winget 安装，完成后重新检测 node/npm（含 PATH 兜底刷新）。"""
        try:
            err = ""
            ok, dirs = _detect_node()
            self._prepend_path(dirs)
            if not ok:
                r = subprocess.run(
                    [
                        "winget", "install", "OpenJS.NodeJS.LTS", "--silent",
                        "--accept-package-agreements", "--accept-source-agreements",
                    ],
                    capture_output=True, timeout=900, **_NO_WINDOW,
                )
                err = (r.stderr or r.stdout).decode("utf-8", "ignore").strip()
                ok, dirs = _detect_node()
                self._prepend_path(dirs)
            if ok:
                self._status("Node.js 安装完成 ✔")
                self._winget_active = False
                self.node_ready.set()
                return
            self._winget_active = False
            self._hide_spinner(True)
            self._set_node_buttons(False)
            self._error("winget 安装 Node.js 未成功。\n" + (err or "请重试，或选择手动安装。"))
        except Exception as exc:
            self._winget_active = False
            self._hide_spinner(True)
            self._set_node_buttons(False)
            self._error("winget 安装失败：\n{}".format(exc))

    def use_manual(self):
        """「手动安装 (MSI)」：打开官网并显示「我已安装」按钮。"""
        try:
            webbrowser.open("https://nodejs.org")
        except Exception:
            pass
        self._status("请在浏览器中下载并安装 Node.js LTS，完成后点击「我已安装」。")
        self._hide_spinner(True)
        self._show_done_btn(True)

    def already_installed(self):
        """「我已安装」：重新检测 node/npm（含 PATH 兜底刷新），通过则继续，否则提示。"""
        ok, dirs = _detect_node()
        self._prepend_path(dirs)
        if ok:
            self._status("Node.js 就绪 ✔")
            self._winget_active = False
            self.node_ready.set()
        else:
            self._error("未检测到 Node.js，请确认安装完成。可重试或切回「用 winget 自动安装」。")
            self._set_node_buttons(False)

    # ---- 插件阶段按钮 ----
    def retry(self):
        """「重试」：重新执行插件安装。"""
        self.plugin_retry.set()

    def continue_boot(self):
        """「仍然继续」：跳过插件安装，直接进入服务启动。"""
        self.plugin_continue.set()


# 引导窗初始等待页：中性文案，避免环境就绪时闪出「正在安装」误导
CHECKING_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
  html, body { margin: 0; height: 100%; }
  body {
    display: flex; align-items: center; justify-content: center;
    background: #101319; color: #e8eaed;
    font-family: -apple-system, "Segoe UI", "Microsoft YaHei", sans-serif;
    user-select: none; overflow: hidden;
  }
  .box { text-align: center; padding: 32px; }
  .spinner {
    width: 52px; height: 52px; margin: 0 auto 22px;
    border: 4px solid rgba(255,255,255,.12);
    border-top-color: #4d6bfe; border-radius: 50%;
    animation: spin 0.9s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  h1 { font-size: 17px; font-weight: 600; margin: 0 0 10px; }
  p { font-size: 13px; color: #9aa0a6; margin: 0; line-height: 1.6; }
</style>
</head>
<body>
  <div class="box">
    <div class="spinner"></div>
    <h1>正在检查运行环境</h1>
    <p>正在检测 Node.js、DeepSeek Harness 与插件…</p>
  </div>
</body>
</html>"""


def _init_boot_window(api):
    """创建并返回引导窗（初始显示中性等待画面，按需切换安装页）。"""
    import webview
    return webview.create_window(
        APP_NAME, html=CHECKING_HTML, width=520, height=400,
        resizable=False, js_api=api, text_select=True,
    )


def _run_node_stage(window, api):
    """第 1 步：Node.js 双选项安装交互（硬阻塞，不可跳过）。

    未装时切到 NODE_INSTALL_HTML 并等待 user 完成安装（node_ready）。
    用户关闭窗口会让 webview 事件循环退出，从而让整个程序退出。
    """
    window.load_html(NODE_INSTALL_HTML)
    if not shutil.which("winget"):
        _js_eval_safe(
            window,
            "document.getElementById('btn-winget').disabled=true;"
            "document.getElementById('btn-winget').title='未检测到 winget 命令';"
            "document.getElementById('status').textContent="
            + json.dumps("未检测到 winget，请选择手动安装 (MSI) 方式。") + ";",
        )
    # 硬阻塞：只有安装成功才 set node_ready；失败仅展示错误并继续等待/重试。
    # 用户关闭窗口（放弃安装）= 程序整体退出。
    api.node_ready.wait()


def _run_dsh_stage(window, logfile):
    """第 2 步：安装 DeepSeek Harness（现有逻辑，界面复用 INSTALLING_HTML）。

    安装失败抛出异常，由 _bootstrap 统一展示失败并退出（DSH 是硬依赖，不可跳过）。
    """
    window.load_html(INSTALLING_HTML)
    install_dsh()


def _run_plugin_stage(window, api):
    """第 3 步：插件安装（可跳过）。失败在窗口提示「重试 / 仍然继续」。"""
    window.load_html(PLUGIN_INSTALL_HTML)
    while True:
        api.plugin_retry.clear()
        api.plugin_continue.clear()
        try:
            install_plugins()
            _js_eval_safe(
                window,
                "document.getElementById('title').textContent=" + json.dumps("插件安装完成 ✔") + ";"
                "document.getElementById('status').textContent=" + json.dumps("远程访问与插件市场已就绪。") + ";",
            )
            return
        except Exception as exc:
            _js_eval_safe(
                window,
                "document.getElementById('title').textContent=" + json.dumps("插件安装失败") + ";"
                "document.getElementById('status').textContent=" + json.dumps("请选择下方的操作：") + ";"
                "document.getElementById('err').textContent=" + json.dumps(str(exc)) + ";",
            )
            api._show_plugin_buttons(True)
            # 等待用户选择「重试」或「仍然继续」
            while not (api.plugin_retry.is_set() or api.plugin_continue.is_set()):
                time.sleep(0.2)
            if api.plugin_continue.is_set():
                return
            # 否则「重试」，回到循环开头重新安装


def _watchdog(window, logfile, stop_event):
    """后台守护线程：检测 dsh web 服务退出并自动重启（兜底）。

    dsh-market 等插件在执行「一键重启」时会杀掉 dsh web 进程并尝试自行
    拉起新实例；若其拉起失败（例如插件自身 bug 或端口未及时释放），服务会
    一直处于掉线状态。本线程检测到「由本程序启动的服务」持续不可用超过
    宽限期后，主动重新拉起服务并刷新主窗口。

    宽限期（WATCHDOG_GRACE_SEC）让插件自身的重启先完成；只有它失败了才
    由桌面端兜底，避免与插件重启竞争。
    """
    global _proc, _started_by_us
    down_since = None
    while not stop_event.is_set():
        try:
            # 校正进程句柄：若服务仍在运行但我们的子进程已退出（例如插件
            # 自行重启成功并接管了服务），放弃句柄与清理权，避免退出时误杀。
            if _started_by_us and _proc is not None and _proc.poll() is not None:
                if is_server_up():
                    _proc = None
                    _started_by_us = False
                else:
                    _proc = None
            if not _started_by_us:
                # 复用了外部实例：不干预（保持原有语义）。
                pass
            elif is_server_up():
                down_since = None
            else:
                # 服务不可用
                now = time.time()
                if down_since is None:
                    down_since = now
                if now - down_since >= WATCHDOG_GRACE_SEC:
                    # 宽限期已过：尝试重新拉起
                    try:
                        _proc = start_server(logfile)
                        _started_by_us = True
                    except Exception:
                        _proc = None
                        down_since = None
                    else:
                        if wait_until_up(timeout=WATCHDOG_STARTUP_TIMEOUT_SEC):
                            down_since = None
                            # 服务恢复：刷新主窗口，让界面重新连上后端
                            try:
                                window.load_url(URL)
                            except Exception:
                                pass
                        else:
                            # 拉起失败：清理并重置计时，稍后再试
                            stop_server(_proc)
                            _proc = None
                            down_since = None
        except Exception:
            pass
        # 可中断的轮询间隔（stop_event 置位时立即退出）
        stop_event.wait(WATCHDOG_POLL_SEC)


def _bootstrap(window, api, logfile, stop_event):
    """后台线程：按顺序引导 Node.js → DSH → 插件 → 服务 → 主界面。"""
    import webview
    try:
        # 第 1 步：Node.js（硬依赖）
        if not is_node_installed():
            _run_node_stage(window, api)

        # 第 2 步：DSH 本体
        if not is_dsh_installed():
            _run_dsh_stage(window, logfile)

        # 第 3 步：插件（缺失才引导，失败可跳过）
        if any(not is_plugin_installed(p) for p in PLUGINS):
            _run_plugin_stage(window, api)

        # 第 4 步：启动后端服务
        prepare_server(logfile)

        # 第 5 步：打开主界面（先建主窗、再销毁引导窗，避免窗口数归零导致退出）
        main_window = webview.create_window(
            APP_NAME, URL, width=1280, height=820, min_size=(900, 600),
            text_select=True,  # 允许鼠标框选复制文本
        )
        window.destroy()
        # 启动服务守护（兜底：插件重启失败时由桌面端拉起）
        watchdog = threading.Thread(
            target=_watchdog, args=(main_window, logfile, stop_event),
            daemon=True,
        )
        watchdog.start()
    except Exception as exc:
        # 服务启动等阶段发生硬错误：在窗口内展示并等待用户关闭即退出
        _show_install_failure(window, exc)


def main():
    import webview

    logfile = os.path.join(log_dir(), "dsh-web.log")
    stop_event = threading.Event()

    # 先检测环境：Node.js → DSH → 插件
    node_ok = is_node_installed()
    dsh_ok = is_dsh_installed()
    plugins_ok = all(is_plugin_installed(p) for p in PLUGINS)

    if node_ok and dsh_ok and plugins_ok:
        # 环境已就绪：直接打开主界面，不经过引导窗
        try:
            prepare_server(logfile)
        except Exception as exc:
            show_error(str(exc))
            sys.exit(1)
        window = webview.create_window(
            APP_NAME, URL, width=1280, height=820, min_size=(900, 600),
            text_select=True,  # 允许鼠标框选复制文本
        )
        # 启动服务守护（兜底：插件重启失败时由桌面端拉起）
        watchdog = threading.Thread(
            target=_watchdog, args=(window, logfile, stop_event), daemon=True,
        )
        watchdog.start()
        try:
            webview.start()
        finally:
            stop_event.set()
            if _started_by_us:
                stop_server(_proc)
    else:
        # 存在缺失组件：进入引导窗，仅在实际检测到未安装时弹出对应安装页
        api = _BootApi()
        window = _init_boot_window(api)
        try:
            webview.start(_bootstrap, (window, api, logfile, stop_event))
        finally:
            stop_event.set()
            if _started_by_us:
                stop_server(_proc)


if __name__ == "__main__":
    main()


