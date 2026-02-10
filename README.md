# Isaac Downloader

一个跨平台 GUI 桌面下载器，用于批量下载 Isaac Sim 平台的采集文件。

## 技术栈

- **后端**: Go 1.21+
- **前端**: Svelte + Vite
- **构建**: Wails v2

## 功能特性

1. 解析脚本文件（.ps1 / .bat / .sh），提取 JSON 配置
2. 指定本地保存路径
3. 暂停/继续下载（断点续传）
4. 并发下载（默认 3 个，可配置）
5. 自动检测同目录下的脚本文件
6. macOS 风格 UI

## 构建说明

### 前置要求

- Go 1.21+
- Node.js 18+
- Wails CLI: `go install github.com/wailsapp/wails/v2/cmd/wails@latest`

### 安装依赖

```bash
# 安装前端依赖
cd frontend
npm install
cd ..
```

### 构建可执行文件

#### Windows x86-64
```bash
./build-windows.bat
```

#### macOS ARM64
```bash
chmod +x build-macos-arm.sh
./build-macos-arm.sh
```

#### Linux x86-64
```bash
chmod +x build-linux-x64.sh
./build-linux-x64.sh
```

#### Linux ARM64
```bash
chmod +x build-linux-arm64.sh
./build-linux-arm64.sh
```

### 手动构建（任意平台）

```bash
wails build -platform <platform>/<arch>
```

支持的平台：
- `windows/amd64`
- `darwin/arm64`
- `linux/amd64`
- `linux/arm64`

## 项目结构

```
isaac-downloader/
├── main.go                     # Wails 入口
├── app.go                      # 主逻辑
├── backend/
│   ├── parser.go               # 脚本解析器
│   └── downloader.go           # 下载引擎
├── frontend/
│   ├── src/
│   │   ├── App.svelte          # 主组件
│   │   ├── components/
│   │   │   ├── TaskList.svelte
│   │   │   ├── ProgressBar.svelte
│   │   │   ├── ControlBar.svelte
│   │   │   ├── LogPanel.svelte
│   │   │   └── Settings.svelte
│   │   └── main.js
│   ├── package.json
│   └── vite.config.js
├── wails.json
└── build/
```

## 使用说明

1. 从 Java 后端 `/isaacsim/file/Downloader` 接口下载 ZIP 包
2. 解压 ZIP 包，得到可执行文件和脚本文件
3. 将脚本文件放在与可执行文件同一目录
4. 双击运行可执行文件
5. 点击"开始下载"按钮开始下载
6. 可通过设置面板调整并发数和下载路径

## API 接口

### `/isaacsim/file/Downloader`

**请求方法**: POST

**请求参数**:
```json
{
  "taskIds": [1, 2, 3],
  "os": "windows",
  "arch": "x64"
}
```

**响应**: ZIP 文件下载

## 许可证

Copyright © Isaac Sim Platform
