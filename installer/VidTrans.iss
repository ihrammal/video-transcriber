; Accessible Video Transcriber -- Inno Setup installer script
;
; Build (after the application folder exists):
;     "C:\Users\<you>\AppData\Local\Programs\Inno Setup 6\ISCC.exe" installer\VidTrans.iss
; or simply:  python build.py
;
; The installer carries the whole application folder produced by VidTrans.spec:
;   {app}\AccessibleVideoTranscriber.exe   the program itself
;   {app}\ffmpeg.exe        standalone ffmpeg, resolvable from the exe's folder
;   {app}\models\base\      the Whisper recognition model, so the very first
;                           run works with the network unplugged
; plus the two licence files.  Everything is copied as one folder tree, so
; nothing can be forgotten when a file is added later.
;
; Pages: Select language -> Welcome -> License agreement (accept / decline
; radio buttons, no check box, shown once before anything is written) ->
; Select destination folder -> Select additional tasks -> Ready to install ->
; Installing -> Finished.
;
; Every shortcut points at {app}\{#MyAppExeName} -- never at this setup file --
; and the only [Run] entry launches the installed application.  No network is
; used at install time or on first run.

#define MyAppName "Accessible Video Transcriber"
#define MyAppVersion "1.1"
#define MyAppPublisher "Iman Rammal"
#define MyAppExeName "AccessibleVideoTranscriber.exe"
; Fixed id: upgrades and uninstall keep working between releases.
#define MyAppId "{{0ABD1C2E-8F42-4D3A-9CBD-6E3F7A2C1B04}"

; The folder build.py produces.  The second branch only exists so a developer
; running ISCC by hand still gets a useful error instead of a missing file.
#if DirExists(AddBackslash(SourcePath) + "..\build\app")
  #define AppDir "..\build\app"
#elif DirExists(AddBackslash(SourcePath) + "..\dist")
  #define AppDir "..\dist"
#else
  #define AppDir "..\build\app"
#endif

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoVersion=1.1.0.0
DefaultDirName={autopf}\Accessible Video Transcriber
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; Per-user installation: no administrator rights are needed and everything
; lands in %LocalAppData%\Programs, which is always writable.
PrivilegesRequired=lowest
MinVersion=10.0
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; --- wizard pages -----------------------------------------------------------
; More than one [Languages] entry switches the language selector on.
ShowLanguageDialog=yes
UsePreviousLanguage=yes
; The program was renamed: never reuse the previous folder or the previous
; Start Menu group of the old name, or the shortcuts would be created under
; "Video Transcript By Iman Rammal" again.
UsePreviousAppDir=no
UsePreviousGroup=no
UsePreviousTasks=yes
; The licence is presented once, here, before a single file is written.  The
; standard page already disables Next until "I accept" is chosen.
LicenseFile=..\resources\agreement_en.txt

; --- appearance -------------------------------------------------------------
SetupIconFile=..\app-icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
WizardStyle=modern
WizardImageFile=..\installer\splash\wiz-image.bmp
WizardSmallImageFile=..\installer\splash\wiz-small.bmp

; --- output -----------------------------------------------------------------
OutputDir=..\dist
OutputBaseFilename=AccessibleVideoTranscriberSetup-{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
CloseApplications=yes
LZMANumBlockThreads=4

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"; LicenseFile: "..\resources\agreement_en.txt"
Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"; LicenseFile: "..\resources\agreement_ar.txt"

[Tasks]
Name: "startmenuicon"; Description: "{cm:TaskStartMenu}"; GroupDescription: "{cm:TaskGroup}"
Name: "desktopicon"; Description: "{cm:TaskDesktop}"; GroupDescription: "{cm:TaskGroup}"

[Files]
; The complete application folder: program, standalone ffmpeg and the bundled
; speech model, in one entry so a new file cannot be left behind by accident.
Source: "{#AppDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\resources\agreement_en.txt"; DestDir: "{app}"; DestName: "License.txt"; Flags: ignoreversion
Source: "..\resources\agreement_ar.txt"; DestDir: "{app}"; DestName: "License.ar.txt"; Flags: ignoreversion
; The two detailed HTML documents opened from the Help menu (and the "Open
; guide file" / "Open shortcut file" actions): one pair per language.
Source: "..\resources\help\en\*.html"; DestDir: "{app}\help\en"; Flags: ignoreversion
Source: "..\resources\help\ar\*.html"; DestDir: "{app}\help\ar"; Flags: ignoreversion

[Icons]
; All shortcuts target the installed application, never the setup executable.
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Comment: "{cm:AppComment}"; Tasks: startmenuicon
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"; WorkingDir: "{app}"; Tasks: startmenuicon
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Comment: "{cm:AppComment}"; Tasks: desktopicon

[Run]
; The installed application is the only thing launched after setup: the
; postinstall option appears on the Finished page and is skipped silently.
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: postinstall skipifsilent nowait; WorkingDir: "{app}"

[CustomMessages]
; --- English --------------------------------------------------------------
english.TaskGroup=Shortcuts:
english.TaskStartMenu=Create a &Start Menu shortcut
english.TaskDesktop=Create a &desktop shortcut
english.AppComment=Video transcription, translation and subtitling
; --- Arabic ---------------------------------------------------------------
arabic.TaskGroup=الاختصارات:
arabic.TaskStartMenu=إنشاء اختصار في قائمة ابدأ
arabic.TaskDesktop=إنشاء اختصار على سطح المكتب
arabic.AppComment=تفريغ الفيديو وترجمته وإنشاء التسميات التوضيحية

[Code]
{ The standard License Agreement page supplied by Inno Setup already renders
  an "I accept the agreement" / "I do not accept the agreement" radio pair and
  keeps the Next button disabled until "accept" is picked.  Adding a second
  pair here used to put four radios on the screen, which is what made the
  agreement page look stuck.  No check box is used anywhere.

  The application itself never asks for acceptance again: vt_setup's welcome
  screen replaces the licence gate, so the words appear exactly once during
  setup and nowhere in the running program. }
