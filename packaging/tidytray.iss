; Inno Setup script for the Windows installer.
; Build after PyInstaller has produced dist\TidyTray\ :
;   iscc /DMyAppVersion=1.0.0 packaging\tidytray.iss
; Installs for the current user only, so no administrator rights are needed.

#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif

[Setup]
AppId={{6F3C2A8E-5B1D-4C7A-9E2F-7A1B3C4D5E6F}
AppName=TidyTray
AppVersion={#MyAppVersion}
AppPublisher=HyderJavaid
AppCopyright=Copyright (c) 2026 HyderJavaid
AppPublisherURL=https://github.com/HyderJavaid/tidytray
LicenseFile=..\LICENSE
DefaultDirName={localappdata}\Programs\TidyTray
DefaultGroupName=TidyTray
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=TidyTray-{#MyAppVersion}-windows-setup
SetupIconFile=tidytray.ico
UninstallDisplayIcon={app}\TidyTray.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\TidyTray\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userprograms}\TidyTray"; Filename: "{app}\TidyTray.exe"
Name: "{userdesktop}\TidyTray"; Filename: "{app}\TidyTray.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\TidyTray.exe"; Description: "Start TidyTray"; Flags: nowait postinstall skipifsilent
