#ifndef AppVersion
  #error Run packaging/windows/build.py to supply the application version.
#endif

[Setup]
AppId=io.github.boxu_pku.MULTI1Dvisual
AppName=MULTI1Dvisual
AppVersion={#AppVersion}
AppPublisher=Bo Xu
VersionInfoVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\MULTI1Dvisual
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
DisableProgramGroupPage=yes
WizardStyle=modern
ShowLanguageDialog=yes
SetupIconFile=..\..\resources\icons\multi1dvisual.ico
UninstallDisplayIcon={app}\MULTI1Dvisual.exe
OutputDir=..\..\dist
OutputBaseFilename=MULTI1Dvisual-Setup-{#AppVersion}-x64
Compression=lzma2/fast
SolidCompression=yes

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "zhcn"; MessagesFile: "ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\..\build\windows\bundle\MULTI1Dvisual\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\README*.md"; DestDir: "{app}\manual"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}\manual\packaging"; Flags: ignoreversion
Source: "..\..\resources\icons\multi1dvisual.png"; DestDir: "{app}\manual\resources\icons"; Flags: ignoreversion
Source: "..\..\docs\manual_CN\multi1dvisual_manual_zh.pdf"; DestDir: "{app}\manual\docs\manual_CN"; Flags: ignoreversion
Source: "..\..\docs\manual_EN\multi1dvisual_manual_en.pdf"; DestDir: "{app}\manual\docs\manual_EN"; Flags: ignoreversion
Source: "..\..\docs\examples\quickstart.zip"; DestDir: "{app}\manual\docs\examples"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\MULTI1Dvisual"; Filename: "{app}\MULTI1Dvisual.exe"
Name: "{autodesktop}\MULTI1Dvisual"; Filename: "{app}\MULTI1Dvisual.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\MULTI1Dvisual.exe"; Description: "{cm:LaunchProgram,MULTI1Dvisual}"; Flags: nowait postinstall skipifsilent
