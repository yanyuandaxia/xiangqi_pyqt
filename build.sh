#!/bin/bash
# 中国象棋 PyInstaller 打包脚本
# 用法: ./build.sh

set -e

echo "========================================="
echo "       中国象棋 打包脚本"
echo "========================================="


# 清理旧的构建文件
echo "清理旧的构建文件..."
rm -rf build/ dist/ __pycache__/

# 使用 spec 文件打包
echo "开始打包..."
pyinstaller xiangqi.spec --clean

# 检查打包结果
if [ -f "dist/xiangqi_pyqt" ]; then
    echo "========================================="
    echo "打包成功!"
    echo "可执行文件位置: dist/xiangqi_pyqt"
    echo "========================================="
    
    # 显示文件大小
    ls -lh dist/xiangqi_pyqt
else
    echo "打包失败，请检查错误信息"
    exit 1
fi
