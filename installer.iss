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
; Note : Si vous êtes en mode 'onedir', assurez-vous que cela copie tout le dossier, pas juste l'exe.
; Si 'dist' contient un dossier 'Automatisation ECMO', mettez "dist\Automatisation ECMO\*"
Source: "dist\main\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Automatisation ECMO"; Filename: "{app}\main.exe"
Name: "{autodesktop}\Automatisation ECMO"; Filename: "{app}\main.exe"; Tasks: desktopicon

[Run]
; L'installation de TeXLive se fait ici. Inno Setup ignorera désormais la demande de reboot venant de ce fichier.
Filename: "{tmp}\install-tl-windows.exe"; Parameters: "-gui=text"; Tasks: installtexlive; Flags: waituntilterminated; Check: PrepareTexLiveDownload
Filename: "{app}\main.exe"; Description: "{cm:LaunchProgram,Automatisation ECMO}"; Flags: nowait postinstall shellexec

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
var
  TexLiveURL: String;

function PrepareTexLiveDownload: Boolean;
var
  DownloadPage: TDownloadWizardPage;
begin
  // 1. Si la tâche n'est pas cochée, on continue.
  if not IsTaskSelected('installtexlive') then
  begin
    Result := True;
    Exit;
  end;

  // 2. URL directe
  TexLiveURL := 'https://mirror.ctan.org/systems/texlive/tlnet/install-tl-windows.exe';

  // 3. Création page de téléchargement
  DownloadPage := CreateDownloadPage(SetupMessage(msgWizardPreparing), 'Téléchargement de TeXLive...', nil);
  
  DownloadPage.Clear;
  DownloadPage.Add(TexLiveURL, 'install-tl-windows.exe', '');
  
  DownloadPage.Show;

  try
    try
      DownloadPage.Download;
      Log('Téléchargement de TeXLive réussi.');
      Result := True;
    except
      Log('Exception lors du téléchargement: ' + GetExceptionMessage);
      SuppressibleMsgBox('Erreur lors du téléchargement de TeXLive :' + #13#10 + GetExceptionMessage, mbError, MB_OK, IDOK);
      Result := False;
    end;
  finally
    DownloadPage.Hide;
  end;
end;