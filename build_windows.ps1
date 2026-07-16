param(
  [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

function Assert-LastExitCode([string]$Step) {
  if ($LASTEXITCODE -ne 0) {
    throw "$Step failed with exit code $LASTEXITCODE."
  }
}

if (-not (Test-Path ".venv")) {
  if (Get-Command py -ErrorAction SilentlyContinue) {
    py -3.12 -m venv .venv
  } else {
    python -m venv .venv
  }
  Assert-LastExitCode "Creating the Python environment"
}

& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
Assert-LastExitCode "Updating pip"
& ".\.venv\Scripts\python.exe" -m pip install -r requirements-dev.txt
Assert-LastExitCode "Installing dependencies"
& ".\.venv\Scripts\python.exe" build\generate_icon.py
Assert-LastExitCode "Generating the application icon"
$env:PYTHONPATH = "$ProjectRoot\src"
& ".\.venv\Scripts\python.exe" -m unittest discover -s tests -v
Assert-LastExitCode "Running automated tests"
& ".\.venv\Scripts\pyinstaller.exe" --noconfirm --clean "UPLOAD_PLUGG.spec"
Assert-LastExitCode "Building the Windows executable"

$PortableZip = Join-Path $ProjectRoot "dist\UPLOAD_PLUGG_1.0.2_Portable.zip"
if (Test-Path $PortableZip) { Remove-Item $PortableZip -Force }
Compress-Archive -Path "dist\UPLOAD PLUGG\*" -DestinationPath $PortableZip

if (-not $SkipInstaller) {
  $Iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
  if (-not (Test-Path $Iscc)) {
    throw "Inno Setup 6 was not found. Install it or run .\build_windows.ps1 -SkipInstaller."
  }
  & $Iscc "installer\UPLOAD_PLUGG.iss"
  Assert-LastExitCode "Building the Windows installer"
}

Write-Host "Build complete. Files are in dist\."
