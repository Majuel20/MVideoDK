; ==========================================================
; Inno Setup script para MVideoDK (FINAL)
; - Licencia antes de instalar
; - Copia docs a {app}\docs
; - Página extra (Aceptar) con instrucciones
; - Página final NORMAL con casilla para ejecutar y Finalizar
; - Sin botón "Abrir carpeta"
; - Oculta "Atrás" en EULA e inicio
; ==========================================================

#define MyAppName        "MVideoDK"
#define MyAppVersion     "1.0.0"
#define MyAppPublisher   "Majuel20"

#define MyLauncherFile   "MVideoDK.exe"

#define SourceProgramDir     "..\..\3_Package_Final\Programa"
#define SourceProgramDataDir "..\..\2_Installer_Resources\ProgramData\MVideoDK"
#define SourceDocsDir        "docs"


[Setup]
AppId={{2C4C417B-7E3F-4D51-9E04-3C1C6C4F1234}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}

DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

SetupIconFile=MVideoDK_ico.ico
UninstallDisplayIcon={app}\{#MyLauncherFile}

OutputDir=Output
OutputBaseFilename={#MyAppName}-Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin

ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64

LicenseFile={#SourceDocsDir}\EULA_MVideoDK.txt


[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"


[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; \
GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked


[Dirs]
Name: "{app}\docs"


[Files]
Source: "{#SourceProgramDir}\*"; DestDir: "{app}"; \
  Flags: recursesubdirs createallsubdirs ignoreversion

Source: "{#SourceDocsDir}\*"; DestDir: "{app}\docs"; Flags: ignoreversion

Source: "{#SourceProgramDataDir}\*"; DestDir: "{commonappdata}\MVideoDK"; \
  Flags: recursesubdirs createallsubdirs ignoreversion

Source: "{#SourceProgramDataDir}\Apk\*"; \
  DestDir: "{userdocs}\..\Downloads\MVideoDK_resources\Apk"; \
  Flags: recursesubdirs createallsubdirs ignoreversion

Source: "{#SourceProgramDataDir}\Extension\*"; \
  DestDir: "{userdocs}\..\Downloads\MVideoDK_resources\Extension"; \
  Flags: recursesubdirs createallsubdirs ignoreversion


[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyLauncherFile}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyLauncherFile}"; Tasks: desktopicon

Name: "{group}\README - Cómo usar MVideoDK"; Filename: "{app}\docs\README_Installed.txt"
Name: "{group}\Créditos y licencias"; Filename: "{app}\docs\THIRD_PARTY_NOTICES.txt"


; ==========================================================
; PÁGINA EXTRA ANTES DE FINALIZAR (ACEPTAR)
; ==========================================================
[Code]
var
  ExtPage: TWizardPage;
  ExtMemo: TMemo;

function DownloadsBasePath(): string;
begin
  Result := ExpandConstant('{userdocs}') + '\..\Downloads';
end;

function ExtensionFolderPath(): string;
begin
  Result := DownloadsBasePath() + '\MVideoDK_resources\Extension';
end;

procedure InitializeWizard();
var
  instructions: string;
begin
  { Página extra después de instalar y antes de la pantalla final }
  ExtPage := CreateCustomPage(
    wpInstalling,
    'Extensión del navegador (opcional)',
    'Lee estas instrucciones antes de finalizar.'
  );

  ExtMemo := TMemo.Create(ExtPage);
  ExtMemo.Parent := ExtPage.Surface;
  ExtMemo.Left := 0;
  ExtMemo.Top := 0;
  ExtMemo.Width := ExtPage.SurfaceWidth;
  ExtMemo.Height := ExtPage.SurfaceHeight;
  ExtMemo.ReadOnly := True;
  ExtMemo.ScrollBars := ssVertical;
  ExtMemo.WordWrap := True;

  instructions :=
    '✅ Instalación completada.' + #13#10 + #13#10 +
    'La extensión del navegador es OPCIONAL (complementaria).' + #13#10 +
    'MVideoDK funciona sin la extensión, pero con la extensión tendrás funciones extra.' + #13#10 + #13#10 +
    'Si deseas instalar la extensión:' + #13#10 +
    '1) Abre tu navegador (Brave / Chrome / Edge).' + #13#10 +
    '2) Ve a Extensiones.' + #13#10 +
    '3) Activa "Modo desarrollador".' + #13#10 +
    '4) Pulsa "Cargar descomprimida" / "Load unpacked".' + #13#10 +
    '5) Selecciona la carpeta:' + #13#10 +
    '   Descargas\MVideoDK_resources\Extension' + #13#10 + #13#10 +
    'Ruta exacta:' + #13#10 +
    ExtensionFolderPath() + #13#10 + #13#10 +
    'Nota: La extensión funcionará mientras el modo desarrollador esté habilitado.';

  ExtMemo.Lines.Text := instructions;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  { --- Ocultar "Atrás" donde no tiene sentido --- }
  { Bien al inicio (Welcome) y en Licencia (EULA) }
  if (CurPageID = wpWelcome) or (CurPageID = wpLicense) then
    WizardForm.BackButton.Visible := False
  else
    WizardForm.BackButton.Visible := True;

  { En nuestra página extra, el botón debe decir Aceptar }
  if CurPageID = ExtPage.ID then
  begin
    WizardForm.BackButton.Visible := False;
    WizardForm.NextButton.Caption := 'Aceptar';
  end;

  { En la pantalla final, restaurar textos normales }
  if CurPageID = wpFinished then
  begin
    WizardForm.NextButton.Caption := SetupMessage(msgButtonFinish);
    WizardForm.RunList.Visible := True;  { casilla para ejecutar }
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  base: string;
begin
  if CurStep = ssInstall then
  begin
    base := DownloadsBasePath() + '\MVideoDK_resources';
    ForceDirectories(base);
    ForceDirectories(base + '\Apk');
    ForceDirectories(base + '\Extension');
  end;
end;


[Run]
Filename: "{app}\{#MyLauncherFile}"; Description: "Iniciar {#MyAppName}"; \
Flags: postinstall nowait skipifsilent
