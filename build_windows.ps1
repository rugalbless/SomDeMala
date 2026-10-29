# Gera o executável para Windows em dist\SomDeMala-windows.zip
# Uso (no PowerShell, dentro da pasta do projeto):
#   powershell -ExecutionPolicy Bypass -File build_windows.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$App = "SomDeMala"

Write-Host ">> Preparando ambiente de build"
$Base = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
& $Base -m venv .venv-build
$Py = ".\.venv-build\Scripts\python.exe"
& $Py -m pip install -q -U pip
& $Py -m pip install -q -U yt-dlp PySide6 pyinstaller

if (-not (Test-Path "ffmpeg-bin\ffmpeg.exe")) {
    Write-Host ">> Baixando FFmpeg"
    New-Item -ItemType Directory -Force "ffmpeg-bin" | Out-Null
    Invoke-WebRequest -Uri "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip" -OutFile "ffmpeg.zip"
    Expand-Archive "ffmpeg.zip" -DestinationPath "ffmpeg-tmp" -Force
    Get-ChildItem "ffmpeg-tmp" -Recurse -Include "ffmpeg.exe" | Copy-Item -Destination "ffmpeg-bin"
    Remove-Item "ffmpeg.zip", "ffmpeg-tmp" -Recurse -Force
}

Write-Host ">> Empacotando"
& $Py -m PyInstaller --noconfirm --clean --windowed --name $App `
    --add-binary "ffmpeg-bin\ffmpeg.exe;." `
    SomDeMala.py

Compress-Archive -Path "dist\$App" -DestinationPath "dist\$App-windows.zip" -Force
Write-Host ">> Pronto: dist\$App-windows.zip"
Write-Host "   Para abrir: extraia e rode $App\$App.exe"
