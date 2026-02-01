# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

# 1. 定义默认文件名变量
exe_name = 'xiangqi_pyqt'

# Determine engine path and exe name based on platform
engine_bin = []

if sys.platform == 'win32':
    # Windows 平台配置
    exe_name = 'xiangqi-pyqt-windows' # 自动生成 .exe 后缀
    if os.path.exists('Windows/pikafish-avx2.exe'):
        engine_bin = [('Windows/pikafish-avx2.exe', 'Windows')]
    elif os.path.exists('pikafish.exe'):
        engine_bin = [('pikafish.exe', '.')]

elif sys.platform == 'darwin':
    # macOS 平台配置
    exe_name = 'xiangqi-pyqt-macos'
    if os.path.exists('MacOS/pikafish-apple-silicon'):
        engine_bin = [('MacOS/pikafish-apple-silicon', 'MacOS')]
    elif os.path.exists('pikafish'):
        engine_bin = [('pikafish', '.')]

else: 
    # Linux 平台配置
    exe_name = 'xiangqi-pyqt-linux'
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
    # 2. 这里使用动态定义的变量，而不是写死的字符串
    name=exe_name,
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