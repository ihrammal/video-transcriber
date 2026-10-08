"""vt_install.py -- installation work shared by the app and the setup program.

Everything in here is plain standard library: no Qt, so the very same functions
run inside the installer executable, inside the running application and inside
command line checks.  The installer and the in-app wizard therefore behave
identically on the user's machine.

The functions are deliberately forgiving: they return a short human readable
result instead of raising, because every caller shows that text in a progress
line and a failed shortcut must never abort an otherwise successful install.
"""

from __future__ import annotations

import ctypes
import os
import re
import shutil
import subprocess
import sys
import winreg

APP_DISPLAY_NAME = "Accessible Video Transcriber"
PUBLISHER = "Iman Rammal"
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\VidTrans"
PAYLOAD_NAME = "AccessibleVideoTranscriber.exe"
UNINSTALLER_NAME = "unins000.exe"
START_MENU_FOLDER = "Accessible Video Transcriber"

CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
MOVEFILE_DELAY_UNTIL_REBOOT = 0x00000004

CSIDL_PROGRAMS = 0x0002
CSIDL_DESKTOPDIRECTORY = 0x0010


def app_version() -> str:
    try:
        import vt_bootstrap

        return getattr(vt_bootstrap, "APP_VERSION", "0.0.0")
    except Exception:
        return "0.0.0"


def app_data_dir() -> str:
    try:
        import vt_bootstrap

        return vt_bootstrap.app_data_dir()
    except Exception:
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        path = os.path.join(base, "Accessible Video Transcriber")
        os.makedirs(path, exist_ok=True)
        return path


def frozen_exe() -> str:
    """The executable the user started, or '' when running from Python."""
    if getattr(sys, "frozen", False):
        return os.path.abspath(sys.executable)
    return ""


def app_dir() -> str:
    """Folder holding the running program: next to the exe, else the project.

    Everything the install lays down *outside* the ``_internal`` folder --
    ``ffmpeg.exe`` and ``models\\`` -- is looked up here, so a relocated or
    portable folder keeps working.
    """
    exe = frozen_exe()
    if exe:
        return os.path.dirname(exe)
    return os.path.dirname(os.path.abspath(__file__))


#: Files a CTranslate2 Whisper model directory must contain to be usable.
MODEL_REQUIRED_FILES = ("config.json", "model.bin", "tokenizer.json")


def model_dir(model_name: str = "base") -> str:
    """A model folder shipped with the program, or '' if it is not there.

    The recognition model is bundled next to the executable instead of inside
    it: unpacking ~140 MB on every launch would be a second of dead time for no
    benefit, and the installer has to copy the folder anyway.
    """
    candidates = [
        os.path.join(app_dir(), "models", model_name),
        os.path.join(app_dir(), "_internal", "models", model_name),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", model_name),
    ]
    for folder in candidates:
        if all(os.path.isfile(os.path.join(folder, name)) for name in MODEL_REQUIRED_FILES):
            return folder
    return ""


def model_is_local(model_name: str = "base") -> bool:
    """True when the model travels with the program and needs no download."""
    return bool(model_dir(model_name))



# ---------------------------------------------------------------- known paths
def default_install_dir() -> str:
    """Per-user Programs folder: writable without an administrator account."""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, "Programs", "Accessible Video Transcriber")


def portable_dir() -> str:
    """Folder used by the portable installation type."""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, "Accessible Video Transcriber-Portable")


def _shell_folder(csidl: int) -> str:
    """Resolve a shell folder, honouring OneDrive redirection of the Desktop."""
    buf = ctypes.create_unicode_buffer(1024)
    try:
        ctypes.windll.shell32.SHGetFolderPathW(None, csidl, None, 0, buf)
    except Exception:
        return ""
    return buf.value or ""


def programs_dir() -> str:
    """Per-user Start menu \\ Programs folder."""
    folder = _shell_folder(CSIDL_PROGRAMS)
    if not folder:
        folder = os.path.join(
            os.environ.get("APPDATA", os.path.expanduser("~")), "Microsoft", "Windows", "Start Menu", "Programs"
        )
    return folder


