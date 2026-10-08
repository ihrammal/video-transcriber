# -*- mode: python ; coding: utf-8 -*-
# VidTransSetup.spec -- the single executable handed to the user.
#
# The compressed application (AccessibleVideoTranscriber.exe.lzma) and the compressed uninstaller
# (unins000.exe.lzma) are produced by build.py in build/payload and added here
# as data files; setup_main.py unpacks them during the installation.  The render
# stack (ffmpeg, Pillow, MoviePy, faster-whisper) is deliberately NOT bundled a
# second time: it travels inside the application payload.

import glob
import os
import sysconfig

_PURELIB = sysconfig.get_paths()["purelib"]
DIST_INFOS = [
    (path, os.path.basename(path))
    for path in sorted(glob.glob(os.path.join(_PURELIB, "*.dist-info")))
]

PAYLOAD = [
    (path, "payload")
    for path in sorted(glob.glob(os.path.join("build", "payload", "*")))
    if os.path.isfile(path)
]
if not PAYLOAD:
    raise SystemExit("no payload found in build\\payload - run build.py first")

a = Analysis(
    ['installer/setup_main.py'],
    pathex=[],
    binaries=[],
    datas=DIST_INFOS + PAYLOAD + [('resources', 'resources')],
    hiddenimports=[
        'vt_setup',
        'vt_bootstrap',
        'vt_i18n',
        'vt_install',
        'winsound',
        # The splash screen is drawn by the Tcl/Tk based bootloader, so Tcl and
        # Tk must travel with the executable.  Nothing else in the setup program
        # imports tkinter (PIL is excluded below), so ask for it explicitly.
        'tkinter',
        '_tkinter',
    ],
    hookspath=['installer/hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'moviepy',
        'numpy',
        'PIL',
        'faster_whisper',
        'av',
        'ctranslate2',
    ],
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
    text_default="Setting up Accessible Video Transcriber...",
    minify_script=True,
    always_on_top=True,
    center='primary',
)

exe = EXE(
    pyz,
    splash,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='VidTransSetup',
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
)
