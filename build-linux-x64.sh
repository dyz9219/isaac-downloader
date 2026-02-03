#!/bin/bash
set -e
echo "Building Isaac Downloader for Linux x86-64..."
cd "$(dirname "$0")"
wails build -platform linux/amd64
cp build/bin/isaac-downloader ../isaac-sim-backend/isaac-sim-backend-service/src/main/resources/installers/downloader/linux-x64/
echo "Linux x86-64 build complete!"
echo "Output: isaac-sim-backend-service/src/main/resources/installers/downloader/linux-x64/isaac-downloader"