def desktop_dir() -> str:
    """Per-user Desktop, following the folder if OneDrive moved it."""
    folder = _shell_folder(CSIDL_DESKTOPDIRECTORY)
    if not folder:
        folder = os.path.join(os.path.expanduser("~"), "Desktop")
    return folder


def start_menu_link(uninstall_exe: str = "") -> str:
    folder = os.path.join(programs_dir(), START_MENU_FOLDER)
    return os.path.join(folder, APP_DISPLAY_NAME + ".lnk")


def start_menu_uninstall_link() -> str:
    folder = os.path.join(programs_dir(), START_MENU_FOLDER)
    return os.path.join(folder, "Uninstall " + APP_DISPLAY_NAME + ".lnk")


def desktop_link() -> str:
    return os.path.join(desktop_dir(), APP_DISPLAY_NAME + ".lnk")


# ------------------------------------------------------------------ shortcuts
def _powershell() -> str:
    for name in ("powershell.exe", "pwsh.exe"):
        path = shutil.which(name)
        if path:
            return path
    return "powershell.exe"


def _ps_quote(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def create_shortcuts(
    target_exe: str, uninstall_exe: str = "", start_menu: bool = True, desktop: bool = True
) -> list:
    """Write every .lnk in a single PowerShell call.

    ``WScript.Shell`` is present on every supported Windows version, so no extra
    dependency (pywin32) has to be shipped, and batching the links keeps the
    install down to a single process start instead of one per link.
    """
    wanted = []
    if start_menu:
        wanted.append((start_menu_link(), target_exe, ""))
        if uninstall_exe:
            wanted.append((start_menu_uninstall_link(), uninstall_exe, ""))
    if desktop:
        wanted.append((desktop_link(), target_exe, ""))
    if not wanted:
        return []
    folders = []
    if start_menu:
        folders.append(os.path.dirname(start_menu_link()))
    if desktop:
        folders.append(desktop_dir())

    lines = [
        "$ErrorActionPreference='Continue';",
        "$sh=New-Object -ComObject WScript.Shell;",
        "foreach($folder in @({}, {})){{if($folder){{New-Item -ItemType Directory -Force -Path $folder | Out-Null}}}};".format(
            _ps_quote(folders[0] if folders else ""), _ps_quote(folders[1] if len(folders) > 1 else "")
        ),
    ]
    for link_path, target, args in wanted:
        # each link is saved on its own so one failure cannot cancel the others
        lines.append(
            "try{{"
            "$s=$sh.CreateShortcut({link});"
            "$s.TargetPath={target};$s.WorkingDirectory={wd};"
            "$s.Description={desc};$s.IconLocation={icon};{arguments}$s.Save();"
            "}}catch{{Write-Output ('SHORTCUT FAILED: '+{link}+' '+$_.Exception.Message)}};".format(
                link=_ps_quote(link_path),
                target=_ps_quote(target),
                wd=_ps_quote(os.path.dirname(target)),
                desc=_ps_quote(APP_DISPLAY_NAME),
                icon=_ps_quote(target + ",0"),
                arguments=("$s.Arguments=%s;" % _ps_quote(args)) if args else "",
            )
        )
    script = " ".join(lines)

    try:
        proc = subprocess.run(
            [
                _powershell(),
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            creationflags=CREATE_NO_WINDOW,
        )
    except Exception as exc:
        return ["shortcut error: %s" % exc]

    created = [path for path, _target, _args in wanted if os.path.exists(path)]
    missing = [path for path, _target, _args in wanted if not os.path.exists(path)]
    if missing:
        detail = "".join(
            line for line in ((proc.stdout or "") + (proc.stderr or "")).splitlines()
            if "SHORTCUT FAILED" in line
        ).strip()
        created.append(
            "shortcut error: %s" % (detail[:160] if detail else "could not write " + missing[0])
        )
    return created


def remove_shortcuts() -> list:
    removed = []
    folder = os.path.join(programs_dir(), START_MENU_FOLDER)
    targets = [start_menu_link(), start_menu_uninstall_link(), desktop_link(), folder]
    for path in targets:
        try:
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
                removed.append(path)
            elif os.path.exists(path):
                os.remove(path)
                removed.append(path)
        except OSError:
            pass
    return removed


# --------------------------------------------------------------------- payload
def install_exe(install_dir: str) -> str:
    return os.path.join(install_dir, PAYLOAD_NAME)


def copy_payload(source_exe: str, install_dir: str, progress=None) -> str:
    """Copy the application executable into ``install_dir``."""
    os.makedirs(install_dir, exist_ok=True)
    target = install_exe(install_dir)
    if os.path.abspath(source_exe) == os.path.abspath(target):
        return target

    total = max(os.path.getsize(source_exe), 1)
    temp = target + ".new"
    with open(source_exe, "rb") as src, open(temp, "wb") as dst:
        copied = 0
        while True:
            chunk = src.read(4 * 1024 * 1024)
            if not chunk:
                break
            dst.write(chunk)
            copied += len(chunk)
            if progress is not None:
                progress(min(99, int(copied / total * 100)))
    os.replace(temp, target)
    if progress is not None:
        progress(100)
    return target


def unpack_payload(compressed: str, target: str, progress=None) -> str:
    """Decompress the LZMA payload shipped inside the setup executable."""
    import lzma

    if not os.path.exists(compressed):
        raise FileNotFoundError("the setup payload is missing: %s" % compressed)
    total = max(os.path.getsize(compressed), 1)
    temp = target + ".new"
    os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
    with lzma.open(compressed, "rb") as src, open(temp, "wb") as dst:
        written = 0
        while True:
            chunk = src.read(4 * 1024 * 1024)
            if not chunk:
                break
            dst.write(chunk)
            written += len(chunk)
            if progress is not None:
                progress(min(99, int(written / total * 100 * 0.9)))
    os.replace(temp, target)
    if progress is not None:
        progress(100)
    return target


def payload_is_ready(path: str) -> bool:
    """True for a usable payload: the application file or its archive."""
    if not path or not os.path.exists(path):
        return False
    if str(path).lower().endswith(".lzma"):
        return os.path.getsize(path) > 5 * 1024 * 1024
    return os.path.getsize(path) > 20 * 1024 * 1024


def install_size_mb(install_dir: str) -> int:
    total = 0
    for root, _dirs, files in os.walk(install_dir):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
    return int(total / (1024 * 1024))


# -------------------------------------------------------------------- registry
def _uninstall_key(write: bool):
    root = winreg.HKEY_CURRENT_USER
    access = winreg.KEY_SET_VALUE if write else winreg.KEY_READ
    return winreg.CreateKeyEx(root, UNINSTALL_KEY, 0, access) if write else winreg.OpenKey(root, UNINSTALL_KEY, 0, access)


def register_uninstall(install_dir: str, size_mb: int = 0, uninstaller: str = "") -> str:
    exe = install_exe(install_dir)
    if not uninstaller:
        uninstaller = os.path.join(install_dir, UNINSTALLER_NAME)
    try:
        with _uninstall_key(True) as key:
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, APP_DISPLAY_NAME)
            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, app_version())
            winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, PUBLISHER)
            winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, exe)
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, install_dir)
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, '"%s"' % uninstaller)
            winreg.SetValueEx(key, "QuietUninstallString", 0, winreg.REG_SZ, '"%s" /S' % uninstaller)
            winreg.SetValueEx(key, "InstallDate", 0, winreg.REG_SZ, "")
            winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD, max(int(size_mb), 1))
        return "registered"
    except OSError as exc:
        return "registry error: %s" % exc


