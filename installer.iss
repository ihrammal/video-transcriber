; Inno Setup script for Accessible Video Transcriber and Translator
; Requires Inno Setup 6.3 or newer (needed for the x64compatible setting).
;
; OldAppGuid is the AppId of the OLD installer (installer\VidTrans.iss), so the
; old per-user copy can be found and removed. Keep the single braces here.

#define AppName "Accessible Media Transcriber"
#define AppVersion "1.3.1"
#define AppPublisher "Iman Rammal"
#define ExeName "AccessibleVideoTranscriber.exe"
#ifndef DistFolder
  #define DistFolder "dist\AccessibleVideoTranscriber"
#endif
#define OldFolderName "Accessible Video Transcriber"
#define OldAppGuid "{0ABD1C2E-8F42-4D3A-9CBD-6E3F7A2C1B04}"
#define AppIdentity "{{8F3A6C21-5B7D-4E94-A1C2-3D9E7F0B4A56}"
#define BuildSuffix ""
#ifdef ValidationInstall
  #undef AppName
  #define AppName "Accessible Media Transcriber QA"
  #undef AppIdentity
  #define AppIdentity "{{CE980EF4-4F4A-4EED-A2B7-639C605C9B14}"
  #undef BuildSuffix
  #define BuildSuffix "_QA"
#endif

