# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path

import tkinterdnd2

block_cipher = None
tkdnd_src = Path(tkinterdnd2.__file__).parent / "tkdnd" / "win-x64"

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[(str(tkdnd_src), os.path.join("tkinterdnd2", "tkdnd", "win-x64"))],
    hiddenimports=["PIL._imaging", "worker", "preview_view", "pixelizer_core", "toggle_switch"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Pixelizer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="icon.ico",
)