def unregister_uninstall() -> str:
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
        return "unregistered"
    except FileNotFoundError:
        return "already removed"
    except OSError as exc:
        return "registry error: %s" % exc


def installed_version() -> str:
    try:
        with _uninstall_key(False) as key:
            value, _kind = winreg.QueryValueEx(key, "DisplayVersion")
            return str(value)
    except OSError:
        return ""


# ----------------------------------------------------------------- video tools
def ffmpeg_exe() -> str:
    """The ffmpeg this machine should use.

    A standalone ``ffmpeg.exe`` placed next to ``AccessibleVideoTranscriber.exe`` wins, then one
    in ``bin\\`` under it.  The copy shipped inside the package by
    imageio-ffmpeg is only the fallback: it lives in the temporary extraction
    folder, so it disappears with every other temporary file and cannot be
    replaced by a user.
    """
    override = os.environ.get("VT_FFMPEG", "").strip()
    if override and os.path.exists(override):
        return override
    here = app_dir()
    for candidate in (
        os.path.join(here, "ffmpeg.exe"),
        os.path.join(here, "bin", "ffmpeg.exe"),
        os.path.join(here, "ffmpeg", "bin", "ffmpeg.exe"),
    ):
        if os.path.isfile(candidate):
            return candidate
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return ""


