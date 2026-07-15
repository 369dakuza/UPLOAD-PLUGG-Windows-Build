# Building for Windows

## Requirements

- Windows 10 or 11, 64-bit
- Python 3.12 64-bit with the `py` launcher
- Internet access during dependency installation
- [Inno Setup 6](https://jrsoftware.org/isinfo.php) for the installer
- Optional: a code-signing certificate for distributable releases

## One-command build

Open PowerShell in the project root and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build_windows.ps1
```

The script creates `.venv`, installs pinned dependency ranges, generates the icon, runs every automated test, compiles the PyInstaller directory build, creates the portable ZIP and invokes Inno Setup.

Outputs:

- `dist\UPLOAD PLUGG\UPLOAD PLUGG.exe` — standalone directory build
- `dist\UPLOAD_PLUGG_1.0.1_Portable.zip` — portable package
- `dist\UPLOAD_PLUGG_1.0.1_Update.exe` — installer and in-place updater

To omit Inno Setup while testing the executable:

```powershell
.\build_windows.ps1 -SkipInstaller
```

## Manual commands

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe build\generate_icon.py
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\pyinstaller.exe --noconfirm --clean "UPLOAD_PLUGG.spec"
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" "installer\UPLOAD_PLUGG.iss"
```

## Build design

PyInstaller creates an onedir application because it starts faster and is less likely to trigger antivirus heuristics than a self-extracting one-file executable. The installer places the complete directory under Program Files and creates the normal uninstall record, Start Menu entry and optional desktop shortcut. Runtime configuration stays under `%LOCALAPPDATA%\UploadPlugg`.

Before a public release, build in a clean Windows virtual machine, review third-party licenses, sign both the executable and installer, scan the artifacts, and perform the manual checklist in `TEST_PLAN.md`.
