; Script pour Inno Setup 6

[Setup]
AppId=45B35AD4-7BE5-44E4-AE07-B599650D1942
AppName=Automatisation ECMO
#ifndef AppVersion
#define AppVersion "0.1.0"
#endif
AppVersion={#AppVersion}
DefaultDirName={autopf}\Automatisation ECMO
DefaultGroupName=Automatisation ECMO
PrivilegesRequired=admin
OutputBaseFilename=Automatisation_ECMO_Setup_{#AppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}";
Name: "installtexlive"; Description: "Installer TeXLive (téléchargement requis)"; GroupDescription: "Dépendances requises :";

[Files]
; CORRECTION: Assuming 'onedir' output. 
; Point to the FOLDER content, not just main.exe.
; If your PyInstaller output is in "dist\Automatisation ECMO", use that path.
Source: "dist\main\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Automatisation ECMO"; Filename: "{app}\main.exe"
Name: "{autodesktop}\Automatisation ECMO"; Filename: "{app}\main.exe"; Tasks: desktopicon

[Run]
; Note: install-tl-windows.exe might require specific parameters for a truly silent install 
; (e.g., -gui=text or -profile=...). "/quiet" is a generic placeholder.
Filename: "{tmp}\install-tl-windows.exe"; Parameters: "-gui=text"; Tasks: installtexlive; Flags: waituntilterminated; Check: PrepareTexLiveDownload
Filename: "{app}\main.exe"; Description: "{cm:LaunchProgram,Automatisation ECMO}"; Flags: nowait postinstall shellexec

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
// SECTION CODE : Inno Setup 6 Native Downloader

var
  // We declare the URL globally so it's easy to change
  TexLiveURL: String;

function PrepareTexLiveDownload: Boolean;
var
  DownloadPage: TDownloadWizardPage;
begin
  // 1. Check if the task is selected
  if not IsTaskSelected('installtexlive') then
  begin
    Result := True; // We return True to allow the installation to proceed (the [Run] entry has its own task check)
    Exit;
  end;

  // 2. Define the URL (Direct link to the .exe)
  TexLiveURL := 'https://mirror.ctan.org/systems/texlive/tlnet/install-tl-windows.exe';

  // 3. Create the native download page
  DownloadPage := CreateDownloadPage(SetupMessage(msgWizardPreparing), 'Téléchargement de TeXLive...', @OnDownloadProgress);
  DownloadPage.Clear;
  
  // Add the file to the download queue
  // Parameters: URL, Filename, SHA256 (optional, empty string to skip)
  DownloadPage.Add(TexLiveURL, 'install-tl-windows.exe', '');

  DownloadPage.Show;
  
  try
    try
      // 4. Start the download
      DownloadPage.Download; 
      Log('Téléchargement de TeXLive réussi.');
      Result := True;
    except
      // Handle errors (network, etc.)
      Log('Exception lors du téléchargement: ' + GetExceptionMessage);
      SuppressibleMsgBox('Erreur lors du téléchargement de TeXLive :' + #13#10 + GetExceptionMessage, mbError, MB_OK, IDOK);
      Result := False;
    end;
  finally
    DownloadPage.Hide;
  end;
end;