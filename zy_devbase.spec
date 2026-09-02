# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Zy_DevBase desktop application.

Builds an onedir (single folder) distribution containing:
  * main.py as the entry point
  * the zy_devbase backend package
  * the prebuilt web/dist frontend (served as static files)

Run from the project root:
    & backend\.venv\Scripts\python.exe -m PyInstaller zy_devbase.spec --noconfirm
"""

from pathlib import Path

block_cipher = None

ROOT = Path(SPECPATH)

a = Analysis(
    ["main.py"],
    pathex=[str(ROOT / "backend")],
    binaries=[],
    datas=[
        # Bundle the prebuilt frontend so the packaged app can serve it.
        (str(ROOT / "web" / "dist"), "web/dist"),
    ],
    hiddenimports=[
        # pywebview edgechromium backend
        "webview",
        "webview.platforms.edgechromium",
        "clr_loader",
        "pythonnet",
        # backend modules loaded dynamically at runtime
        "zy_devbase.desktop.launcher",
        "zy_devbase.api.app",
        # uvicorn parts pulled in via factory string
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Trim test-only deps from the frozen bundle.
        "pytest",
        "httpx",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Zy_DevBase",
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
    icon=None,
    # version="version_info.txt",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Zy_DevBase",
)