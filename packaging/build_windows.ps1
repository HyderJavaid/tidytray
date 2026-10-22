# Build the Windows portable zip and installer into dist\.
# Run from the project root in PowerShell with the virtual environment active:
#   python -m pip install -r requirements.txt pyinstaller
#   .\packaging\build_windows.ps1
# The installer step needs Inno Setup 6 (https://jrsoftware.org/isdl.php, or: winget install JRSoftware.InnoSetup).
$ErrorActionPreference = "Stop"

$version = python -c "import tidytray; print(tidytray.__version__)"

pyinstaller --noconfirm --clean --windowed --name TidyTray --icon packaging\tidytray.ico run_tidytray.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

# License texts travel with every build.
Copy-Item LICENSE, THIRD_PARTY_NOTICES.md, README.md dist\TidyTray\

# Portable: unzip anywhere and run TidyTray\TidyTray.exe. No install, no admin.
Compress-Archive -Path dist\TidyTray -DestinationPath "dist\TidyTray-$version-windows-x64-portable.zip" -Force

# Installer (per-user, no admin).
$iscc = (Get-Command iscc -ErrorAction SilentlyContinue).Source
if (-not $iscc) {
    foreach ($candidate in @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe", "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe")) {
        if (Test-Path $candidate) { $iscc = $candidate; break }
    }
}
if (-not $iscc) { throw "Inno Setup 6 (ISCC.exe) not found; the portable zip was still built." }
& $iscc "/DMyAppVersion=$version" packaging\tidytray.iss
if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed" }

Get-ChildItem dist\*.zip, dist\*.exe
