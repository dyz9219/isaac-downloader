@echo off
echo Building Isaac Downloader for Linux using Docker...

REM 构建镜像（如果不存在）
if not exist ".docker-built" (
    echo Building Docker image...
    docker build -f Dockerfile.build -t isaac-downloader-builder .
    if errorlevel 1 (
        echo Failed to build Docker image
        exit /b 1
    )
    echo. > .docker-built
)

REM 清理之前的构建
if exist "build\bin\isaac-downloader" del /Q "build\bin\isaac-downloader"

REM 运行构建
echo Building Linux x64 executable...
docker run --rm -v "%CD%:/workspace" isaac-downloader-builder bash -c "cd /workspace && wails build -platform linux/amd64"

if errorlevel 1 (
    echo Build failed
    exit /b 1
)

echo.
echo Build completed!
echo Output: build\bin\isaac-downloader
echo.
