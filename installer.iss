[Setup]
AppName=MonAppLatex
AppVersion=1.0
DefaultDirName={pf}\MonAppLatex
DefaultGroupName=MonAppLatex
OutputBaseFilename=MonAppLatexSetup
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\main.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "resources\*"; DestDir: "{app}\resources"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\MonAppLatex"; Filename: "{app}\main.exe"

[Run]
Filename: "{app}\main.exe"; Description: "Lancer MonAppLatex"; Flags: nowait postinstall skipifsilent
