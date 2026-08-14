# -*- coding: utf-8 -*-
"""DeepSeek Harness 桌面启动器 (DSH Desktop Launcher)

功能：
1. 启动（或复用）dsh web 后端服务；
2. 用 pywebview 以原生窗口加载 WebUI，实现桌面软件体验；
3. 窗口关闭时自动清理由本程序启动的后端进程。
"""

import os
import sys
import time
import shutil
import subprocess
import urllib.request

APP_NAME = "DeepSeek Harness"
HOST = os.environ.get("DSH_HOST", "127.0.0.1")
PORT = int(os.environ.get("DSH_PORT", "3080"))
URL = "http://{host}:{port}".format(host=HOST, port=PORT)


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


def is_server_up(timeout=1.5):
    try:
        with urllib.request.urlopen(URL + "/", timeout=timeout) as resp:
            return resp.status < 500
    except Exception:
        return False


def start_server(logfile):
    cmd = resolve_dsh() + ["web", "--host", HOST, "--port", str(PORT)]
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    with open(logfile, "ab") as logf:
        return subprocess.Popen(
            cmd, stdout=logf, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, **kwargs
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
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
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
        ctypes.windll.user32.MessageBoxW(0, msg, APP_NAME, 0x10)  # MB_ICONERROR
    except Exception:
        print(msg, file=sys.stderr)


def main():
    import webview

    logfile = os.path.join(log_dir(), "dsh-web.log")
    proc = None
    started_by_us = False

    if not is_server_up():
        try:
            proc = start_server(logfile)
            started_by_us = True
        except Exception as exc:
            show_error("启动 DSH 后端失败：\n{exc}".format(exc=exc))
            sys.exit(1)
        if not wait_until_up():
            show_error("DSH WebUI 启动超时，请查看日志：\n" + logfile)
            stop_server(proc)
            sys.exit(1)

    window = webview.create_window(
        APP_NAME,
        URL,
        width=1280,
        height=820,
        min_size=(900, 600),
    )
    try:
        webview.start()
    finally:
        if started_by_us:
            stop_server(proc)


if __name__ == "__main__":
    main()
