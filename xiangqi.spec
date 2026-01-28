# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for xiangqi_pyqt
Usage: pyinstaller xiangqi.spec
"""

import sys
import os
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# 获取当前目录
CURRENT_DIR = os.path.dirname(os.path.abspath(SPEC))

# 需要包含的数据文件
datas = [
    # NNUE 神经网络权重文件
    (os.path.join(CURRENT_DIR, 'pikafish.nnue'), '.'),
    # 默认设置文件
    (os.path.join(CURRENT_DIR, 'settings.json'), '.'),
    # 示例 PGN 文件
    (os.path.join(CURRENT_DIR, 'example.pgn'), '.'),
    # 应用图标
    (os.path.join(CURRENT_DIR, 'xiangqi_pyqt.png'), '.'),
]

# 根据平台包含对应的引擎文件
if sys.platform == 'linux':
    # Linux 引擎
    linux_dir = os.path.join(CURRENT_DIR, 'Linux')
    if os.path.exists(linux_dir):
        for f in os.listdir(linux_dir):
            if os.path.isfile(os.path.join(linux_dir, f)):
                datas.append((os.path.join(linux_dir, f), 'Linux'))
elif sys.platform == 'darwin':
    # macOS 引擎
    macos_dir = os.path.join(CURRENT_DIR, 'MacOS')
    if os.path.exists(macos_dir):
        for f in os.listdir(macos_dir):
            filepath = os.path.join(macos_dir, f)
            if os.path.isfile(filepath):
                datas.append((filepath, 'MacOS'))
elif sys.platform == 'win32':
    # Windows 引擎
    windows_dir = os.path.join(CURRENT_DIR, 'Windows')
    if os.path.exists(windows_dir):
        for f in os.listdir(windows_dir):
            filepath = os.path.join(windows_dir, f)
            if os.path.isfile(filepath):
                datas.append((filepath, 'Windows'))

a = Analysis(
    ['main.py'],
    pathex=[CURRENT_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtWidgets',
        'PyQt5.QtGui',
    ],
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
    console=False,  # 设置为 False 隐藏控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
