#!/bin/bash
set -e
echo "Building Isaac Downloader for macOS ARM64..."
cd "$(dirname "$0")"
wails build -platform darwin/arm64
cp "build/bin/Isaac Downloader" ../isaac-sim-backend/isaac-sim-backend-service/src/main/resources/installers/downloader/darwin-arm64/
echo "macOS ARM64 build complete!"
echo "Output: isaac-sim-backend-service/src/main/resources/installers/downloader/darwin-arm64/Isaac Downloader"
