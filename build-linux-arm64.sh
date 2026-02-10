#!/bin/bash
set -e
echo "Building Isaac Downloader for Linux ARM64..."
cd "$(dirname "$0")"
wails build -platform linux/arm64
cp build/bin/isaac-downloader ../isaac-sim-backend/isaac-sim-backend-service/src/main/resources/installers/downloader/linux-arm64/
echo "Linux ARM64 build complete!"
echo "Output: isaac-sim-backend-service/src/main/resources/installers/downloader/linux-arm64/isaac-downloader"
