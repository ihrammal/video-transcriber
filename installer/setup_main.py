"""setup_main.py -- the Accessible Video Transcriber setup program (AccessibleVideoTranscriberSetup.exe).

This is the single executable the user receives.  It carries the compressed
``AccessibleVideoTranscriber.exe`` inside itself, shows the same welcome and installation screens
as the application (``vt_setup.SetupWizard``) and then installs the application,
its shortcuts and its Add/Remove-Programs entry.

Command line::

    AccessibleVideoTranscriberSetup.exe                 normal, interactive installation
    AccessibleVideoTranscriberSetup.exe --install DIR   silent installation, no wizard
    AccessibleVideoTranscriberSetup.exe --selftest [F]  write a report about the payload
    AccessibleVideoTranscriberSetup.exe /?              usage

Nothing but Windows itself is required on the target machine: no Python, no
administrator account and no internet connection.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _path in (ROOT, HERE):
    if _path not in sys.path:
        sys.path.insert(0, _path)

PAYLOAD_NAME = "AccessibleVideoTranscriber.exe"
UNINSTALLER_NAME = "unins000.exe"
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
DETACHED_PROCESS = 0x00000008


def _payload_root() -> str:
    """Where the archives live: the bundle, or build/payload in a source tree."""
    if getattr(sys, "frozen", False):
        return os.path.join(getattr(sys, "_MEIPASS", HERE), "payload")
    for candidate in (os.path.join(HERE, "payload"), os.path.join(ROOT, "build", "payload")):
        if os.path.isdir(candidate):
            return candidate
    return os.path.join(ROOT, "build", "payload")


def payload_archive() -> str:
    return os.path.join(_payload_root(), "AccessibleVideoTranscriber.exe.lzma")


def uninstaller_archive() -> str:
    return os.path.join(_payload_root(), "unins000.exe.lzma")


def install_payload(destination: str, progress=None) -> str:
    """Unpack AccessibleVideoTranscriber.exe into ``destination`` and return the final path."""
    import vt_install

    return vt_install.unpack_payload(payload_archive(), destination, progress=progress)


def extract_uninstaller(install_dir: str) -> str:
    import vt_install

    target = os.path.join(install_dir, vt_install.UNINSTALLER_NAME)
    if not os.path.exists(target):
        try:
            vt_install.unpack_payload(uninstaller_archive(), target)
        except Exception:
            return ""
    return target


def install_unattended(install_dir: str, shortcuts: bool = True, desktop: bool = True) -> int:
    """``--install``: the same steps as the wizard, without any window."""
    import vt_install
    import vt_setup

    os.makedirs(install_dir, exist_ok=True)
    payload = install_payload(vt_install.install_exe(install_dir))
    if not os.path.exists(payload):
        print("payload is missing: " + payload)
        return 2
    uninstaller = extract_uninstaller(install_dir)

    if shortcuts:
        vt_install.create_shortcuts(
            payload,
            uninstaller,
            start_menu=True,
            desktop=desktop,
        )
    vt_install.register_uninstall(
        install_dir,
        vt_install.install_size_mb(install_dir),
        uninstaller=uninstaller,
    )
    vt_setup.save_setup(
        "en",
        True,
        install_dir=install_dir,
        install_mode=vt_setup.MODE_STANDARD,
        installed_version=vt_install.app_version(),
    )
    print("installed to " + install_dir)
    if shortcuts:
        print("shortcuts: " + ("start menu and desktop" if desktop else "start menu only"))
    else:
        print("shortcuts: none")
    return 0


def selftest(result_path: str = "") -> int:
    """Report what the setup program carries; used by build.py."""
    import vt_install
    import vt_setup

    lines = []
    ok = True

    def check(label, fn):
        nonlocal ok
        try:
            detail = fn() or ""
            lines.append("PASS  %s%s" % (label, (" - " + str(detail)) if detail else ""))
        except Exception as exc:  # noqa: BLE001 - reported in the file
            ok = False
            lines.append("FAIL  %s: %r" % (label, exc))

    def _payload():
        size = os.path.getsize(payload_archive())
        lines.append("      payload archive: %.1f MB" % (size / 1048576.0))
        if size < 5 * 1024 * 1024:
            raise RuntimeError("payload archive is too small")

    def _unpack():
        import shutil

        sandbox = os.path.join(tempfile.gettempdir(), "VT_setup_selftest")
        shutil.rmtree(sandbox, ignore_errors=True)
        os.makedirs(sandbox, exist_ok=True)
        target = install_payload(os.path.join(sandbox, vt_install.PAYLOAD_NAME))
        size = os.path.getsize(target)
        if size < 20 * 1024 * 1024:
            raise RuntimeError("unpacked payload is too small: %d" % size)
        shutil.rmtree(sandbox, ignore_errors=True)
        return "unpacked %d MB" % (size // 1048576)

    def _wizard():
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication, QLabel

        app = QApplication.instance() or QApplication([])
        wizard = vt_setup.SetupWizard(mode="setup", payload=payload_archive())
        try:
            pages = wizard.stack.count()
            labels = wizard.tools_box.findChildren(QLabel) + wizard.steps_box.findChildren(QLabel)
            if pages != 2:
                raise RuntimeError("expected 2 wizard pages, found %d" % pages)
            return "%d pages, %d status labels" % (pages, len(labels))
        finally:
            wizard._stop_worker()
            wizard.banner.stop()
            wizard.close()
            del wizard
            del app

    def _helpers():
        report = vt_install.check_video_tools(bundled=True)
        if not report["ok"]:
            raise RuntimeError("tool chain incomplete: %r" % report)
        return "ffmpeg ok, caption font %s" % report["font"]

    check("payload archive", _payload)
    check("payload unpack", _unpack)
    check("setup wizard", _wizard)
    check("video tools", _helpers)

    text = "\n".join(lines) + "\nRESULT: " + ("OK" if ok else "FAIL") + "\n"
    if result_path:
        try:
            with open(result_path, "w", encoding="utf-8") as handle:
                handle.write(text)
        except Exception:
            pass
    print(text)
    return 0 if ok else 1


def launch_installed(target: str) -> bool:
    if not target or not os.path.exists(target):
        return False
    try:
        subprocess.Popen(
            [target],
            cwd=os.path.dirname(target),
            close_fds=True,
            creationflags=CREATE_NO_WINDOW | DETACHED_PROCESS,
        )
        return True
    except Exception:
        return False


def usage() -> int:
    print(__doc__)
    return 0


def main(argv=None) -> int:
    import vt_bootstrap

    vt_bootstrap.install()

    argv = list(sys.argv if argv is None else argv)
    args = argv[1:]
    if args and args[0] in ("/?", "-h", "--help"):
        return usage()
    if args and args[0] == "--selftest":
        return selftest(args[1] if len(args) > 1 else "")

    import vt_install
    import vt_setup

    if args and args[0] == "--install":
        target = args[1] if len(args) > 1 else vt_install.default_install_dir()
        return install_unattended(
            os.path.abspath(target),
            shortcuts="--no-shortcuts" not in args,
            desktop="--no-desktop" not in args,
        )

    from PyQt6.QtGui import QFont
    from PyQt6.QtWidgets import QApplication

    app = QApplication(argv)
    app.setApplicationName("Accessible Video Transcriber Setup")
    app.setApplicationDisplayName(vt_install.APP_DISPLAY_NAME)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 11))

    data = vt_setup.load_setup()
    accepted, _language = vt_setup.run_setup(
        app,
        mode="setup",
        payload=payload_archive(),
        uninstaller=uninstaller_archive(),
    )
    if not accepted:
        return 0

    if data.get("install_mode") != vt_setup.MODE_PORTABLE:
        launch_installed(data.get("install_dir") or vt_install.default_install_dir())
    return 0


if __name__ == "__main__":
    sys.exit(main())
