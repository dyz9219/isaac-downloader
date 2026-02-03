# Isaac Downloader - 构建指南

本文档说明如何为不同平台构建 Isaac Downloader 可执行文件。

## 前置条件

### 安装 Go
- 下载并安装 Go 1.21+: https://golang.org/dl/
- 验证安装: `go version`

### 安装 Wails v2
```bash
go install github.com/wailsapp/wails/v2/cmd/wails@latest
```
- 验证安装: `wails version`

## 平台构建说明

### Windows x64 (当前环境)

由于项目目录位于 Windows 环境，但 Go 未安装，需要先安装 Go 和 Wails:

```bash
# 1. 安装 Go 1.21+ 后
# 2. 安装 Wails
go install github.com/wailsapp/wails/v2/cmd/wails@latest

# 3. 构建
cd D:\workspace\work\bwy\isaac-downloader
wails build -platform windows/amd64

# 4. 复制到 Java 项目资源目录
copy build\bin\isaac-downloader.exe ..\isaac-sim-backend\isaac-sim-backend-service\src\main\resources\installers\downloader\windows-x64\
```

### macOS ARM64

需要在 macOS ARM64 (Apple Silicon) 机器上构建:

```bash
# 1. 安装 Go 和 Wails
# 2. 构建
cd /path/to/isaac-downloader
wails build -platform darwin/arm64

# 3. 复制到 Java 项目资源目录
cp "build/bin/Isaac Downloader" ../isaac-sim-backend/isaac-sim-backend-service/src/main/resources/installers/downloader/darwin-arm64/
```

### Linux x64

需要在 Linux x64 机器上构建:

```bash
# 1. 安装 Go 和 Wails
# 2. 安装依赖 (Ubuntu/Debian)
sudo apt-get install libwebkit2gtk-4.1-dev \
    build-essential \
    pkg-config \
    libgtk-3-dev

# 3. 构建
cd /path/to/isaac-downloader
wails build -platform linux/amd64

# 4. 复制到 Java 项目资源目录
cp build/bin/isaac-downloader ../isaac-sim-backend/isaac-sim-backend-service/src/main/resources/installers/downloader/linux-x64/
```

## 使用 Docker 构建 (替代方案)

如果无法访问对应平台的机器，可以使用 Docker:

### Linux x64 Docker 构建

使用提供的 Dockerfile:

```bash
cd D:\workspace\work\bwy\isaac-downloader
docker build -f Dockerfile.build -t isaac-downloader-builder .
docker run --rm -v ${PWD}/build:/build isaac-downloader-builder
```

## 当前状态

- [x] Windows x64: `isaac-downloader.exe` - 已复制到 `windows-x64/` 目录
- [ ] macOS ARM64: `Isaac Downloader` - 待构建
- [ ] Linux x64: `isaac-downloader` - 待构建

## 验证构建

构建完成后，验证可执行文件是否正确放置:

```bash
# 检查 Windows 版本
ls -lh isaac-sim-backend/isaac-sim-backend-service/src/main/resources/installers/downloader/windows-x64/

# 检查 macOS 版本
ls -lh isaac-sim-backend/isaac-sim-backend-service/src/main/resources/installers/downloader/darwin-arm64/

# 检查 Linux 版本
ls -lh isaac-sim-backend/isaac-sim-backend-service/src/main/resources/installers/downloader/linux-x64/
```

## 相关文件

- Wails 配置: `wails.json`
- 构建脚本: `build-windows.bat`, `build-macos-arm.sh`, `build-linux-x64.sh`
- 主应用: `main.go`, `app.go`
- 后端逻辑: `backend/downloader.go`, `backend/parser.go`
- 前端界面: `frontend/src/App.svelte`

## 测试

构建完成后，可以通过 Java 后端接口测试:

```bash
# 调用 /Downloader 接口下载 ZIP 包
# ZIP 包应包含:
# 1. 可执行文件
# 2. 脚本文件
```