def caption_font() -> str:
    """Font used to burn captions into the video.

    A Windows system font comes first: Segoe UI, Tahoma and Arial are present on
    every supported Windows version and are the only ones that shape Arabic text
    correctly.  The font bundled in ``resources/fonts`` is the fallback for a
    machine without them.
    """
    windows = os.environ.get("WINDIR", r"C:\Windows")
    for name in ("segoeui.ttf", "tahoma.ttf", "arial.ttf"):
        path = os.path.join(windows, "Fonts", name)
        if os.path.exists(path):
            return path
    try:
        import vt_bootstrap

        bundled = vt_bootstrap.resource_path("resources", "fonts", "captions.ttf")
    except Exception:
        bundled = ""
    if bundled and os.path.exists(bundled):
        return bundled
    return ""


def _candidate_tool_dirs() -> list:
    """Directories worth searching for a system ffprobe / ffmpeg."""
    dirs = []
    try:
        import imageio_ffmpeg

        bundle_dir = os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe() or "")
        if bundle_dir:
            dirs.append(bundle_dir)
    except Exception:
        pass
    for name in ("ffprobe", "ffmpeg"):
        found = shutil.which(name)
        if found:
            dirs.append(os.path.dirname(found))
    here = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else __file__)
    dirs.extend(
        [
            here,
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Links"),
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "ffmpeg", "bin"),
            os.environ.get("SystemRoot", r"C:\Windows") and os.path.join(
                os.environ.get("SystemRoot", r"C:\Windows"), "System32"
            ),
            r"C:\ffmpeg\bin",
        ]
    )
    seen, unique = set(), []
    for item in dirs:
        if item and item not in seen and os.path.isdir(item):
            seen.add(item)
            unique.append(item)
    return unique


def ffprobe_exe() -> str:
    """ffprobe when it is installed, else ''.

    ffprobe is optional: the pipeline probes containers with the bundled
    ffmpeg when no ffprobe is available, but a copy found on ``PATH``, next to
    the bundled ffmpeg, or in one of the usual install folders is preferred
    because it returns structured JSON.
    """
    override = os.environ.get("VT_FFPROBE", "").strip()
    if override and os.path.exists(override):
        return override
    found = shutil.which("ffprobe")
    if found:
        return found
    for folder in _candidate_tool_dirs():
        candidate = os.path.join(folder, "ffprobe.exe")
        if os.path.exists(candidate):
            return candidate
    exe = ffmpeg_exe()
    if exe:
        sibling = os.path.join(os.path.dirname(exe), "ffprobe.exe")
        if os.path.exists(sibling):
            return sibling
    return ""


def _tool_version(exe: str) -> str:
    """Short version label, e.g. ``7.1``; falls back to the file name."""
    try:
        proc = subprocess.run(
            [exe, "-version"],
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=CREATE_NO_WINDOW,
        )
        first = (proc.stdout or "").splitlines()[:1]
        if not first:
            return os.path.basename(exe)
        match = re.search(r"\bversion\s+([0-9]+(?:\.[0-9]+)+)", first[0])
        return match.group(1) if match else first[0].strip()[:48]
    except Exception:
        return os.path.basename(exe)


