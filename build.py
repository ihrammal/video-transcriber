"""build.py -- build the one and only Accessible Video Transcriber executable.

    python build.py              build everything and verify it
    python build.py --fast       skip the frozen self tests
    python build.py --no-setup   only rebuild the application
    python build.py --no-inno    skip the Inno Setup installer
    python build.py --qt-setup   also build the legacy Qt setup program

What it does, in order:

1. ``VidTrans.spec``  -> dist\\AccessibleVideoTranscriber\\   the application
   (folder build: AccessibleVideoTranscriber.exe, _internal\\, ffmpeg.exe,
   models\\ and the help folder)
2. ``installer.iss``  -> installer_output\\AccessibleVideoTranscriber_Setup_<version>.exe
   the wizard-style installer (licence, folder, shortcuts, post-install
   launch, removal of the old 1.1 copy) -- this is the one setup file that
   ships.
3. runs ``--selftest`` on the application, then silently installs the setup
   file into a throwaway folder and checks the shortcuts, the
   Add/Remove-Programs entry and the uninstaller.

``dist`` therefore holds the application folder and ``installer_output`` the
one setup file the user receives.  ``--qt-setup`` additionally builds the
older Qt based installer
(``VidTransSetup.spec`` -> ``dist/AccessibleVideoTranscriberSetup-<version>-Qt.exe``) for
comparison; it is never produced by default.
"""

from __future__ import annotations

import lzma
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(ROOT, "dist")
# PyInstaller's COLLECT name appends this folder to the distpath; the spec
# and installer.iss both pack dist\AccessibleVideoTranscriber.
APP_DIR = os.path.join(DIST_DIR, "AccessibleVideoTranscriber")
OUTPUT_DIR = os.path.join(ROOT, "installer_output")
UNINSTALL_DIR = os.path.join(ROOT, "build", "uninstaller")
PAYLOAD_DIR = os.path.join(ROOT, "build", "payload")
TEMP = os.path.join(ROOT, "build", "verify")

PYINSTALLER = [sys.executable, "-m", "PyInstaller"]


def say(text: str) -> None:
    print("\n=== %s" % text, flush=True)


def app_version() -> str:
    try:
        sys.path.insert(0, ROOT)
        import vt_bootstrap

        return vt_bootstrap.APP_VERSION
    except Exception:
        return "0.0.0"


def run(args, cwd=ROOT) -> int:
    print("> " + " ".join(os.path.basename(str(a)) if i == 0 else str(a) for i, a in enumerate(args)), flush=True)
    return subprocess.call([str(a) for a in args], cwd=cwd)


def compress(source: str, target: str) -> int:
    filters = [{"id": lzma.FILTER_LZMA2, "preset": 9 | lzma.PRESET_EXTREME}]
    with open(source, "rb") as src, lzma.open(target, "wb", format=lzma.FORMAT_XZ, filters=filters) as dst:
        while True:
            chunk = src.read(4 * 1024 * 1024)
            if not chunk:
                break
            dst.write(chunk)
    return os.path.getsize(target)


def freeze(spec: str, workdir: str, outdir: str) -> str:
    os.makedirs(outdir, exist_ok=True)
    # Onefile builds only replace their own .exe and leave a stale one from
    # an older build (e.g. the executable before a rename) in the folder,
    # and the installer copies the whole folder.  Remove old executables.
    for name in os.listdir(outdir):
        if name.lower().endswith(".exe"):
            os.remove(os.path.join(outdir, name))
    code = run(
        PYINSTALLER
        + [
            "--noconfirm",
            "--clean",
            "--distpath",
            outdir,
            "--workpath",
            workdir,
            ROOT + os.sep + spec,
        ]
    )
    if code != 0:
        raise SystemExit("PyInstaller failed for %s (exit %d)" % (spec, code))
    return outdir


def first_exe(folder: str) -> str:
    for name in sorted(os.listdir(folder)):
        if name.lower().endswith(".exe"):
            return os.path.join(folder, name)
    raise SystemExit("no executable was produced in " + folder)


