# Isaac Downloader 打包执行计划

## 环境准备

### 1. 检查并安装 Wails CLI

```bash
# 检查是否已安装
wails version

# 如果未安装，执行安装
go install github.com/wailsapp/wails/v2/cmd/wails@latest
```

### 2. 安装前端依赖

```bash
cd D:\workspace\work\bwy\isaac-downloader\frontend
npm install
cd ..
```

---

## 打包步骤

### 方案 A：Windows 本地构建（推荐）

#### Windows x64 版本

```bash
cd D:\workspace\work\bwy\isaac-downloader
.\build-windows.bat
```

**输出位置**：
```
isaac-sim-backend-service\src\main\resources\installers\downloader\windows-x64\isaac-downloader.exe
```

#### macOS ARM64 和 Linux x64 版本

由于 Wails 交叉编译限制，这两个平台需要：

**选项 1 - 使用 GitHub Actions（推荐）**
- 在仓库中添加 `.github/workflows/build.yml`
- 推送代码后自动构建三平台版本

**选项 2 - 找对应平台的机器构建**
- macOS ARM：在 Apple Silicon Mac 上运行 `./build-macos-arm.sh`
- Linux x64：在 Linux 机器上运行 `./build-linux-x64.sh`

**选项 3 - 使用 Docker（Linux）**
```bash
# 在 Windows 上用 Docker 构建 Linux 版本
docker run --rm -v %cd%:/app -w /app/isaac-downloader \
    ghcr.io/wailsbuild/go:1.21 wails build -platform linux/amd64
```

---

### 方案 B：完整构建（有三台电脑可用时）

```bash
# Windows 电脑
cd D:\workspace\work\bwy\isaac-downloader
.\build-windows.bat

# macOS ARM 电脑
cd /path/to/isaac-downloader
chmod +x build-macos-arm.sh
./build-macos-arm.sh

# Linux 电脑
cd /path/to/isaac-downloader
chmod +x build-linux-x64.sh
./build-linux-x64.sh
```

---

## 验证打包结果

### 1. 检查文件存在

```bash
# Windows
dir isaac-sim-backend-service\src\main\resources\installers\downloader\windows-x64\isaac-downloader.exe

# 应该看到文件存在
```

### 2. 测试运行

```bash
# Windows
.\build\bin\isaac-downloader.exe

# 应该能看到 GUI 界面启动
```

---

## 常见问题

### Wails 命令找不到

```bash
# 确保 Go bin 目录在 PATH 中
go env -w GOBIN=%USERPROFILE%\go\bin
set PATH=%PATH%;%USERPROFILE%\go\bin
```

### 前端构建失败

```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### 构建成功但无法运行

- Windows：可能需要安装 [VC++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)
- macOS：需要在"系统设置"中允许运行未签名应用
- Linux：确保有执行权限 `chmod +x isaac-downloader`

---

## 最终文件清单

打包完成后，确保以下文件存在：

```
isaac-sim-backend-service/src/main/resources/installers/downloader/
├── windows-x64/
│   └── isaac-downloader.exe      ← 从 Windows 构建
├── darwin-arm64/
│   └── Isaac Downloader          ← 从 macOS ARM 构建
└── linux-x64/
    └── isaac-downloader          ← 从 Linux 构建
```

---

## 集成到 Java 后端

打包完成后，Java 后端的 `/Downloader` 接口会自动：
1. 从 resources 目录读取对应平台的可执行文件
2. 生成脚本文件
3. 打包成 ZIP 返回给用户

**测试接口**：
```bash
curl -X POST http://localhost:8080/isaacsim/file/Downloader \
  -H "Content-Type: application/json" \
  -d "{\"taskIds\":[1],\"os\":\"windows\",\"arch\":\"x64"}" \
  --output test.zip
```
