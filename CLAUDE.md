# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此代码库中工作时提供指导。

## 项目概述

Isaac Downloader 是一个跨平台桌面应用程序，用于批量下载 Isaac Sim 平台文件。该应用与 Java 后端服务集成——用户接收包含可执行文件和脚本文件的 ZIP 包，然后在本地运行下载器。

**技术栈：**
- 后端：Go 1.21+ with Wails v2 framework
- 前端：Svelte 4.2.0 + Vite 5.0.0
- 构建：Wails CLI 跨平台编译（Windows、macOS ARM64、Linux x64）

## 开发命令

### 前置要求
```bash
# 安装 Wails CLI（如果尚未安装）
go install github.com/wailsapp/wails/v2/cmd/wails@latest
```

### 项目设置
```bash
# 安装前端依赖
cd frontend
npm install
```

### 开发调试
```bash
# 前端开发服务器（仅前端）
cd frontend
npm run dev

# Wails 开发模式（完整应用，支持热重载）
wails dev
```

### 构建打包
```bash
# Windows x64
.\build-windows.bat

# macOS ARM64
chmod +x ./build-macos-arm.sh && ./build-macos-arm.sh

# Linux x64
chmod +x ./build-linux-x64.sh && ./build-linux-x64.sh

# Linux ARM64
chmod +x ./build-linux-arm64.sh && ./build-linux-arm64.sh

# 手动指定平台构建
wails build -platform windows/amd64
wails build -platform darwin/arm64
wails build -platform linux/amd64
wails build -platform linux/arm64
```

### 输出位置
构建的二进制文件会被复制到 Java 后端资源目录：
```
isaac-sim-backend-service/src/main/resources/installers/downloader/
├── windows-x64/isaac-downloader.exe
├── darwin-arm64/Isaac Downloader
├── linux-x64/isaac-downloader
└── linux-arm64/isaac-downloader
```

## 架构设计

### 后端（Go）

**入口点：**
- `main.go` - Wails 应用启动
- `app.go` - 主应用逻辑、前端绑定和事件发射

**核心组件（`backend/` 包）：**

1. **DownloadEngine**（`downloader.go`）：
   - 使用信号量模式管理并发下载（默认：3 个并发）
   - 支持暂停/恢复，通过 HTTP Range 请求实现断点续传
   - 使用 `sync.RWMutex` 保证线程安全的任务跟踪
   - 基于回调的事件系统，用于进度/完成/错误事件

2. **Script Parser**（`parser.go`）：
   - 从 PowerShell（.ps1）、Batch（.bat）和 Shell（.sh）脚本中提取 JSON 配置
   - 处理 `__AMP__` 占位符替换为 `&` 字符（解决脚本转义问题）
   - 支持多种脚本变量模式：`$FilesJson`、`set FilesJson=`、`FILES_JSON=`
   - **任务名称兜底机制**：当无法从文件路径提取任务名称时，使用脚本文件名作为兜底

3. **配置结构：**
   ```
   DownloaderConfig
   └── Tasks []TaskInfo
       └── Files []FileInfo
           ├── URL（下载源）
           └── Path（相对本地路径）
   ```

### 前端（Svelte）

**组件结构（`frontend/src/components/`）：**
- `App.svelte` - 主容器、状态管理、Wails 事件监听
- `TaskList.svelte` - 显示从脚本加载的任务
- `ProgressBar.svelte` - 整体进度可视化
- `ControlBar.svelte` - 开始/暂停/加载脚本控制
- `LogPanel.svelte` - 实时事件日志显示
- `Settings.svelte` - 并发数和下载路径配置
- `FileListDialog.svelte` - 脚本文件选择对话框

**状态流：**
- Go 后端发射 Wails 事件（`progress`、`complete`、`error`）
- 前端监听器更新响应式状态变量
- `window.go.main.App.*` 绑定从 Svelte 调用 Go 方法

### 与 Java 后端集成

1. Java 后端的 `/Downloader` 端点以 ZIP 格式提供平台特定二进制文件
2. ZIP 包含：可执行文件 + 嵌入 JSON 配置的脚本文件
3. 用户解压并运行可执行文件
4. 应用在启动时自动检测同目录下的脚本文件（`App.autoDetectScript()`）
5. DownloadEngine 将文件并发下载到配置的路径

## 核心实现细节

### 并发模型
- 信号量模式：`semaphore chan struct{}` 限制并发下载数
- 每个下载在一个 goroutine 中运行
- 使用 `sync.Mutex` 保护任务状态（进度/字节计数）
- 使用 context 取消实现暂停功能

### 暂停/恢复支持
- 下载前检查现有文件大小
- 设置 HTTP `Range: bytes=N-` 头请求部分内容
- 以 `O_APPEND` 模式打开文件继续下载
- `context.CancelFunc` 停止进行中的下载

### 脚本自动检测
- 启动时扫描可执行文件目录（`OnStartup`）
- 匹配 `.ps1`、`.bat`、`.sh` 扩展名
- 自动加载第一个匹配的脚本
- 用户可通过文件对话框手动选择

### 脚本加载逻辑
- **单文件选择**：始终替换当前任务
- **多文件选择**：第一个文件替换，后续文件合并
- **浏览其他目录**：始终替换当前任务
- **替换时重置状态**：清除下载进度、完成数、下载状态

### Wails 事件通信
- Go 发射：`runtime.EventsEmit(ctx, "progress", data)`
- Svelte 监听：`window.EventsOn('progress', callback)`
- 数据序列化由 Wails 运行时处理
- 对下载期间的实时进度更新至关重要

## 常见模式

**添加可从前端调用的新 Go 方法：**
1. 在 `app.go` 的 `App` 结构体上定义方法
2. 导出方法必须大写（public）
3. 返回类型应为 JSON 可序列化类型或 error
4. 在 Svelte 中通过 `window.go.main.App.MethodName()` 访问

**添加新的 Wails 事件：**
1. 在 Go 中发射：`runtime.EventsEmit(a.ctx, "eventName", data)`
2. 在 Svelte `onMount` 中监听：`window.EventsOn('eventName', callback)`
3. 组件卸载时清理监听器（目前未实现）

**修改脚本解析器：**
- 更新 `extractJsonFromScript()` 中的正则表达式模式
- 测试所有三种脚本类型（.ps1、.bat、.sh）
- 如果 URL 包含 `&` 字符，处理 `__AMP__` 替换

## 故障排查规则

故障排查需遵循以下核心规则：

1. **症状-原因分层诊断** - 别在第一层停下
   - 不仅是修复错误，要理解根本原因
   - 从表象深入到配置、框架、系统层面

2. **静态分析优先** - 配置文件比日志更诚实
   - 先检查配置文件（wails.json、package.json、workflow 等）
   - 配置决定构建行为，日志只是结果

3. **三角验证** - 源码配置 × 构建配置 × 实际输出
   - 源码配置：wails.json 中的 productName、outputfilename
   - 构建配置：workflow 中的 matrix 参数
   - 实际输出：build/bin 目录下的实际文件名
   - 三者必须一致才能成功

4. **框架默认优先** - 稳定版 > 最新版
   - Ubuntu 22.04 比 ubuntu-latest 更稳定（包版本确定）
   - 避免使用 "latest" 类标签，使用明确版本号

5. **问题重构** - 从"怎么修"转向"为什么不一致"
   - 不是问"如何修复"，而是问"配置之间哪里不一致"
   - macOS: productName="Isaac Downloader" → 输出 "Isaac Downloader.app"
   - workflow 期望: "isaac-downloader" → 不匹配
   - 解决方案是让三者一致，而不是"打补丁"
