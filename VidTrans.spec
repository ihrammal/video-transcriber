# -*- mode: python ; coding: utf-8 -*-
# Accessible Video Transcriber application (folder build, windowed).
#
#   pyinstaller --noconfirm VidTrans.spec
#
# Entry point: vid_trans_app.py -- shows the welcome screen, then the
# application itself.  The splash is drawn by the bootloader, so the branded
# screen is on screen while the large payload is prepared; that is why the
# splash is attached to the executable.
#
# The result is a FOLDER build: dist\AccessibleVideoTranscriber\ holds
# AccessibleVideoTranscriber.exe, the _internal folder with Python, Whisper,
# every library and the help folder, plus ffmpeg.exe and models\ copied
# beside it at the end of this file.  installer.iss packs exactly that
# folder, so the two names must stay identical.
#
# Two things are deliberately copied in as plain files and not collected:
# ffmpeg.exe and models\.  Both are large, neither is Python, and a user
# must be able to see and replace them.

import glob
import os
import shutil
import sysconfig

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VarFileInfo,
    VarStruct,
    VSVersionInfo,
)

# The release version of the program, written into the properties of the
# executable.  It must match update_checker.APP_VERSION, installer.iss and
# vt_bootstrap.APP_VERSION.
VERSION = (1, 2, 0, 0)
VERSION_INFO = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=VERSION,
        prodvers=VERSION,
        mask=0x3F,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0),
    ),
    kids=[
        StringFileInfo(
            kids=[
                StringTable(
                    name="040904B0",
                    kids=[
                        StringStruct("CompanyName", "Iman Rammal"),
                        StringStruct("FileDescription", "Accessible Video Transcriber and Translator"),
                        StringStruct("FileVersion", "1.2.0.0"),
                        StringStruct("InternalName", "AccessibleVideoTranscriber"),
                        StringStruct("LegalCopyright", "Copyright (c) Iman Rammal. Noncommercial use only."),
                        StringStruct("OriginalFilename", "AccessibleVideoTranscriber.exe"),
                        StringStruct("ProductName", "Accessible Video Transcriber"),
                        StringStruct("ProductVersion", "1.2.0.0"),
                    ],
                )
            ]
        ),
        VarFileInfo(kids=[VarStruct(name="Translation", kids=[1033, 1200])]),
    ],
)

# Several runtime packages read their own version through importlib.metadata at
# import time (imageio does it unconditionally).  Without the *.dist-info
# metadata next to them they raise PackageNotFoundError and moviepy dies as soon
# as it is imported, so every installed distribution metadata folder is shipped
# with the executable.
_PURELIB = sysconfig.get_paths()["purelib"]
DIST_INFOS = [
    (path, os.path.basename(path))
    for path in sorted(glob.glob(os.path.join(_PURELIB, "*.dist-info")))
]

# faster-whisper keeps its speech-activity model as a data file.  Analysis only
# follows imports, so the .onnx would silently vanish and every transcription
# with vad_filter=True would fail on the user's machine while working fine here.
FASTER_WHISPER_DATA = collect_data_files("faster_whisper")
FASTER_WHISPER_MODULES = collect_submodules("faster_whisper")

a = Analysis(
    ['vid_trans_app.py'],
    pathex=[],
    binaries=[],
    datas=DIST_INFOS
    + [('resources', 'resources')]
    + [('help', 'help')]  # the combined help guide (--add-data "help;help")
    + FASTER_WHISPER_DATA,
    hiddenimports=[
        'vt_setup',
        'vt_bootstrap',
        'vt_i18n',
        'vt_install',
        'vt_render',
        'vt_workers',
        # Imported with a plain "import ..." inside functions, so the
        # module graph cannot see them on its own.
        'vt_prefs',
        'vt_api',
        'vt_settings',
        'vt_a11y',
        'vt_secrets',
        'vt_e2e',
        'vt_help',
        'help_menu',
        'update_checker',
        'winsound',
        'onnxruntime',
    ] + FASTER_WHISPER_MODULES,
    hookspath=['installer/hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

splash = Splash(
    'installer/splash/splash.png',
    binaries=a.binaries,
    datas=a.datas,
    text_pos=(70, 200),
    text_size=13,
    text_color="#FFC107",
    text_font="Segoe UI",
    text_default="Preparing Accessible Video Transcriber...",
    minify_script=True,
    always_on_top=True,
    center='primary',
)

exe = EXE(
    pyz,
    splash,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AccessibleVideoTranscriber',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['app-icon.ico'],
    version=VERSION_INFO,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='AccessibleVideoTranscriber',
)

# ---------------------------------------------------------------- payload
# Everything below runs after dist\AccessibleVideoTranscriber exists.  The
# installer packs this folder as it is, so what lands here is what the user
# gets, and the running program finds both pieces next to its own executable.
DIST = os.path.abspath(os.path.join(DISTPATH, 'AccessibleVideoTranscriber'))

_ffmpeg_src = os.path.join(SPECPATH, "bin", "ffmpeg.exe")
if not os.path.isfile(_ffmpeg_src):
    # bin\ffmpeg.exe is a local folder and may be absent (it is not kept in
    # the repository).  The imageio-ffmpeg package ships the identical binary,
    # and a frozen build must have a standalone copy beside the executable.
    try:
        import imageio_ffmpeg

        _ffmpeg_src = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        _ffmpeg_src = ""
if _ffmpeg_src and os.path.isfile(_ffmpeg_src):
    shutil.copy2(_ffmpeg_src, os.path.join(DIST, "ffmpeg.exe"))

_models_src = os.path.join(SPECPATH, "models")
if os.path.isdir(_models_src):
    _models_dst = os.path.join(DIST, "models")
    if os.path.isdir(_models_dst):
        shutil.rmtree(_models_dst)
    shutil.copytree(_models_src, _models_dst)
