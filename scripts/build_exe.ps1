param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$venv = Join-Path $root ".venv"
$py = Join-Path $venv "Scripts\python.exe"
$any4 = Join-Path (Split-Path $root -Parent) "any4lerobot"

if (-not (Test-Path $py)) {
    python -m venv $venv
}

if ($Clean) {
    if (Test-Path "$root\build") { Remove-Item -Recurse -Force "$root\build" }
    if (Test-Path "$root\dist") { Remove-Item -Recurse -Force "$root\dist" }
}

& $py -m pip install -U pip
& $py -m pip install -e .
& $py -m pip install pyinstaller

if (-not (Test-Path (Join-Path $any4 "agibot2lerobot\agibot_h5.py"))) {
    throw "Missing bundled any4lerobot source: $any4"
}

& $py -m PyInstaller `
  --noconfirm `
  --windowed `
  --name AgibotConverterShell `
  --distpath "$root\dist" `
  --workpath "$root\build" `
  --collect-all flet `
  --collect-all flet_desktop `
  --collect-all rosbags `
  --collect-submodules rosbags.typesys.stores `
  --collect-data tkinter `
  --add-data "$any4;any4lerobot" `
  src/agibot_converter/main.py

Write-Host "Build finished. EXE output in dist/AgibotConverterShell" -ForegroundColor Green
