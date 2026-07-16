#define MyAppName "UPLOAD PLUGG"
#define MyAppVersion "1.0.4"
#define MyAppPublisher "Dakuza"
#define MyAppExeName "UPLOAD PLUGG.exe"

[Setup]
AppId={{835F269F-1F05-4923-8259-C69839A67C77}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\UPLOAD PLUGG
DefaultGroupName=UPLOAD PLUGG
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=UPLOAD_PLUGG_1.0.4_Update
SetupIconFile=..\resources\upload_plugg.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName=UPLOAD PLUGG
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
VersionInfoCompany=Dakuza
VersionInfoDescription=UPLOAD PLUGG Installer
VersionInfoProductName=UPLOAD PLUGG
VersionInfoProductVersion=1.0.4

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\UPLOAD PLUGG\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\UPLOAD PLUGG"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\UPLOAD PLUGG"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch UPLOAD PLUGG"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

; User history and settings in %LOCALAPPDATA%\UploadPlugg are intentionally preserved.