def selftest(exe: str, report: str) -> bool:
    if not os.path.isfile(exe):
        print("self test skipped: %s is missing" % exe)
        return False
    if os.path.exists(report):
        os.remove(report)
    proc = subprocess.run([exe, "--selftest", report], capture_output=True, text=True, timeout=1800)
    text = ""
    if os.path.exists(report):
        with open(report, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    print(text.strip() or (proc.stdout or "").strip() or (proc.stderr or "").strip())
    return "RESULT: OK" in text


def find_iscc() -> str:
    """Locate Inno Setup's command line compiler."""
    name = "ISCC.exe"
    candidates = []
    environ = os.environ.get("ISCC", "")
    if environ:
        candidates.append(environ)
    local = os.environ.get("LOCALAPPDATA", "")
    if local:
        for ver in ("7", "6", "5"):
            candidates.append(os.path.join(local, "Programs", "Inno Setup " + ver, name))
    for base in (os.environ.get("ProgramFiles(x86)", ""), os.environ.get("ProgramFiles", "")):
        if base:
            for ver in ("7", "6", "5"):
                candidates.append(os.path.join(base, "Inno Setup " + ver, name))
    for path in (os.environ.get("PATH") or "").split(os.pathsep):
        if path:
            candidates.append(os.path.join(path, name))
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate
    raise SystemExit("Inno Setup's ISCC.exe was not found; install Inno Setup 6 or 7")


def compile_inno(version: str) -> str | None:
    """Compile installer.iss and return the installer path."""
    script = os.path.join(ROOT, "installer.iss")
    if not os.path.isfile(script):
        print("installer.iss is missing; skipped", flush=True)
        return None
    say("2/3 Inno Setup -> installer_output\\AccessibleVideoTranscriber_Setup_%s.exe" % version)
    iscc = find_iscc()
    print("> %s" % iscc, flush=True)
    code = subprocess.call([iscc, "/Qp", script], cwd=ROOT)
    if code != 0:
        raise SystemExit("Inno Setup failed (exit %d)" % code)
    target = os.path.join(OUTPUT_DIR, "AccessibleVideoTranscriber_Setup_%s.exe" % version)
    if not os.path.isfile(target):
        raise SystemExit("Inno Setup did not produce " + target)
    print("installer: %.1f MB" % (os.path.getsize(target) / 1048576.0), flush=True)
    return target


def verify_inno(setup_exe: str) -> bool:
    """Silent-install the Inno build, check it, then uninstall again."""
    import winreg

    app_name = "Accessible Video Transcriber"
    app_id = "{8F3A6C21-5B7D-4E94-A1C2-3D9E7F0B4A56}"
    uninstall_key = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\%s_is1" % app_id
    target = os.path.join(TEMP, "Accessible Video Transcriber-Inno")
    log_file = os.path.join(TEMP, "inno.log")
    # Inno exits immediately when it cannot open the log file, so the
    # verification folder has to exist before the silent install starts.
    os.makedirs(TEMP, exist_ok=True)

    # An existing installation under the same AppId would silently lose its
    # registry entry to the throwaway copy.  Remove it first.
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, uninstall_key) as key:
            previous, _kind = winreg.QueryValueEx(key, "InstallLocation")
    except OSError:
        previous = ""
    if previous:
        old_unins = os.path.join(str(previous).rstrip("\\"), "unins000.exe")
        if os.path.isfile(old_unins):
            subprocess.run([old_unins, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
                           capture_output=True, timeout=600)
            time.sleep(2.0)

    def links():
        import vt_install

        # The Desktop may live in OneDrive; ask the shell folder, do not guess.
        desktop = vt_install.desktop_link()
        start_dir = os.path.join(
            os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs", app_name
        )
        found = [desktop] if os.path.exists(desktop) else []
        if os.path.isdir(start_dir):
            found += [os.path.join(start_dir, n) for n in os.listdir(start_dir)]
        return found

    def registry():
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, uninstall_key) as key:
                out = {}
                for name in ("DisplayVersion", "InstallLocation", "UninstallString"):
                    try:
                        out[name] = winreg.QueryValueEx(key, name)[0]
                    except OSError:
                        out[name] = ""
                return out
        except OSError:
            return {}

    say("installing the Inno build silently")
    subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", target], capture_output=True)
    proc = subprocess.run(
        [setup_exe, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CURRENTUSER",
         "/DIR=" + target, "/TASKS=startmenuicon,desktopicon", "/LOG=" + log_file],
        capture_output=True, text=True, timeout=1800,
    )
    print("install exit:", proc.returncode)
    if proc.returncode != 0:
        print("setup output:", (proc.stdout or "").strip()[-800:])
        print("setup error:", (proc.stderr or "").strip()[-800:])

    exe = os.path.join(target, "AccessibleVideoTranscriber.exe")
    reg = registry()
    before = len(links())
    checks = [
        ("installed application",
         os.path.exists(exe) and os.path.getsize(exe) > 5 * 1024 * 1024
         and os.path.isdir(os.path.join(target, "_internal"))),
        ("standalone ffmpeg",
         os.path.exists(os.path.join(target, "ffmpeg.exe"))
         and os.path.getsize(os.path.join(target, "ffmpeg.exe")) > 50 * 1024 * 1024),
        ("bundled speech model",
         os.path.exists(os.path.join(target, "models", "base", "model.bin"))
         and os.path.getsize(os.path.join(target, "models", "base", "model.bin")) > 100 * 1024 * 1024),
        ("uninstaller", os.path.exists(os.path.join(target, "unins000.exe"))),
        ("english licence", os.path.exists(os.path.join(target, "License.txt"))),
        ("arabic licence", os.path.exists(os.path.join(target, "License.ar.txt"))),
        ("english help files",
         all(os.path.exists(os.path.join(target, "_internal", "resources", "help", "en", name))
             for name in ("guide.html", "shortcuts.html"))),
        ("arabic help files",
         all(os.path.exists(os.path.join(target, "_internal", "resources", "help", "ar", name))
             for name in ("guide.html", "shortcuts.html"))),
        ("combined user guide",
         all(os.path.exists(os.path.join(target, "_internal", "help", name))
             for name in ("user_guide.html", "user_guide_ar.html"))),
        ("shortcuts", before >= 2),
        ("registry entry", bool(reg.get("InstallLocation"))),
        ("registry location",
         os.path.normcase(reg.get("InstallLocation", "").rstrip("\\"))
         == os.path.normcase(target).rstrip("\\")),
        ("installed self test", selftest(exe, os.path.join(TEMP, "inno-selftest.txt"))),
    ]

    say("uninstalling the Inno build")
    unins = os.path.join(target, "unins000.exe")
    if os.path.exists(unins):
        subprocess.run([unins, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
                       capture_output=True, timeout=600)
        time.sleep(2.0)
    checks += [
        ("uninstalled application", not os.path.exists(exe)),
        ("uninstalled shortcuts", len(links()) < before),
        ("uninstalled registry", not registry()),
    ]

    ok = True
    for label, passed in checks:
        print("%s  %s" % ("PASS " if passed else "FAIL ", label))
        ok = ok and bool(passed)
    return ok


def verify_installer(setup_exe: str) -> bool:
    """Install into a throwaway folder and check what the user's machine sees."""
    import vt_install

    target = os.path.join(TEMP, "Accessible Video Transcriber")
    shutil.rmtree(target, ignore_errors=True)
    os.makedirs(target, exist_ok=True)

    say("installing into the throwaway folder %s" % target)
    proc = subprocess.run(
        [setup_exe, "--install", target], capture_output=True, text=True, timeout=1800
    )
    print((proc.stdout or "").strip() or (proc.stderr or "").strip())
    if proc.returncode != 0:
        return False

    ok = True
    payload = vt_install.install_exe(target)
    checks = [
        ("application file", os.path.exists(payload) and os.path.getsize(payload) > 20 * 1024 * 1024),
        ("uninstaller", os.path.exists(os.path.join(target, vt_install.UNINSTALLER_NAME))),
        ("start menu shortcut", os.path.exists(vt_install.start_menu_link())),
        (
            "uninstall shortcut",
            os.path.exists(vt_install.start_menu_uninstall_link()),
        ),
        ("desktop shortcut", os.path.exists(vt_install.desktop_link())),
    ]
    version = ""
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, vt_install.UNINSTALL_KEY) as key:
            version, _kind = winreg.QueryValueEx(key, "DisplayVersion")
            location, _kind = winreg.QueryValueEx(key, "InstallLocation")
        checks.append(("registry location", os.path.normcase(location) == os.path.normcase(target)))
    except Exception as exc:  # noqa: BLE001 - reported below
        print("registry error: %r" % (exc,))
        version = ""
    checks.append(("registry version", bool(version)))

    say("installed application self test")
    checks.append(("installed self test", selftest(payload, os.path.join(TEMP, "installed.txt"))))

    for label, passed in checks:
        print("%s  %s" % ("PASS " if passed else "FAIL ", label))
        ok = ok and bool(passed)

    say("cleaning up the throwaway installation")
    subprocess.run(
        [os.path.join(target, vt_install.UNINSTALLER_NAME), "/S"], capture_output=True, timeout=300
    )
    time.sleep(1.0)
    gone = not os.path.exists(vt_install.start_menu_link()) and not os.path.exists(
        vt_install.desktop_link()
    )
    print("%s  uninstaller removed the shortcuts" % ("PASS " if gone else "FAIL "))
    ok = ok and gone
    return ok


