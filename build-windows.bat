@echo off
echo Building Isaac Downloader for Windows x86-64...
cd /d %~dp0
wails build -platform windows/amd64
if %ERRORLEVEL% NEQ 0 (
    echo Build failed!
    exit /b 1
)
copy build\bin\isaac-downloader.exe ..\isaac-sim-backend\isaac-sim-backend-service\src\main\resources\installers\downloader\windows-x64\
if %ERRORLEVEL% NEQ 0 (
    echo Copy failed!
    exit /b 1
)
echo Windows x86-64 build complete!
echo Output: isaac-sim-backend-service\src\main\resources\installers\downloader\windows-x64\isaac-downloader.exe
