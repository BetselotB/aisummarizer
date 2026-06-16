# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for AI Study Guide Generator desktop app."""

import sys
from pathlib import Path

block_cipher = None
root = Path(SPECPATH).resolve().parent

datas = [
    (str(root / "app" / "static"), "app/static"),
    (str(root / "prompts"), "prompts"),
    (str(root / "template"), "template"),
]

hiddenimports = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    "multipart",
    "google.generativeai",
    "google.api_core",
    "reportlab",
    "pypdf",
    "httpx",
    "sqlite3",
]

a = Analysis(
    [str(root / "desktop.py")],
    pathex=[str(root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["googleapiclient", "googleapiclient.discovery_cache"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# API discovery JSON is huge and unused by this app.
a.datas = [entry for entry in a.datas if "discovery_cache" not in entry[0]]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AI Study Guide Generator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="AI Study Guide Generator",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="AI Study Guide Generator.app",
        icon=None,
        bundle_identifier="com.aisummarizer.desktop",
        info_plist={
            "CFBundleDisplayName": "AI Study Guide Generator",
            "CFBundleName": "AI Study Guide Generator",
            "NSHighResolutionCapable": True,
        },
    )
