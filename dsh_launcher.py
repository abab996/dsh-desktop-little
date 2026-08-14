# -*- coding: utf-8 -*-
"""DeepSeek Harness 桌面启动器 (DSH Desktop Launcher)

功能：
1. 启动时自动检查 DeepSeek Harness（dsh）是否已安装，未安装则先安装；
2. 启动（或复用）dsh web 后端服务；
3. 用 pywebview 以原生窗口加载 WebUI，实现桌面软件体验；
4. 窗口关闭时自动清理由本程序启动的后端进程。
"""

import os
import sys
import time
import json
import shutil
import subprocess
import urllib.request

APP_NAME = "DeepSeek Harness"
HOST = os.environ.get("DSH_HOST", "127.0.0.1")
PORT = int(os.environ.get("DSH_PORT", "3080"))
URL = "http://{host}:{port}".format(host=HOST, port=PORT)

IS_WIN = os.name == "nt"
_NO_WINDOW = {"creationflags": subprocess.CREATE_NO_WINDOW} if IS_WIN else {}

# 后端进程状态（跨线程共享）
_proc = None
_started_by_us = False

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


def log_dir():
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "DeepSeekHarness")
    os.makedirs(d, exist_ok=True)
    return d


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


def is_server_up(timeout=1.5):
    try:
        with urllib.request.urlopen(URL + "/", timeout=timeout) as resp:
            return resp.status < 500
    except Exception:
        return False


def start_server(logfile):
    cmd = resolve_dsh() + ["web", "--host", HOST, "--port", str(PORT)]
    with open(logfile, "ab") as logf:
        return subprocess.Popen(
            cmd, stdout=logf, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, **_NO_WINDOW,
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


def _install_then_launch(window, logfile):
    """后台线程：安装 dsh → 启动后端 → 切到主界面。"""
    try:
        install_dsh()
        prepare_server(logfile)
        # evaluate_js 线程安全（内部会 marshal 到 GUI 线程）
        window.evaluate_js("window.location.href = '" + URL + "';")
    except Exception as exc:
        _show_install_failure(window, exc)


def _show_install_failure(window, exc):
    msg = json.dumps(str(exc))
    updated = False
    try:
        window.evaluate_js(
            "document.body.innerHTML = "
            "'<div style=\"padding:40px;text-align:center;font-family:Segoe UI,Microsoft YaHei,sans-serif;\">"
            "<h2 style=\"color:#e5484d;font-size:18px;margin:0 0 16px;\">安装失败</h2>"
            "<pre style=\"white-space:pre-wrap;font-size:12px;color:#9aa0a6;text-align:left;\">' + "
            + msg + " + '</pre></div>';"
        )
        updated = True
    except Exception:
        pass
    if not updated:
        show_error("DeepSeek Harness 安装失败：\n" + str(exc))


def main():
    import webview

    logfile = os.path.join(log_dir(), "dsh-web.log")

    if is_dsh_installed():
        try:
            prepare_server(logfile)
        except Exception as exc:
            show_error(str(exc))
            sys.exit(1)
        window = webview.create_window(
            APP_NAME, URL, width=1280, height=820, min_size=(900, 600),
        )
        try:
            webview.start()
        finally:
            if _started_by_us:
                stop_server(_proc)
    else:
        window = webview.create_window(
            APP_NAME, html=INSTALLING_HTML, width=460, height=320, resizable=False,
        )
        try:
            webview.start(_install_then_launch, (window, logfile))
        finally:
            if _started_by_us:
                stop_server(_proc)


if __name__ == "__main__":
    main()
