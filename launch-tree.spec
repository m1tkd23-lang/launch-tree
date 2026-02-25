# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import os

# repo ルートで pyinstaller を実行する前提
REPO_ROOT = Path(os.getcwd()).resolve()
SRC_DIR = REPO_ROOT / "src"

a = Analysis(
    ['apps\\main.py'],
    pathex=[str(SRC_DIR)],
    binaries=[],
    datas=[
        ('data', 'data'),
        ('README.md', '.'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='launch-tree',
    icon='assets\\launch_tree_clean.ico',  # ← ここ重要
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
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='launch-tree',
)