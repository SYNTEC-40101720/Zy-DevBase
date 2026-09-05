# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the independent SYNTEC updater helper."""

from pathlib import Path

block_cipher = None
ROOT = Path(SPECPATH)

updater = Analysis(
    [str(ROOT / "backend" / "devbase" / "desktop" / "update_helper.py")],
    pathex=[str(ROOT / "backend")],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "httpx"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(updater.pure, updater.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    updater.scripts,
    [],
    exclude_binaries=True,
    name="SYNTEC_DevBase-updater",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "app-logo.ico"),
    version=str(ROOT / "version_info.txt"),
)

coll = COLLECT(
    exe,
    updater.binaries,
    updater.zipfiles,
    updater.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SYNTEC_DevBase-updater",
)