def main(argv=None) -> int:
    argv = list(sys.argv if argv is None else argv)[1:]
    fast = "--fast" in argv
    no_setup = "--no-setup" in argv
    no_inno = "--no-inno" in argv
    qt_setup = "--qt-setup" in argv
    version = app_version()

    os.makedirs(DIST_DIR, exist_ok=True)
    if os.path.isdir(DIST_DIR):
        for name in os.listdir(DIST_DIR):
            if name.lower().endswith(".exe"):
                os.remove(os.path.join(DIST_DIR, name))
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for name in os.listdir(OUTPUT_DIR):
        if name.lower().endswith(".exe"):
            os.remove(os.path.join(OUTPUT_DIR, name))

    say("1/3 application -> dist\\AccessibleVideoTranscriber\\AccessibleVideoTranscriber.exe")
    freeze("VidTrans.spec", os.path.join(ROOT, "build", "work-app"), DIST_DIR)
    app_exe = first_exe(APP_DIR)
    print("application: %.1f MB" % (os.path.getsize(app_exe) / 1048576.0))
    ok = True
    if not fast:
        ok = selftest(app_exe, os.path.join(TEMP, "app.txt"))

    if no_setup:
        if not no_inno:
            try:
                compile_inno(version)
            except SystemExit as exc:
                print("Inno Setup skipped: %s" % exc, flush=True)
        return 0 if ok else 1

    inno_exe = None
    if not no_inno:
        try:
            inno_exe = compile_inno(version)
        except SystemExit as exc:
            if fast:
                print("Inno Setup skipped: %s" % exc, flush=True)
            else:
                raise

    if qt_setup:
        say("building the legacy Qt setup program")
        freeze(
            os.path.join("installer", "Uninstaller.spec"),
            os.path.join(ROOT, "build", "work-uninstaller"),
            UNINSTALL_DIR,
        )
        uninstaller_exe = first_exe(UNINSTALL_DIR)
        shutil.rmtree(PAYLOAD_DIR, ignore_errors=True)
        os.makedirs(PAYLOAD_DIR, exist_ok=True)
        for source, name in ((app_exe, "AccessibleVideoTranscriber.exe.lzma"), (uninstaller_exe, "unins000.exe.lzma")):
            size = compress(source, os.path.join(PAYLOAD_DIR, name))
            print("%s -> %.1f MB" % (name, size / 1048576.0))
        freeze(
            "VidTransSetup.spec",
            os.path.join(ROOT, "build", "work-setup"),
            os.path.join(ROOT, "build", "dist-setup"),
        )
        built = first_exe(os.path.join(ROOT, "build", "dist-setup"))
        shutil.move(built, os.path.join(DIST_DIR, "AccessibleVideoTranscriberSetup-%s-Qt.exe" % version))
        shutil.rmtree(os.path.join(ROOT, "build", "dist-setup"), ignore_errors=True)

    if fast:
        return 0 if ok else 1

    if inno_exe:
        say("verifying the Inno Setup installer")
        try:
            ok = verify_inno(inno_exe) and ok
        except SystemExit as exc:
            print("Inno verification skipped: %s" % exc, flush=True)

    print("\nBUILD: " + ("OK" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
