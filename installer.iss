#define MyAppName "MC Resource Table"
#define MyAppVersion "13.4"
#define MyAppExeName "MCResourceTable.exe"
[Setup]
AppId={{6A5E6C11-4C34-4F21-9C43-7C85A17F93D1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=MC Resource Table
DefaultDirName={autopf}\MC Resource Table
DefaultGroupName=MC Resource Table
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=output
OutputBaseFilename=MC_Resource_Table_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
[Files]
Source: "dist\MCResourceTable\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\MC Resource Table"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\MC Resource Table"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked
[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch MC Resource Table"; Flags: nowait postinstall skipifsilent
