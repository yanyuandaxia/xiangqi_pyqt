# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

# Determine engine path based on platform
engine_bin = []
if sys.platform == 'win32':
    if os.path.exists('Windows/pikafish-avx2.exe'):
        engine_bin = [('Windows/pikafish-avx2.exe', 'Windows')]
    elif os.path.exists('pikafish.exe'):
        engine_bin = [('pikafish.exe', '.')]
elif sys.platform == 'darwin':
    if os.path.exists('MacOS/pikafish-apple-silicon'):
        engine_bin = [('MacOS/pikafish-apple-silicon', 'MacOS')]
    elif os.path.exists('pikafish'):
        engine_bin = [('pikafish', '.')]
else: # Linux
    if os.path.exists('Linux/pikafish-avx2'):
        engine_bin = [('Linux/pikafish-avx2', 'Linux')]
    elif os.path.exists('pikafish'):
        engine_bin = [('pikafish', '.')]

# Add nnue if exists
datas = [('xiangqi_pyqt.png', '.')]
if os.path.exists('pikafish.nnue'):
    datas.append(('pikafish.nnue', '.'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=engine_bin,
    datas=datas,
    hiddenimports=[],
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
    name='xiangqi_pyqt',
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
)