def check_video_tools(bundled: bool = False) -> dict:
    """Everything the app needs to turn speech into a subtitled video file.

    ``ok`` is False only when something the output pipeline cannot work without
    is missing -- ffmpeg, Pillow (caption rendering) or a caption font.  The
    recognition model is reported separately because it is downloaded on first
    use and is not an installation error.

    ``bundled=True`` is used by the setup program, which deliberately does not
    carry a second copy of the render stack: ffmpeg and Pillow travel inside the
    application payload, so the installer reports them as bundled instead of
    probing libraries it does not have.
    """
    report = {"ffmpeg": "", "ffprobe": "", "pillow": "", "font": "", "model": "", "ok": False}

    if bundled:
        report["ffmpeg"] = "bundled"
        report["ffprobe"] = "bundled"
        report["pillow"] = "bundled"
    else:
        exe = ffmpeg_exe()
        if exe and os.path.exists(exe):
            report["ffmpeg"] = "ready: " + _tool_version(exe)
        else:
            report["ffmpeg"] = "missing"

        probe = ffprobe_exe()
        report["ffprobe"] = "ready: " + _tool_version(probe) if probe else "optional"

        try:
            from PIL import ImageFont  # noqa: F401

            report["pillow"] = "ready"
        except Exception:
            report["pillow"] = "missing"

    font = caption_font()
    report["font"] = "ready: " + os.path.basename(font) if font else "missing"

    if model_is_local():
        report["model"] = "bundled"
    elif model_is_cached():
        report["model"] = "ready"
    else:
        report["model"] = "download on first use"
    report["ok"] = (
        report["ffmpeg"].startswith(("ready", "bundled"))
        and report["pillow"] in ("ready", "bundled")
        and bool(font)
    )
    return report


def model_is_cached(model_name: str = "base") -> bool:
    """True when the recognition model is already on this machine.

    The bundled copy is checked first: that is the normal case for an installed
    program, and it must never reach for the network.  The Hugging Face cache
    is the fallback for a developer running from source.
    """
    if model_is_local(model_name):
        return True
    try:
        from faster_whisper.utils import download_model

        download_model(model_name, local_files_only=True)
        return True
    except Exception:
        return False


def download_model(model_name: str = "base", progress=None) -> str:
    """Make sure the recognition model is available, offline when possible."""
    folder = model_dir(model_name)
    if folder:
        # Shipped with the program: nothing to fetch and no call to make.
        if progress is not None:
            progress(100)
        return os.path.basename(folder)
    try:
        from faster_whisper.utils import download_model

        path = download_model(model_name)
        if progress is not None:
            progress(100)
        return os.path.basename(str(path))
    except Exception as exc:
        return "download failed: %s" % str(exc)[:80]


# ------------------------------------------------------------------- uninstall
def defer_delete(path: str) -> bool:
    """Ask Windows to delete a file that is still running, at next boot."""
    if not path or not os.path.exists(path):
        return False
    try:
        ctypes.windll.kernel32.MoveFileExW(path, None, MOVEFILE_DELAY_UNTIL_REBOOT)
        return True
    except Exception:
        return False


def read_install_dir() -> str:
    try:
        with _uninstall_key(False) as key:
            value, _kind = winreg.QueryValueEx(key, "InstallLocation")
            return str(value)
    except OSError:
        return os.path.dirname(os.path.abspath(sys.executable))


def running_app_pids(install_dir: str) -> list:
    """PIDs of a running AccessibleVideoTranscriber.exe (the uninstaller is ctypes only)."""
    name = os.path.basename(install_exe(install_dir)).lower()
    pids = []
    try:
        kernel32 = ctypes.windll.kernel32
        TH32CS_SNAPPROCESS = 0x00000002

        class PROCESSENTRY32W(ctypes.Structure):
            _fields_ = [
                ("dwSize", ctypes.c_uint),
                ("cntUsage", ctypes.c_uint),
                ("th32ProcessID", ctypes.c_uint),
                ("th32DefaultHeapID", ctypes.c_void_p),
                ("th32ModuleID", ctypes.c_uint),
                ("cntThreads", ctypes.c_uint),
                ("th32ParentProcessID", ctypes.c_uint),
                ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", ctypes.c_uint),
                ("szExeFile", ctypes.c_wchar * 260),
            ]

        snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        ok = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while ok:
            if entry.szExeFile.lower() == name:
                pids.append(int(entry.th32ProcessID))
            ok = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
        kernel32.CloseHandle(snapshot)
    except Exception:
        pass
    return pids


def stop_app(install_dir: str) -> int:
    stopped = 0
    for pid in running_app_pids(install_dir):
        try:
            os.kill(pid, 15)
            stopped += 1
        except OSError:
            pass
    return stopped
