param(
  [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

if (-not (Test-Path ".venv")) {
  if (Get-Command py -ErrorAction SilentlyContinue) {
    py -3.12 -m venv .venv
  } else {
    python -m venv .venv
  }
}

& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements-dev.txt
& ".\.venv\Scripts\python.exe" build\generate_icon.py
$env:PYTHONPATH = "$ProjectRoot\src"
& ".\.venv\Scripts\python.exe" -m unittest discover -s tests -v
& ".\.venv\Scripts\pyinstaller.exe" --noconfirm --clean "UPLOAD_PLUGG.spec"

$PortableZip = Join-Path $ProjectRoot "dist\UPLOAD_PLUGG_1.0.0_Portable.zip"
if (Test-Path $PortableZip) { Remove-Item $PortableZip -Force }
Compress-Archive -Path "dist\UPLOAD PLUGG\*" -DestinationPath $PortableZip

if (-not $SkipInstaller) {
  $Iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
  if (-not (Test-Path $Iscc)) {
    throw "Inno Setup 6 was not found. Install it or run .\build_windows.ps1 -SkipInstaller."
  }
  & $Iscc "installer\UPLOAD_PLUGG.iss"
}

Write-Host "Build complete. Files are in dist\."
