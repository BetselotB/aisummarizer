#!/usr/bin/env python3
"""Desktop launcher — embedded FastAPI server + native app window."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

import uvicorn

APP_TITLE = "AI Study Guide Generator"
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 860
MIN_WIDTH = 960
MIN_HEIGHT = 640


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
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=port,
        log_level="info",
        access_log=False,
    )


def _open_app_window(url: str) -> subprocess.Popen | None:
    if sys.platform == "darwin":
        for browser, args in (
            ("/Applications/Google Chrome.app", ["--args", f"--app={url}", f"--window-size={WINDOW_WIDTH},{WINDOW_HEIGHT}"]),
            ("/Applications/Microsoft Edge.app", ["--args", f"--app={url}", f"--window-size={WINDOW_WIDTH},{WINDOW_HEIGHT}"]),
            ("Safari", ["-g", url]),
        ):
            if browser.startswith("/") and not os.path.exists(browser):
                continue
            try:
                return subprocess.Popen(["open", "-na", browser, *args])
            except OSError:
                continue
    if sys.platform == "win32":
        for cmd in (
            ["cmd", "/c", "start", "", "msedge", f"--app={url}"],
            ["cmd", "/c", "start", "", "chrome", f"--app={url}"],
        ):
            try:
                return subprocess.Popen(cmd)
            except OSError:
                continue
    import webbrowser

    webbrowser.open(url)
    return None


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

    server = threading.Thread(target=_run_server, args=(port,), daemon=True)
    server.start()
    _wait_for_server(url)

    if _open_with_pywebview(url):
        return

    browser = _open_app_window(url)
    if browser is None:
        while server.is_alive():
            time.sleep(0.5)
        return

    while server.is_alive():
        if browser.poll() is not None:
            break
        time.sleep(0.5)


if __name__ == "__main__":
    main()
