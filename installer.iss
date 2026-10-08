; Inno Setup script for Accessible Video Transcriber and Translator
; Requires Inno Setup 6.3 or newer (needed for the x64compatible setting).
;
; OldAppGuid is the AppId of the OLD installer (installer\VidTrans.iss), so the
; old per-user copy can be found and removed. Keep the single braces here.

#define AppName "Accessible Video Transcriber"
#define AppVersion "1.2.0"
#define AppPublisher "Iman Rammal"
#define ExeName "AccessibleVideoTranscriber.exe"
#define DistFolder "dist\AccessibleVideoTranscriber"
#define OldFolderName "Accessible Video Transcriber"
#define OldAppGuid "{0ABD1C2E-8F42-4D3A-9CBD-6E3F7A2C1B04}"

[Setup]
; Two opening braces here is correct. It is how Inno Setup writes one brace.
AppId={{8F3A6C21-5B7D-4E94-A1C2-3D9E7F0B4A56}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#ExeName}
LicenseFile=resources\agreement_en.txt
OutputDir=installer_output
OutputBaseFilename=AccessibleVideoTranscriber_Setup_{#AppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

; 64-bit install into the real Program Files folder
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Default is all users (needs administrator). The dialog option makes Setup
; ask at the start: install for all users, or for the current user only.
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "startmenuicon"; Description: "Create a &Start menu shortcut"; GroupDescription: "Additional shortcuts:"
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
; Everything PyInstaller produced: the program, Whisper, libraries, ffmpeg,
; the help folder and any bundled models.
Source: "{#DistFolder}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; The licence files the program and the build checks look for in the install
; folder (the same files the 1.1 installer shipped).
Source: "resources\agreement_en.txt"; DestDir: "{app}"; DestName: "License.txt"; Flags: ignoreversion
Source: "resources\agreement_ar.txt"; DestDir: "{app}"; DestName: "License.ar.txt"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#ExeName}"; WorkingDir: "{app}"; Tasks: startmenuicon
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#ExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#ExeName}"; Description: "Launch {#AppName}"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent

[Code]
{ Runs after the Ready page and also in silent installs.
  Looks for the old per-user copy in AppData Local Programs, asks to remove
  it, then removes it. Returning text from this function stops the install. }
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  KeyPath, OldDir, InstLoc, UninstallCmd, Msg: String;
  HasKey: Boolean;
  ResultCode, I: Integer;
begin
  Result := '';
  KeyPath := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#OldAppGuid}_is1';
  OldDir := ExpandConstant('{localappdata}\Programs\{#OldFolderName}');
  HasKey := RegKeyExists(HKCU, KeyPath);

  if HasKey then
    if RegQueryStringValue(HKCU, KeyPath, 'InstallLocation', InstLoc) then
      OldDir := InstLoc;
  OldDir := RemoveBackslash(OldDir);

  { Nothing old found: carry on }
  if (not HasKey) and (not DirExists(OldDir)) then
    Exit;

  Msg := 'An older copy of {#AppName} was found in this folder:' + #13#10 + #13#10 +
         OldDir + #13#10 + #13#10 +
         'It must be removed before the new version can be installed. ' +
         'Your settings and saved files in your user data folder are not deleted.' + #13#10 + #13#10 +
         'Remove the older copy now and continue?';

  if SuppressibleMsgBox(Msg, mbConfirmation, MB_YESNO, IDYES) = IDNO then
  begin
    Result := 'Installation was stopped because the older copy was not removed.';
    Exit;
  end;

  { Preferred way: run the old uninstaller so shortcuts and registry entries go too }
  if HasKey then
    if RegQueryStringValue(HKCU, KeyPath, 'UninstallString', UninstallCmd) then
    begin
      Exec(RemoveQuotes(UninstallCmd), '/VERYSILENT /NORESTART /SUPPRESSMSGBOXES', '',
           SW_HIDE, ewWaitUntilTerminated, ResultCode);
      { The Inno uninstaller relaunches itself from a temp folder, so wait for it }
      I := 0;
      while FileExists(OldDir + '\unins000.exe') and (I < 75) do
      begin
        Sleep(200);
        I := I + 1;
      end;
    end;

  { Fallback: delete whatever is left of the old folder }
  if DirExists(OldDir) then
    DelTree(OldDir, True, True, True);

  if DirExists(OldDir) then
    Result := 'The older copy could not be removed completely. ' +
              'Please close the program, delete this folder by hand, and run Setup again: ' + OldDir;
end;
