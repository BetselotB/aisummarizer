#!/usr/bin/env python3
"""Desktop launcher — embedded FastAPI server + native app window."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
from pathlib import Path

import uvicorn

APP_TITLE = "AI Study Guide Generator"
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 860
MIN_WIDTH = 960
MIN_HEIGHT = 640


def _log_path() -> Path:
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "AI Study Guide Generator"
    elif sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA")
        base = Path(local) if local else Path.home() / "AppData" / "Local" / "AIStudyGuideGenerator"
    else:
        base = Path.home() / ".local" / "share" / "aisummarizer"
    base.mkdir(parents=True, exist_ok=True)
    return base / "desktop.log"


def _log(message: str) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n"
    try:
        _log_path().write_text(
            (_log_path().read_text(encoding="utf-8") if _log_path().exists() else "") + line,
            encoding="utf-8",
        )
    except OSError:
        pass


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_server(url: str, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status < 500:
                    return
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.15)
    raise RuntimeError(f"Server did not start within {timeout:.0f}s: {url}")


def _run_server(port: int) -> None:
    from app.main import app as fastapi_app

    uvicorn.run(
        fastapi_app,
        host="127.0.0.1",
        port=port,
        log_level="info",
        access_log=False,
    )


def _open_app_window(url: str) -> None:
    if sys.platform == "darwin":
        for browser, args in (
            (
                "/Applications/Google Chrome.app",
                ["--args", f"--app={url}", f"--window-size={WINDOW_WIDTH},{WINDOW_HEIGHT}"],
            ),
            (
                "/Applications/Microsoft Edge.app",
                ["--args", f"--app={url}", f"--window-size={WINDOW_WIDTH},{WINDOW_HEIGHT}"],
            ),
            ("Safari", ["-g", url]),
        ):
            if browser.startswith("/") and not os.path.exists(browser):
                continue
            try:
                subprocess.Popen(["open", "-na", browser, *args])
                return
            except OSError:
                continue
    elif sys.platform == "win32":
        for cmd in (
            ["cmd", "/c", "start", "", "msedge", f"--app={url}"],
            ["cmd", "/c", "start", "", "chrome", f"--app={url}"],
        ):
            try:
                subprocess.Popen(cmd)
                return
            except OSError:
                continue
    else:
        import webbrowser

        webbrowser.open(url)


def _open_with_pywebview(url: str) -> bool:
    try:
        import webview
    except ImportError:
        return False

    window = webview.create_window(
        APP_TITLE,
        url,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        min_size=(MIN_WIDTH, MIN_HEIGHT),
    )
    webview.start(gui="edgechromium" if sys.platform == "win32" else None)
    return True


def main() -> None:
    os.environ.setdefault("AISUMMARIZER_DESKTOP", "1")

    port = _find_free_port()
    url = f"http://127.0.0.1:{port}/"
    _log(f"Starting desktop app on {url}")

    server = threading.Thread(target=_run_server, args=(port,), daemon=True)
    server.start()
    _wait_for_server(url)
    _log("Server ready")

    if _open_with_pywebview(url):
        return

    _open_app_window(url)
    _log("Opened browser window")

    while server.is_alive():
        time.sleep(0.5)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        _log(traceback.format_exc())
        raise
