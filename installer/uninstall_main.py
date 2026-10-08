"""uninstall_main.py -- the Accessible Video Transcriber uninstaller (unins000.exe).

Deliberately tiny and dependency free: ctypes and the Win32 API only, so the
file that has to disappear last is a few hundred kilobytes and does not need
Python, Qt or the application to be working.

    unins000.exe          ask, then remove everything
    unins000.exe /S       silent, used by the "QuietUninstallString" entry
    unins000.exe /?       usage

The shortcuts, the Windows Apps & features entry, the per user data folder and
finally the install folder itself are removed.  The uninstaller cannot delete
itself while running, so it is scheduled for deletion on the next reboot with
``MoveFileExW(..., MOVEFILE_DELAY_UNTIL_REBOOT)``.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wintypes
import os
import sys

APP_NAME = "Accessible Video Transcriber"
PUBLISHER = "Iman Rammal"
FOLDER_NAME = "Accessible Video Transcriber"
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\VidTrans"
DATA_FOLDER = "VidTrans"

MOVEFILE_DELAY_UNTIL_REBOOT = 0x00000004
CSIDL_PROGRAMS = 0x0002
CSIDL_DESKTOPDIRECTORY = 0x0010
IDYES = 6
MB_YESNO = 0x00000004
MB_ICONQUESTION = 0x00000020
MB_TOPMOST = 0x00040000

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)

kernel32.MoveFileExW.argtypes = (wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD)
kernel32.MoveFileExW.restype = wintypes.BOOL
advapi32.RegOpenKeyExW.argtypes = (
    wintypes.HKEY, wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
    ctypes.POINTER(wintypes.HKEY),
)
advapi32.RegQueryValueExW.argtypes = (
    wintypes.HKEY, wintypes.LPCWSTR, ctypes.c_void_p, ctypes.c_void_p,
    wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD),
)
advapi32.RegDeleteKeyExW.argtypes = (wintypes.HKEY, wintypes.LPCWSTR)

HKEY_CURRENT_USER = 0x80000001
KEY_READ = 0x20019


def log(text: str) -> None:
    try:
        import vt_bootstrap

        vt_bootstrap.log("uninstall: " + text)
    except Exception:
        pass


# ---------------------------------------------------------------------- shell
def shell_folder(csidl: int) -> str:
    buf = ctypes.create_unicode_buffer(1024)
    try:
        if ctypes.c_int32(shell32.SHGetFolderPathW(None, csidl, None, 0, buf)).value != 0:
            return ""
    except Exception:
        return ""
    return buf.value


def programs_dir() -> str:
    return shell_folder(CSIDL_PROGRAMS) or os.path.join(
        os.environ.get("APPDATA", os.path.expanduser("~")),
        "Microsoft", "Windows", "Start Menu", "Programs",
    )


def desktop_dir() -> str:
    return shell_folder(CSIDL_DESKTOPDIRECTORY) or os.path.join(
        os.path.expanduser("~"), "Desktop"
    )


def local_app_data() -> str:
    return os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")


# ------------------------------------------------------------------- registry
def delete_uninstall_key() -> bool:
    try:
        return advapi32.RegDeleteKeyExW(HKEY_CURRENT_USER, UNINSTALL_KEY) == 0
    except Exception:
        return False


def registered_install_dir() -> str:
    """The install folder recorded in the registry, so uninstall is exact."""
    handle = wintypes.HKEY()
    if advapi32.RegOpenKeyExW(
        HKEY_CURRENT_USER, UNINSTALL_KEY, 0, KEY_READ, ctypes.byref(handle)
    ) != 0:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(len(buf))
        if advapi32.RegQueryValueExW(
            handle, "InstallLocation", None, None, buf, ctypes.byref(size)
        ) == 0:
            path = buf.value.strip()
            if os.path.isdir(path):
                return path
    finally:
        advapi32.RegCloseKey(handle)
    return ""


# ---------------------------------------------------------------------- files
def _long(path: str) -> str:
    if os.name != "nt" or path.startswith("\\\\?\\"):
        return path
    absolute = os.path.abspath(path)
    return absolute if len(absolute) < 240 else "\\\\?\\" + absolute


def _delete_entry(path: str, errors: list) -> None:
    target = _long(path)
    try:
        os.chmod(target, 0o777)
    except OSError:
        pass
    try:
        if os.path.isdir(target) and not os.path.islink(target):
            for name in os.listdir(target):
                _delete_entry(os.path.join(target, name), errors)
            os.rmdir(target)
        else:
            os.remove(target)
    except OSError as exc:
        errors.append("%s: %s" % (path, exc))


def remove_tree(path: str) -> bool:
    if not path or not os.path.exists(path):
        return True
    errors: list = []
    _delete_entry(path, errors)
    if errors:
        log("could not remove " + "; ".join(errors[:4]))
    return not os.path.exists(path)


def remove_links() -> int:
    removed = 0
    targets = (
        os.path.join(programs_dir(), FOLDER_NAME),
        os.path.join(desktop_dir(), APP_NAME + ".lnk"),
    )
    for path in targets:
        if os.path.isdir(path):
            if remove_tree(path):
                removed += 1
        elif os.path.exists(path):
            try:
                os.remove(_long(path))
                removed += 1
            except OSError:
                pass
    return removed


def self_delete() -> None:
    try:
        kernel32.MoveFileExW(os.path.abspath(sys.executable), None, MOVEFILE_DELAY_UNTIL_REBOOT)
    except Exception:
        pass


def ask() -> bool:
    message = (
        "Remove %s %s?\n\nThe program, its shortcuts and its settings will be deleted."
    ) % (APP_NAME, PUBLISHER)
    answer = user32.MessageBoxW(
        None, message, "Uninstall " + APP_NAME, MB_YESNO | MB_ICONQUESTION | MB_TOPMOST
    )
    return answer == IDYES


def do_uninstall(install_dir: str, remove_data: bool = True) -> int:
    log("removing installation from " + install_dir)
    delete_uninstall_key()
    remove_links()
    self_delete()
    remove_tree(install_dir)
    if remove_data:
        remove_tree(os.path.join(local_app_data(), DATA_FOLDER))
    log("uninstall finished")
    return 0


def usage() -> None:
    user32.MessageBoxW(
        None,
        __doc__.strip(),
        "Uninstall " + APP_NAME,
        0x00000040 | MB_TOPMOST,  # MB_ICONINFORMATION
    )


def main(argv=None) -> int:
    argv = list(sys.argv if argv is None else argv)
    if argv and argv[0] in ("/?", "-h", "--help"):
        usage()
        return 0
    silent = "/S" in argv or "--silent" in argv
    install_dir = registered_install_dir() or os.path.dirname(os.path.abspath(sys.executable))
    if not silent and not ask():
        return 0
    return do_uninstall(install_dir)


if __name__ == "__main__":
    sys.exit(main())
