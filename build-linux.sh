#!/bin/bash
set -e

# 更新包管理器并安装依赖
apt-get update
apt-get install -y wget libgtk-3-dev libwebkit2gtk-4.0-dev curl gnupg --fix-missing || apt-get install -y wget libgtk-3-dev libwebkit2gtk-4.0-dev curl gnupg

# 安装 Node.js 和 npm
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

# 下载并安装 Go 1.23
wget https://go.dev/dl/go1.23.6.linux-amd64.tar.gz
rm -rf /usr/local/go
tar -C /usr/local -xzf go1.23.6.linux-amd64.tar.gz

# 使用新版本的 Go 安装 Wails
export PATH=/usr/local/go/bin:$PATH
export GOPATH=/root/go
go install github.com/wailsapp/wails/v2/cmd/wails@latest

# 构建 Linux 应用
# 修复 rollup 可选依赖问题 - 直接安装平台特定包
cd /workspace/frontend
rm -rf node_modules package-lock.json
npm install
npm install --no-save @rollup/rollup-linux-x64-gnu
cd /workspace
/root/go/bin/wails build -platform linux/amd64