[Setup]
; Two opening braces here is correct. It is how Inno Setup writes one brace.
AppId={#AppIdentity}
AppName={cm:ProductName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableDirPage=no
AllowNoIcons=no
UninstallDisplayIcon={app}\{#ExeName}
LicenseFile=resources\agreement_en.txt
OutputDir=installer_output
OutputBaseFilename=AccessibleMediaTranscriber_Setup_{#AppVersion}{#BuildSuffix}
#ifdef ValidationInstall
; Keep repeated local installer checks fast; release builds stay compressed.
Compression=none
SolidCompression=no
#else
Compression=lzma2
SolidCompression=yes
#endif
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
Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"; LicenseFile: "resources\agreement_ar.txt"

[CustomMessages]
#ifdef ValidationInstall
english.ProductName=Accessible Media Transcriber QA
arabic.ProductName=مفرّغ الوسائط الميسّر، نسخة اختبار
#else
english.ProductName=Accessible Media Transcriber
arabic.ProductName=مفرّغ الوسائط الميسّر
#endif
english.InstallType=Installation type
arabic.InstallType=نوع التثبيت
english.InstallTypeTitle=Choose express or custom installation
arabic.InstallTypeTitle=اختر التثبيت السريع أو المخصص
english.InstallTypeHint=Express installs automatically in the default folder and creates a Start menu shortcut. Custom lets you choose the folder and shortcuts.
arabic.InstallTypeHint=يثبّت الخيار السريع البرنامج تلقائيًا في المجلد الافتراضي ويضيف اختصار قائمة ابدأ. يتيح لك الخيار المخصص اختيار المجلد والاختصارات.
english.Express=Express installation (recommended)
arabic.Express=تثبيت سريع (موصى به)
english.Custom=Custom installation
arabic.Custom=تثبيت مخصص
english.StartShortcut=Create a &Start menu shortcut
arabic.StartShortcut=إنشاء اختصار في قائمة ا&بدأ
english.DesktopShortcut=Create a &desktop shortcut
arabic.DesktopShortcut=إنشاء اختصار على &سطح المكتب
english.Shortcuts=Additional shortcuts:
arabic.Shortcuts=اختصارات إضافية:
english.Launch=Launch Accessible Media Transcriber
arabic.Launch=تشغيل مفرّغ الوسائط الميسّر
english.Offline=Install an offline transcription model (clear for API-only use)
arabic.Offline=تثبيت نموذج تفريغ دون اتصال (أزل التحديد لاستخدام الواجهات البرمجية فقط)
english.ModelGroup=Offline transcription:
arabic.ModelGroup=التفريغ دون اتصال:
english.Tiny=Tiny - fastest, about 75 MB
arabic.Tiny=صغير جدًا (Tiny) - الأسرع، نحو ٧٥ ميغابايت
english.Base=Base - balanced, about 145 MB (recommended)
arabic.Base=أساسي (Base) - متوازن، نحو ١٤٥ ميغابايت (موصى به)
english.Small=Small - about 484 MB, needs more memory
arabic.Small=صغير (Small) - نحو ٤٨٤ ميغابايت، يحتاج إلى ذاكرة أكثر
english.OlderCopy=An older copy of Accessible Video Transcriber was found in this folder:
arabic.OlderCopy=عُثر على نسخة سابقة من مفرّغ الفيديو الميسّر في هذا المجلد:
english.RemoveOlder=It must be removed before the new version can be installed. Your settings and saved files in your user data folder are not deleted.
arabic.RemoveOlder=يجب إزالة النسخة السابقة قبل تثبيت الإصدار الجديد. لن تُحذف الإعدادات والملفات المحفوظة في مجلد بيانات المستخدم.
english.RemoveQuestion=Remove the older copy now and continue?
arabic.RemoveQuestion=هل تريد إزالة النسخة السابقة الآن والمتابعة؟
english.RemovalDeclined=Installation was stopped because the older copy was not removed.
arabic.RemovalDeclined=توقف التثبيت لأن النسخة السابقة لم تُزل.
english.RemovalIncomplete=The older copy could not be removed completely. Please close the program, review the remaining folder, and run Setup again:
arabic.RemovalIncomplete=تعذّرت إزالة النسخة السابقة بالكامل. أغلق البرنامج وراجع المجلد المتبقي ثم شغّل المثبّت مجددًا:

[Tasks]
Name: "startmenuicon"; Description: "{cm:StartShortcut}"; GroupDescription: "{cm:Shortcuts}"
Name: "desktopicon"; Description: "{cm:DesktopShortcut}"; GroupDescription: "{cm:Shortcuts}"; Flags: unchecked
Name: "offline"; Description: "{cm:Offline}"; GroupDescription: "{cm:ModelGroup}"
Name: "offline\base"; Description: "{cm:Base}"; Flags: exclusive
Name: "offline\tiny"; Description: "{cm:Tiny}"; Flags: exclusive unchecked
Name: "offline\small"; Description: "{cm:Small}"; Flags: exclusive unchecked

[Files]
; Everything PyInstaller produced: the program, Whisper, libraries, ffmpeg,
; the help folder and any bundled models.
Source: "{#DistFolder}\*"; DestDir: "{app}"; Excludes: "\models\*"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#DistFolder}\models\tiny\*"; DestDir: "{app}\models\tiny"; Tasks: offline\tiny; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#DistFolder}\models\base\*"; DestDir: "{app}\models\base"; Tasks: offline\base; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#DistFolder}\models\small\*"; DestDir: "{app}\models\small"; Tasks: offline\small; Flags: ignoreversion recursesubdirs createallsubdirs
; The licence files the program and the build checks look for in the install
; folder (the same files the 1.1 installer shipped).
Source: "resources\agreement_en.txt"; DestDir: "{app}"; DestName: "License.txt"; Flags: ignoreversion
Source: "resources\agreement_ar.txt"; DestDir: "{app}"; DestName: "License.ar.txt"; Flags: ignoreversion
Source: "THIRD-PARTY-LICENSES.md"; DestDir: "{app}"; Flags: ignoreversion

[INI]
Filename: "{app}\installed-model.ini"; Section: "transcription"; Key: "model"; String: "tiny"; Tasks: offline\tiny
Filename: "{app}\installed-model.ini"; Section: "transcription"; Key: "model"; String: "base"; Tasks: offline\base
Filename: "{app}\installed-model.ini"; Section: "transcription"; Key: "model"; String: "small"; Tasks: offline\small

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#ExeName}"; WorkingDir: "{app}"; Tasks: startmenuicon
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#ExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[UninstallDelete]
Type: files; Name: "{app}\installed-model.ini"

[InstallDelete]
Type: files; Name: "{autodesktop}\{#AppName}.lnk"; Tasks: not desktopicon
Type: files; Name: "{group}\{#AppName}.lnk"; Tasks: not startmenuicon
#ifndef ValidationInstall
Type: files; Name: "{autodesktop}\Accessible Video Transcriber.lnk"
Type: files; Name: "{autoprograms}\Accessible Video Transcriber\Accessible Video Transcriber.lnk"
#endif

[Run]
Filename: "{app}\{#ExeName}"; Description: "{cm:Launch}"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent

[Code]
var
  InstallModePage: TInputOptionWizardPage;
  ExpressDir: String;

procedure InitializeWizard;
begin
  ExpressDir := WizardDirValue;
  InstallModePage := CreateInputOptionPage(wpLicense,
    CustomMessage('InstallType'), CustomMessage('InstallTypeTitle'),
    CustomMessage('InstallTypeHint'), True, False);
  InstallModePage.Add(CustomMessage('Express'));
  InstallModePage.Add(CustomMessage('Custom'));
  InstallModePage.SelectedValueIndex := 0;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := (InstallModePage.SelectedValueIndex = 0) and
    ((PageID = wpSelectDir) or (PageID = wpSelectProgramGroup) or
     (PageID = wpSelectTasks) or (PageID = wpReady));
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (CurPageID = InstallModePage.ID) and (InstallModePage.SelectedValueIndex = 0) then
  begin
    WizardForm.DirEdit.Text := ExpressDir;
    WizardForm.GroupEdit.Text := '{#AppName}';
    WizardSelectTasks('startmenuicon,offline,offline\base');
  end;
end;

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
#ifdef ValidationInstall
  { QA has its own identity, folder and shortcuts; never touch a real install. }
  Exit;
#endif
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

  Msg := CustomMessage('OlderCopy') + #13#10 + #13#10 +
         OldDir + #13#10 + #13#10 +
         CustomMessage('RemoveOlder') + #13#10 + #13#10 +
         CustomMessage('RemoveQuestion');

  if SuppressibleMsgBox(Msg, mbConfirmation, MB_YESNO, IDNO) = IDNO then
  begin
    Result := CustomMessage('RemovalDeclined');
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

  { Never recursively delete a directory obtained from a registry value.
    Leave leftovers for review if the registered uninstaller cannot finish. }
  if DirExists(OldDir) then
    Result := CustomMessage('RemovalIncomplete') + ' ' + OldDir;
end;
