"""vt_setup.py -- welcome screen, install screen and goodbye screen.

Opening Accessible Video Transcriber shows the welcome screen once, on the first launch (and
again whenever the program is started with ``--welcome``):

1. **Welcome** -- a full width animated banner types the line
   ``Welcome to the Accessible Video Transcriber by Iman Rammal`` letter by
   letter while a short musical jingle plays.  The sentence is announced by
   the screen reader as soon as the window opens and focus lands on the
   **Continue** button, which starts the program.  No licence or agreement is
   ever shown by the application: the licence belongs to the installer, which
   asks for it once.
2. **Installation** -- the user chooses the type of installation (standard for
   the current user, portable run-in-place, or a custom folder) and which
   shortcuts to create (Start menu, desktop).  The page also reports whether
   the tools needed to produce a subtitled video (ffmpeg, the caption font and
   the speech recognition model) are present, and a progress bar follows the
   real installation steps.

The same dialog is used by ``AccessibleVideoTranscriberSetup.exe``: it only passes a different
payload and lets the caller decide what happens after *Finish*, so the
installer and the application always look and behave the same.

Closing the application shows the mirrored goodbye dialog: the exact line
``Thank you for using my program, Goodbye.``, the farewell music and
an OK button, so nothing closes before the message has been read.

The module only depends on PyQt6, the standard library, ``vt_bootstrap`` (for
the per user data folder) and ``vt_install`` (the installation work itself).
Both jingles are synthesised on first run so no binary audio asset has to ship
with the executable.
"""

from __future__ import annotations

import json
import logging
import math
import os
import struct
import sys
import time
import wave

from PyQt6.QtCore import (
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSequentialAnimationGroup,
    Qt,
    QThread,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPen,
    QRadialGradient,
)
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

WELCOME_TEXT = "Welcome to the Accessible Video Transcriber by Iman Rammal"
FAREWELL_TEXT = "Thank you for using my program, Goodbye."

APP_TITLE = "Accessible Video Transcriber"
GOLD = QColor("#FFC107")
GOLD_SOFT = QColor("#FFD54F")

MODE_STANDARD = "standard"
MODE_PORTABLE = "portable"
MODE_CUSTOM = "custom"

SETUP_TR = {
    "en": {
        "setup_title": "Accessible Video Transcriber - Setup",
        "iface_en": "English",
        "iface_ar": "Arabic",
        "setup_access": "Accessible Video Transcriber setup wizard",
        "setup_access_d": "Two step setup: welcome, then installation type and shortcuts.",
        "welcome_hint": "Welcome! Choose the language, then press Next to continue.",
        "welcome_access": "Welcome banner",
        "welcome_access_d": WELCOME_TEXT,
        "welcome_status_n": "Welcome message",
        "welcome_title": "Welcome to Accessible Video Transcriber",
        "welcome_auto": "The program opens automatically in 3 seconds. Press Continue to start now.",
        "btn_continue": "Continue",
        "btn_continue_n": "Continue button",
        "btn_continue_d": "Closes this welcome message and opens the program.",
        "exit_title": "Goodbye",
        "exit_hint": "The program closes automatically in 3 seconds. Press OK to close now.",
        "btn_ok": "OK",
        "btn_ok_n": "OK button",
        "page_welcome": "Welcome",
        "page_install": "Installation",
        "lbl_setup_language": "Language:",
        "acc_lang_n": "Setup language",
        "acc_lang_d": "Chooses the language of the setup screens and of the application.",
        "install_title": "Installation type",
        "install_hint": "Choose how Accessible Video Transcriber is installed, then press Install and start.",
        "mode_standard": "Standard (recommended)",
        "mode_standard_d": "Install for the current user in your personal Programs folder, add "
        "the Start menu and desktop shortcuts and register Accessible Video Transcriber in Windows Apps & features.",
        "mode_portable": "Portable",
        "mode_portable_d": "Keep Accessible Video Transcriber in one self contained folder: no Start menu, no "
        "desktop shortcut and no entry in Windows Apps & features.",
        "mode_custom": "Custom folder",
        "mode_custom_d": "Install into a folder of your choice.",
        "lbl_install_dir": "Installation folder:",
        "btn_browse": "Browse...",
        "acc_browse_n": "Browse for a folder button",
        "acc_browse_d": "Opens a folder picker to choose where Accessible Video Transcriber is installed.",
        "acc_folder_n": "Installation folder",
        "acc_folder_d": "The folder Accessible Video Transcriber is installed into.",
        "shortcuts_title": "Shortcuts and extra components",
        "chk_start_menu": "Create a Accessible Video Transcriber shortcut in the Start menu",
        "chk_desktop": "Create a Accessible Video Transcriber shortcut on the desktop",
        "chk_model": "Download the speech recognition model now (about 150 MB, needed to transcribe)",
        "acc_start_menu_n": "Start menu shortcut",
        "acc_start_menu_d": "Adds Accessible Video Transcriber to the Windows Start menu and lists it in Apps and features.",
        "acc_desktop_n": "Desktop shortcut",
        "acc_desktop_d": "Adds a Accessible Video Transcriber shortcut to the desktop.",
        "acc_model_n": "Download the speech recognition model",
        "acc_model_d": "Downloads the Whisper speech recognition model so transcription also works "
        "without an internet connection.",
        "chk_launch": "Start Accessible Video Transcriber when the installation finishes",
        "acc_launch_n": "Start Accessible Video Transcriber now",
        "acc_launch_d": "Opens Accessible Video Transcriber as soon as the installation has finished.",
        "tools_title": "Tools for transcription and video output",
        "tool_ffmpeg": "Video engine (ffmpeg)",
        "tool_ffprobe": "Stream inspector (ffprobe)",
        "tool_pillow": "Caption rendering (Pillow)",
        "tool_font": "Caption font",
        "tool_model": "Speech recognition model",
        "tool_ok": "ready",
        "tool_missing": "missing",
        "tool_optional": "optional",
        "tool_not_installed": "not installed",
        "tool_download": "not downloaded yet",
        "btn_recheck": "Check again",
        "acc_recheck_n": "Check the installed tools again",
        "acc_recheck_d": "Checks ffmpeg, the caption font, Pillow and the speech recognition model.",
        "acc_tools_n": "Installed video tools",
        "acc_tools_d": "Reports the components needed to transcribe speech and to write the "
        "subtitled video file.",
        "tools_missing": "Some tools are missing, transcription and video output will not work "
        "until they are installed.",
        "state_pending": "waiting",
        "state_running": "working...",
        "state_done": "done",
        "state_skipped": "skipped",
        "state_failed": "failed",
        "step_folder": "Creating the application folder",
        "step_payload": "Copying the application files",
        "step_shortcuts": "Creating the Start menu and desktop shortcuts",
        "step_register": "Adding Accessible Video Transcriber to Windows Apps & features",
        "step_tools": "Checking the video tools (ffmpeg, captions, speech model)",
        "step_final": "Finishing the installation",
        "install_done": "Setup finished. Press Start to open Accessible Video Transcriber.",
        "install_ready": "Everything is already installed and up to date.",
        "install_portable": "Portable mode: nothing was copied and no shortcut was created.",
        "install_failed": "Step failed: {msg}",
        "step_skipped_shortcuts": "no shortcuts requested",
        "step_skipped_model": "downloaded on first use",
        "step_already": "already up to date",
        "btn_back": "Back",
        "btn_next": "Next",
        "btn_install": "Install and start",
        "btn_start": "Start Accessible Video Transcriber",
        "btn_finish": "Start Accessible Video Transcriber",
        "btn_exit": "Exit",
        "acc_back_n": "Back",
        "acc_back_d": "Returns to the welcome screen.",
        "acc_next_n": "Next",
        "acc_next_d": "Moves to the installation screen.",
        "acc_install_n": "Install and start",
        "acc_install_d": "Installs Accessible Video Transcriber with the selected options and then starts it.",
        "acc_finish_n": "Start Accessible Video Transcriber",
        "acc_finish_d": "Closes the setup and opens Accessible Video Transcriber.",
        "acc_exit_n": "Exit",
        "acc_exit_d": "Closes the setup without installing.",
        "acc_progress_n": "Installation progress",
        "acc_progress_d": "Installation progress: {value} percent.",
        "acc_steps_n": "Installation steps",
        "acc_steps_d": "List of the setup steps and their current state.",
    },
    "ar": {
        "setup_title": "إعداد Accessible Video Transcriber",
        "iface_en": "English",
        "iface_ar": "العربية",
        "setup_access": "معالج إعداد Accessible Video Transcriber",
        "setup_access_d": "إعداد من خطوتين: الترحيب، ثم نوع التثبيت والاختصارات.",
        "welcome_hint": "أهلًا بك! اختر اللغة ثم اضغط «التالي» للمتابعة.",
        "welcome_access": "لوحة الترحيب",
        "welcome_access_d": WELCOME_TEXT,
        "welcome_status_n": "رسالة الترحيب",
        "welcome_title": "أهلًا بك في Accessible Video Transcriber",
        "welcome_auto": "يفتح البرنامج تلقائيًا خلال 3 ثوانٍ. اضغط «متابعة» للبدء الآن.",
        "btn_continue": "متابعة",
        "btn_continue_n": "زر متابعة",
        "btn_continue_d": "يغلق رسالة الترحيب هذه ويفتح البرنامج.",
        "exit_title": "إلى اللقاء",
        "exit_hint": "يُغلق البرنامج تلقائيًا خلال 3 ثوانٍ. اضغط «موافق» للإغلاق الآن.",
        "btn_ok": "موافق",
        "btn_ok_n": "زر موافق",
        "page_welcome": "الترحيب",
        "page_install": "التثبيت",
        "lbl_setup_language": "اللغة:",
        "acc_lang_n": "لغة الإعداد",
        "acc_lang_d": "تختار لغة شاشات الإعداد ولغة التطبيق.",
        "install_title": "نوع التثبيت",
        "install_hint": "اختر طريقة تثبيت Accessible Video Transcriber ثم اضغط «تثبيت وتشغيل».",
        "mode_standard": "قياسي (موصى به)",
        "mode_standard_d": "تثبيت للمستخدم الحالي في مجلد البرامج الشخصية، مع إنشاء اختصارات قائمة "
        "البدء وسطح المكتب وتسجيل Accessible Video Transcriber في تطبيقات Windows.",
        "mode_portable": "محمول",
        "mode_portable_d": "إبقاء Accessible Video Transcriber في مجلد واحد مكتفي: بلا اختصار في قائمة ابدأ وبلا "
        "اختصار على سطح المكتب وبلا تسجيل في تطبيقات Windows.",
        "mode_custom": "مجلد مخصص",
        "mode_custom_d": "التثبيت في مجلد تختاره أنت.",
        "lbl_install_dir": "مجلد التثبيت:",
        "btn_browse": "استعراض...",
        "acc_browse_n": "زر استعراض المجلد",
        "acc_browse_d": "يفتح نافذة اختيار المجلد الذي سيُثبَّت فيه Accessible Video Transcriber.",
        "acc_folder_n": "مجلد التثبيت",
        "acc_folder_d": "المجلد الذي سيُثبَّت فيه Accessible Video Transcriber.",
        "shortcuts_title": "الاختصارات والمكونات الإضافية",
        "chk_start_menu": "إنشاء اختصار Accessible Video Transcriber في قائمة ابدأ",
        "chk_desktop": "إنشاء اختصار Accessible Video Transcriber على سطح المكتب",
        "chk_model": "تنزيل نموذج التعرّف على الكلام الآن (نحو 150 ميغابايت، مطلوب للتفريغ)",
        "acc_start_menu_n": "اختصار قائمة ابدأ",
        "acc_start_menu_d": "يضيف Accessible Video Transcriber إلى قائمة ابدأ في Windows ويسجّله في التطبيقات.",
        "acc_desktop_n": "اختصار سطح المكتب",
        "acc_desktop_d": "يضيف اختصار Accessible Video Transcriber إلى سطح المكتب.",
        "acc_model_n": "تنزيل نموذج التعرّف على الكلام",
        "acc_model_d": "ينزّل نموذج Whisper ليعمل التفريغ حتى بدون اتصال بالإنترنت.",
        "chk_launch": "تشغيل Accessible Video Transcriber عند انتهاء التثبيت",
        "acc_launch_n": "تشغيل Accessible Video Transcriber الآن",
        "acc_launch_d": "يفتح Accessible Video Transcriber فور انتهاء التثبيت.",
        "tools_title": "أدوات التفريغ وإخراج الفيديو",
        "tool_ffmpeg": "محرك الفيديو (ffmpeg)",
        "tool_ffprobe": "فاحص المسارات (ffprobe)",
        "tool_pillow": "رسم التسميات (Pillow)",
        "tool_font": "خط التسميات",
        "tool_model": "نموذج التعرّف على الكلام",
        "tool_ok": "جاهز",
        "tool_missing": "مفقود",
        "tool_optional": "اختياري",
        "tool_not_installed": "غير مثبَّت",
        "tool_download": "لم يُنزَّل بعد",
        "btn_recheck": "فحص مرة أخرى",
        "acc_recheck_n": "زر إعادة فحص الأدوات",
        "acc_recheck_d": "يفحص ffmpeg وخط التسميات وPillow ونموذج التعرّف على الكلام.",
        "acc_tools_n": "أدوات الفيديو المثبَّتة",
        "acc_tools_d": "تعرض المكونات اللازمة لتفريغ الكلام وكتابة ملف الفيديو بالتسميات.",
        "tools_missing": "بعض الأدوات مفقودة، ولن يعمل التفريغ وإخراج الفيديو قبل تثبيتها.",
        "state_pending": "بانتظار التنفيذ",
        "state_running": "جارٍ التنفيذ...",
        "state_done": "تم",
        "state_skipped": "تم التخطي",
        "state_failed": "فشل",
        "step_folder": "إنشاء مجلد التطبيق",
        "step_payload": "نسخ ملفات التطبيق",
        "step_shortcuts": "إنشاء اختصارات قائمة البدء وسطح المكتب",
        "step_register": "إضافة Accessible Video Transcriber إلى تطبيقات Windows",
        "step_tools": "فحص أدوات الفيديو (ffmpeg والتسميات ونموذج الكلام)",
        "step_final": "إنهاء التثبيت",
        "install_done": "اكتمل الإعداد. اضغط «تشغيل Accessible Video Transcriber» لفتحه.",
        "install_ready": "كل شيء مثبَّت بالفعل وفي آخر تحديث.",
        "install_portable": "الوضع المحمول: لم يُنسخ أي ملف ولم يُنشأ أي اختصار.",
        "install_failed": "فشلت الخطوة: {msg}",
        "step_skipped_shortcuts": "لم يُطلب أي اختصار",
        "step_skipped_model": "يُنزَّل عند أول استخدام",
        "step_already": "مثبَّت مسبقًا",
        "btn_back": "السابق",
        "btn_next": "التالي",
        "btn_install": "تثبيت وتشغيل",
        "btn_start": "تشغيل Accessible Video Transcriber",
        "btn_finish": "تشغيل Accessible Video Transcriber",
        "btn_exit": "خروج",
        "acc_back_n": "زر السابق",
        "acc_back_d": "يعيدك إلى شاشة الترحيب.",
        "acc_next_n": "زر التالي",
        "acc_next_d": "ينقلك إلى شاشة التثبيت.",
        "acc_install_n": "زر التثبيت والتشغيل",
        "acc_install_d": "يثبّت Accessible Video Transcriber بالخيارات المحددة ثم يشغّله.",
        "acc_finish_n": "زر تشغيل Accessible Video Transcriber",
        "acc_finish_d": "يغلق الإعداد ويفتح Accessible Video Transcriber.",
        "acc_exit_n": "زر الخروج",
        "acc_exit_d": "يغلق الإعداد دون تثبيت.",
        "acc_progress_n": "شريط تقدم التثبيت",
        "acc_progress_d": "تقدم التثبيت: {value} بالمئة.",
        "acc_steps_n": "خطوات التثبيت",
        "acc_steps_d": "قائمة خطوات الإعداد وحالتها الحالية.",
    },
}


def close_boot_splash() -> None:
    """Hide the PyInstaller boot splash as soon as our own window is on screen.

    The bootloader keeps a small Tk window visible while the executable
    unpacks.  It only disappears when the application tells it to, so without
    this call the white ``tk`` window would stay behind the wizard for the
    whole session.
    """
    try:
        import pyi_splash

        pyi_splash.close()
    except Exception:  # noqa: BLE001 - not a frozen build, or already closed
        pass


def tr(lang, key, **kwargs):
    table = SETUP_TR.get(lang, SETUP_TR["en"])
    text = table.get(key, SETUP_TR["en"].get(key, key))
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text


# ------------------------------------------------------------------ settings
def _setup_file() -> str:
    import vt_bootstrap

    return os.path.join(vt_bootstrap.app_data_dir(), "setup.json")


def load_setup() -> dict:
    try:
        with open(_setup_file(), "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def saved_language() -> str:
    lang = load_setup().get("language")
    return lang if lang in ("en", "ar") else ""


def save_setup(language: str, **extra) -> dict:
    data = load_setup()
    # The acceptance flag belonged to the licence gate, which the application
    # no longer has: drop it so an upgraded install forgets it.
    data.pop("agreed", None)
    data.update(
        {
            "language": language if language in ("en", "ar") else "en",
            "version": _app_version(),
            "installed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
    )
    for key, value in extra.items():
        if value is not None:
            data[key] = value
    try:
        with open(_setup_file(), "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return data


def _app_version() -> str:
    try:
        import vt_bootstrap

        return getattr(vt_bootstrap, "APP_VERSION", "0.0.0")
    except Exception:
        return "0.0.0"


# ---------------------------------------------------------------------- music
_AUDIO_CACHE: dict = {}


def _melody(name: str, notes) -> str:
    """Synthesise (once) and return the path of a short jingle."""
    if name in _AUDIO_CACHE:
        return _AUDIO_CACHE[name]
    import vt_bootstrap

    folder = os.path.join(vt_bootstrap.app_data_dir(), "audio")
    try:
        os.makedirs(folder, exist_ok=True)
    except Exception:
        folder = tempfile_dir()
    path = os.path.join(folder, name + ".wav")
    if not (os.path.exists(path) and os.path.getsize(path) > 2000):
        try:
            _synth(path, notes)
        except Exception:
            return ""
    _AUDIO_CACHE[name] = path
    return path


def tempfile_dir() -> str:
    import tempfile

    return tempfile.gettempdir()


def _synth(path: str, notes) -> None:
    """Render ``(frequency, start_second, duration)`` notes into a wave file."""
    rate = 44100
    total = max(start + dur for _f, start, dur in notes) + 0.35
    buffer = [0.0] * int(rate * total)
    for freq, start, dur in notes:
        first = int(start * rate)
        count = int(dur * rate)
        for i in range(count):
            t = i / rate
            attack = min(1.0, t / 0.02)
            envelope = attack * math.exp(-2.6 * t)
            # fundamental plus a soft second harmonic and a quiet detuned voice
            sample = (
                math.sin(2 * math.pi * freq * t)
                + 0.32 * math.sin(4 * math.pi * freq * t)
                + 0.18 * math.sin(2 * math.pi * (freq * 1.003) * t)
            )
            idx = first + i
            if 0 <= idx < len(buffer):
                buffer[idx] += 0.30 * envelope * sample
    peak = max(0.30, max(abs(v) for v in buffer))
    scale = 0.72 / peak
    frames = bytearray()
    for value in buffer:
        clipped = max(-1.0, min(1.0, value * scale))
        frames += struct.pack("<h", int(clipped * 32767))
    with wave.open(path, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(bytes(frames))


WELCOME_NOTES = (
    (523.25, 0.00, 0.55),   # C5
    (659.25, 0.28, 0.55),   # E5
    (783.99, 0.56, 0.55),   # G5
    (1046.50, 0.84, 0.85),  # C6
    (783.99, 1.40, 0.50),   # G5
    (1046.50, 1.70, 1.00),  # C6
)

FAREWELL_NOTES = (
    (1046.50, 0.00, 0.55),  # C6
    (783.99, 0.30, 0.55),   # G5
    (659.25, 0.60, 0.55),   # E5
    (523.25, 0.90, 1.10),   # C5
)


def _play(path: str, loop: bool = False) -> None:
    if not path or sys.platform != "win32":
        return
    try:
        import winsound

        flags = winsound.SND_ASYNC | winsound.SND_FILENAME
        if loop:
            flags |= winsound.SND_LOOP
        winsound.PlaySound(path, flags)
    except Exception:
        pass


def stop_music() -> None:
    if sys.platform != "win32":
        return
    try:
        import winsound

        winsound.PlaySound(None, winsound.SND_PURGE)
    except Exception:
        pass


def play_welcome_music() -> None:
    _play(_melody("welcome", WELCOME_NOTES), loop=True)


def play_farewell_music() -> None:
    stop_music()
    _play(_melody("farewell", FAREWELL_NOTES), loop=False)


# ----------------------------------------------------------------- animations
def _flags(*values) -> int:
    out = 0
    for value in values:
        out |= int(value)
    return out


def _wrap(text: str, metrics: QFontMetrics, max_width: int) -> list:
    words = text.split()
    if not words:
        return [""]
    lines = []
    current = ""
    for word in words:
        trial = word if not current else current + " " + word
        if not current or metrics.horizontalAdvance(trial) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


class AnimatedBanner(QWidget):
    """Dark branded panel with drifting gold glows and a typewriter headline."""

    def __init__(self, text, mode="welcome", parent=None):
        super().__init__(parent)
        self._text = text
        self._mode = mode
        self._frames = 0
        self._orbs = (
            (1.7, 150, 0.30),
            (2.6, 110, 0.72),
            (1.1, 190, 0.55),
            (3.3, 80, 0.18),
        )
        # The banner is decoration: it animates on its own and must never sit
        # in the tab order, otherwise it steals the focus that has to land on
        # the welcome sentence so a screen reader announces it.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAccessibleName(text)
        self.setAccessibleDescription(text)
        self.setMinimumHeight(150)
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self):
        self._frames += 1
        self.update()

    def start(self):
        if not self._timer.isActive():
            self._timer.start()

    def stop(self):
        self._timer.stop()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        # An exception raised while a QPainter is active corrupts the paint
        # engine and takes the whole process down, so the drawing always runs
        # through this guard.
        try:
            self._draw(painter)
        except Exception:
            logging.getLogger("vidtrans.setup").exception("banner paint failed")
        finally:
            painter.end()

    def _draw(self, painter):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        width = self.width()
        height = self.height()

        gradient = QLinearGradient(0, 0, width, height)
        gradient.setColorAt(0.0, QColor("#0e0e12"))
        gradient.setColorAt(0.55, QColor("#17171d"))
        gradient.setColorAt(1.0, QColor("#24221d"))
        painter.fillRect(0, 0, width, height, gradient)

        for speed, radius, y_ratio in self._orbs:
            centre_x = (self._frames * speed) % (width + 2 * radius) - radius
            centre_y = height * y_ratio
            glow = QRadialGradient(QPointF(centre_x, centre_y), radius)
            inner = QColor(GOLD)
            inner.setAlpha(40)
            outer = QColor(GOLD)
            outer.setAlpha(0)
            glow.setColorAt(0.0, inner)
            glow.setColorAt(1.0, outer)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(glow))
            painter.drawEllipse(QPointF(centre_x, centre_y), radius, radius)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(GOLD, 3))
        painter.drawRoundedRect(
            QRectF(2.0, 2.0, width - 4.0, height - 4.0), 16.0, 16.0
        )

        reveal = min(len(self._text), int(self._frames * (1.4 if self._mode == "exit" else 1.9)))
        visible = self._text[:reveal]

        font = QFont("Segoe UI", 1)
        font.setPixelSize(26 if self._mode == "welcome" else 24)
        font.setBold(True)
        painter.setFont(font)
        metrics = painter.fontMetrics()

        pad_x = 30
        text_width = max(40, width - 2 * pad_x)
        lines = _wrap(visible, metrics, text_width)
        line_height = metrics.height() + 6
        reserved_bottom = 46 if self._mode == "exit" else 18
        block_height = line_height * len(lines)
        top = max(
            16.0,
            (height - reserved_bottom - block_height) / 2.0,
        )
        painter.setPen(QColor("#FFFFFF"))
        for index, line in enumerate(lines):
            painter.drawText(
                QRectF(pad_x, top + index * line_height, text_width, line_height),
                _flags(Qt.AlignmentFlag.AlignLeft, Qt.AlignmentFlag.AlignVCenter),
                line,
            )

        if self._mode == "welcome":
            painter.setPen(QPen(GOLD_SOFT, 3))
            bar_width = max(60.0, text_width * 0.42)
            x = pad_x
            y = height - 26
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#2b2b31"))
            painter.drawRoundedRect(QRectF(x, y, bar_width, 6), 3, 3)
            progress = (self._frames % 150) / 150.0
            painter.setBrush(GOLD)
            painter.drawRoundedRect(
                QRectF(x, y, max(10.0, bar_width * progress), 6), 3, 3
            )
        else:
            painter.setPen(Qt.PenStyle.NoPen)
            track_y = height - 44
            painter.setBrush(QColor("#26262C"))
            painter.drawRoundedRect(QRectF(70, track_y, 440, 14), 7, 7)
            travel = (self._frames * 6) % 380
            painter.setBrush(GOLD)
            painter.drawRoundedRect(
                QRectF(74 + travel, track_y + 2, 96, 10), 5, 5
            )


def _center(widget, width, height):
    screen = widget.screen() if hasattr(widget, "screen") else None
    if screen is None:
        try:
            from PyQt6.QtWidgets import QApplication

            app = QApplication.instance()
            screen = app.primaryScreen() if app is not None else None
        except Exception:
            screen = None
    if screen is None:
        widget.resize(width, height)
        return
    area = screen.availableGeometry()
    widget.resize(width, height)
    widget.move(
        area.x() + max(0, (area.width() - width) // 2),
        area.y() + max(0, (area.height() - height) // 2),
    )


# --------------------------------------------------------------------- install
# --------------------------------------------------------------------- wizard
WIZARD_CSS = """
QDialog {
    background-color: #141418;
    color: #f2f2f4;
    font-size: 11pt;
}
QLabel { background: transparent; }
QLabel#wizTitle {
    color: #FFC107;
    font-size: 20pt;
    font-weight: 800;
}
QLabel#wizSubtitle { color: #9a9aa4; font-size: 10pt; }
QLabel#stepRow { background: transparent; padding: 3px 2px; }
QLabel#stepRow[state="pending"] { color: #8b8b96; }
QLabel#stepRow[state="running"] { color: #FFC107; font-weight: 700; }
QLabel#stepRow[state="done"] { color: #7BE495; }
QLabel#stepRow[state="skipped"] { color: #7f7f8c; }
QLabel#stepRow[state="failed"] { color: #ff8f8f; font-weight: 700; }
QLabel#toolRow { background: transparent; padding: 1px 2px; color: #cfcfd6; }
QLabel#toolRow[state="done"] { color: #7BE495; }
QLabel#toolRow[state="failed"] { color: #ff8f8f; font-weight: 700; }
QFrame#card {
    background-color: #1c1c22;
    border: 1px solid #33333c;
    border-radius: 12px;
}
QLabel#cardTitle {
    color: #FFC107;
    font-weight: 700;
    font-size: 12pt;
    background: transparent;
}
QComboBox, QCheckBox, QRadioButton { background: transparent; spacing: 10px; }
QCheckBox, QRadioButton { padding: 2px 0px; }
QComboBox {
    background-color: #26262e;
    color: #f2f2f4;
    border: 1px solid #4a4a55;
    border-radius: 8px;
    padding: 8px 10px;
    min-height: 22px;
    min-width: 160px;
}
QComboBox:focus, QCheckBox:focus, QRadioButton:focus, QLineEdit:focus, QTextBrowser:focus {
    border: 3px solid #FFC107;
}
QComboBox QAbstractItemView {
    background-color: #1c1c22;
    color: #f2f2f4;
    border: 1px solid #4a4a55;
    selection-background-color: #3b3b1f;
    selection-color: #FFC107;
}
QLineEdit {
    background-color: #26262e;
    color: #f2f2f4;
    border: 1px solid #4a4a55;
    border-radius: 8px;
    padding: 7px 10px;
    min-height: 20px;
}
QLineEdit:disabled { color: #6d6d78; background-color: #1c1c22; }
QTextBrowser {
    background-color: #121216;
    color: #d6d6dc;
    border: 1px solid #33333c;
    border-radius: 8px;
    padding: 8px;
    font-size: 9pt;
}
QProgressBar {
    background-color: #26262e;
    color: #f2f2f4;
    border: 1px solid #4a4a55;
    border-radius: 8px;
    text-align: center;
    min-height: 22px;
}
QProgressBar::chunk { background-color: #FFC107; border-radius: 7px; }
QPushButton {
    background-color: #26262e;
    color: #f2f2f4;
    border: 1px solid #4a4a55;
    border-radius: 8px;
    padding: 9px 22px;
    font-weight: 600;
    min-height: 22px;
    min-width: 96px;
}
QPushButton:hover { background-color: #33333c; border-color: #FFC107; }
QPushButton:focus { border: 3px solid #FFC107; }
QPushButton:disabled { color: #6d6d78; background-color: #1c1c22; border-color: #33333c; }
QPushButton#primaryButton {
    background-color: #FFC107;
    color: #141418;
    border: 1px solid #FFC107;
    font-weight: 800;
}
QPushButton#primaryButton:hover { background-color: #FFD54F; }
QPushButton#primaryButton:disabled {
    background-color: #26262e; color: #6d6d78; border-color: #33333c;
}
QRadioButton::indicator, QCheckBox::indicator { width: 18px; height: 18px; }
"""


class InstallStep:
    """One installation step: a translated label and the work behind it."""

    def __init__(self, key, action, message=""):
        self.key = key
        self.action = action
        self.message = message or key
        self.state = "pending"

    def run(self, worker, index, total):
        self.state = "running"
        worker.stepChanged.emit(index, self.state, "")
        note = self.action(worker) or ""
        self.state = "done"
        return note


class InstallThread(QThread):
    """Runs the installation steps off the GUI thread."""

    stepChanged = pyqtSignal(int, str, str)
    progress = pyqtSignal(int)
    finished_ok = pyqtSignal(str)

    def __init__(self, steps, plan, parent=None):
        super().__init__(parent)
        self.steps = steps
        self.plan = plan
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def is_cancelled(self):
        return self._cancelled

    def report(self, value):
        self.progress.emit(max(0, min(100, int(value))))

    def run(self):
        total = len(self.steps) or 1
        note = ""
        for index, step in enumerate(self.steps):
            if self._cancelled:
                step.state = "skipped"
                self.stepChanged.emit(index, step.state, "")
                continue
            try:
                note = step.run(self, index, total)
            except Exception as exc:  # noqa: BLE001 - reported in the UI
                step.state = "failed"
                self.stepChanged.emit(index, step.state, str(exc)[:160])
                logging.getLogger("vidtrans.setup").exception("install step %s failed", step.key)
                continue
            self.stepChanged.emit(index, step.state, note)
            self.report(int((index + 1) / total * 100))
        self.finished_ok.emit(note)


def app_is_installed() -> bool:
    """True when the application files are already in the install folder.

    Keeps a repeat launch from running the installation steps a second time:
    the welcome screen is still shown, but *Next* then opens the application.
    """
    try:
        import vt_install

        target = load_setup().get("install_dir") or vt_install.default_install_dir()
        return vt_install.payload_is_ready(vt_install.install_exe(target))
    except Exception:  # noqa: BLE001 - never block the wizard on this probe
        return False


class SetupWizard(QDialog):
    """Welcome -> installation type, shortcuts and tools."""

    def __init__(self, mode="app", payload="", uninstaller="", parent=None):
        super().__init__(parent)
        import vt_install

        self.installer_mode = mode == "setup"
        self.payload = payload or vt_install.frozen_exe()
        self.uninstaller = uninstaller or ""
        self.language = saved_language() or "en"
        self.install_finished = False
        self.installing = False
        self.worker = None
        self.install_dir = load_setup().get("install_dir") or vt_install.default_install_dir()
        self.tools = {}
        self._step_rows = []
        self._steps = []
        self._auto_folder = ""

        self.setModal(True)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setMinimumSize(800, 660)
        self.setStyleSheet(WIZARD_CSS)
        self._center(820, 690)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(12)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        self.title_label = QLabel("")
        self.title_label.setObjectName("wizTitle")
        self.subtitle_label = QLabel("")
        self.subtitle_label.setObjectName("wizSubtitle")
        self.subtitle_label.setWordWrap(True)
        titles.addWidget(self.title_label)
        titles.addWidget(self.subtitle_label)
        header.addLayout(titles, 1)

        lang_row = QHBoxLayout()
        lang_row.setSpacing(8)
        self.lang_label = QLabel("")
        self.lang_combo = QComboBox()
        self.lang_combo.addItem(SETUP_TR["en"]["iface_en"], "en")
        self.lang_combo.addItem(SETUP_TR["ar"]["iface_ar"], "ar")
        self.lang_combo.setAccessibleName(tr(self.language, "acc_lang_n"))
        self.lang_combo.setAccessibleDescription(tr(self.language, "acc_lang_d"))
        self.lang_combo.setToolTip(tr(self.language, "acc_lang_d"))
        self.lang_label.setBuddy(self.lang_combo)
        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        lang_row.addWidget(self.lang_label)
        lang_row.addWidget(self.lang_combo)
        header.addLayout(lang_row)
        root.addLayout(header)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)
        self._build_welcome_page()
        self._build_install_page()

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        self.back_button = QPushButton("")
        self.next_button = QPushButton("")
        self.next_button.setObjectName("primaryButton")
        self.exit_button = QPushButton("")
        self.back_button.clicked.connect(self._on_back)
        self.next_button.clicked.connect(self._on_next)
        self.exit_button.clicked.connect(self.reject)
        buttons.addWidget(self.exit_button)
        buttons.addStretch(1)
        buttons.addWidget(self.back_button)
        buttons.addWidget(self.next_button)
        root.addLayout(buttons)

        self.finished.connect(self._stop_extras)
        self.rejected.connect(self._stop_extras)

        self._on_mode_changed(0, True)

        self._apply_language(self.language)
        # A launch of an already installed copy must not run the installation
        # steps again; the welcome page opens straight on the application.
        self.app_installed = not self.installer_mode and app_is_installed()
        self.stack.setCurrentIndex(0)
        self._sync_buttons()
        play_welcome_music()

    # ------------------------------------------------------------------ pages
    def showEvent(self, event):
        super().showEvent(event)
        # Our own window replaces the boot splash drawn by the bootloader.
        close_boot_splash()
        # Announce the welcome sentence to the screen reader as soon as the
        # startup screen appears, then let the user Tab onward.
        try:
            self.welcome_status.setFocus(Qt.FocusReason.OtherFocusReason)
            self.welcome_status.setAccessibleDescription(WELCOME_TEXT)
        except Exception:  # noqa: BLE001 - announcement is best effort
            pass

    def _build_welcome_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.banner = AnimatedBanner(WELCOME_TEXT, mode="welcome")
        self.banner.setAccessibleName(tr(self.language, "welcome_access"))
        self.banner.setAccessibleDescription(WELCOME_TEXT)
        layout.addWidget(self.banner, 2)

        # Visible + screen-reader announcement of the exact welcome sentence.
        self.welcome_status = QLabel(WELCOME_TEXT)
        self.welcome_status.setObjectName("wizTitle")
        self.welcome_status.setWordWrap(True)
        self.welcome_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.welcome_status.setAccessibleName(tr(self.language, "welcome_status_n"))
        self.welcome_status.setAccessibleDescription(WELCOME_TEXT)
        self.welcome_status.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        layout.addWidget(self.welcome_status)

        self.welcome_hint = QLabel("")
        self.welcome_hint.setObjectName("wizSubtitle")
        self.welcome_hint.setWordWrap(True)
        self.welcome_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.welcome_hint)

        # No licence or agreement is presented here: the installer shows the
        # licence once, and the application never asks for acceptance.
        layout.addStretch(1)
        self.stack.addWidget(page)

    def _build_install_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        type_card = QFrame()
        type_card.setObjectName("card")
        type_form = QVBoxLayout(type_card)
        type_form.setContentsMargins(18, 14, 18, 14)
        type_form.setSpacing(6)
        self.install_title = QLabel("")
        self.install_title.setObjectName("cardTitle")
        self.install_hint = QLabel("")
        self.install_hint.setObjectName("wizSubtitle")
        self.install_hint.setWordWrap(True)
        type_form.addWidget(self.install_title)
        type_form.addWidget(self.install_hint)

        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.radio_standard = QRadioButton("")
        self.radio_portable = QRadioButton("")
        self.radio_custom = QRadioButton("")
        for index, button in enumerate(
            (self.radio_standard, self.radio_portable, self.radio_custom)
        ):
            button.setAccessibleName("")
            self.mode_group.addButton(button, index)
            type_form.addWidget(button)
        self.desc_standard = QLabel("")
        self.desc_standard.setObjectName("wizSubtitle")
        self.desc_standard.setWordWrap(True)
        self.desc_portable = QLabel("")
        self.desc_portable.setObjectName("wizSubtitle")
        self.desc_portable.setWordWrap(True)
        self.desc_custom = QLabel("")
        self.desc_custom.setObjectName("wizSubtitle")
        self.desc_custom.setWordWrap(True)
        type_form.addWidget(self.desc_standard)
        type_form.addWidget(self.desc_portable)
        type_form.addWidget(self.desc_custom)

        folder_row = QHBoxLayout()
        folder_row.setSpacing(8)
        self.folder_label = QLabel("")
        self.folder_edit = QLineEdit("")
        self.folder_edit.setAccessibleName(tr(self.language, "acc_folder_n"))
        self.folder_edit.setAccessibleDescription(tr(self.language, "acc_folder_d"))
        self.folder_edit.setToolTip(tr(self.language, "acc_folder_d"))
        self.folder_label.setBuddy(self.folder_edit)
        self.browse_button = QPushButton("")
        self.browse_button.setAccessibleName(tr(self.language, "acc_browse_n"))
        self.browse_button.setAccessibleDescription(tr(self.language, "acc_browse_d"))
        self.browse_button.clicked.connect(self._on_browse)
        folder_row.addWidget(self.folder_label)
        folder_row.addWidget(self.folder_edit, 1)
        folder_row.addWidget(self.browse_button)
        type_form.addLayout(folder_row)

        self.radio_standard.setChecked(True)
        self.mode_group.idToggled.connect(self._on_mode_changed)
        layout.addWidget(type_card)

        links_card = QFrame()
        links_card.setObjectName("card")
        links_form = QVBoxLayout(links_card)
        links_form.setContentsMargins(18, 14, 18, 14)
        links_form.setSpacing(6)
        self.links_title = QLabel("")
        self.links_title.setObjectName("cardTitle")
        links_form.addWidget(self.links_title)
        self.start_menu_check = QCheckBox("")
        self.start_menu_check.setChecked(True)
        self.desktop_check = QCheckBox("")
        self.desktop_check.setChecked(True)
        self.model_check = QCheckBox("")
        self.model_check.setVisible(not self.installer_mode)
        self.launch_check = QCheckBox("")
        self.launch_check.setChecked(True)
        self.launch_check.setVisible(self.installer_mode)
        for check, name_key, desc_key in (
            (self.start_menu_check, "acc_start_menu_n", "acc_start_menu_d"),
            (self.desktop_check, "acc_desktop_n", "acc_desktop_d"),
            (self.model_check, "acc_model_n", "acc_model_d"),
            (self.launch_check, "acc_launch_n", "acc_launch_d"),
        ):
            check.setAccessibleName(tr(self.language, name_key))
            check.setAccessibleDescription(tr(self.language, desc_key))
            check.setToolTip(tr(self.language, desc_key))
            links_form.addWidget(check)
        self.model_check.toggled.connect(self._sync_buttons)
        layout.addWidget(links_card)

        tools_card = QFrame()
        tools_card.setObjectName("card")
        tools_form = QVBoxLayout(tools_card)
        tools_form.setContentsMargins(18, 14, 18, 14)
        tools_form.setSpacing(4)
        tools_head = QHBoxLayout()
        self.tools_title = QLabel("")
        self.tools_title.setObjectName("cardTitle")
        self.recheck_button = QPushButton("")
        self.recheck_button.setAccessibleName(tr(self.language, "acc_recheck_n"))
        self.recheck_button.setAccessibleDescription(tr(self.language, "acc_recheck_d"))
        self.recheck_button.clicked.connect(self._check_tools)
        tools_head.addWidget(self.tools_title)
        tools_head.addStretch(1)
        tools_head.addWidget(self.recheck_button)
        tools_form.addLayout(tools_head)
        self.tools_box = QWidget()
        self.tools_layout = QVBoxLayout(self.tools_box)
        self.tools_layout.setContentsMargins(0, 0, 0, 0)
        self.tools_layout.setSpacing(2)
        self.tools_box.setAccessibleName(tr(self.language, "acc_tools_n"))
        self.tools_box.setAccessibleDescription(tr(self.language, "acc_tools_d"))
        tools_form.addWidget(self.tools_box)
        layout.addWidget(tools_card)

        steps_card = QFrame()
        steps_card.setObjectName("card")
        steps_form = QVBoxLayout(steps_card)
        steps_form.setContentsMargins(18, 14, 18, 14)
        steps_form.setSpacing(6)
        self.steps_box = QWidget()
        self.steps_layout = QVBoxLayout(self.steps_box)
        self.steps_layout.setContentsMargins(0, 0, 0, 0)
        self.steps_layout.setSpacing(3)
        self.steps_box.setAccessibleName(tr(self.language, "acc_steps_n"))
        self.steps_box.setAccessibleDescription(tr(self.language, "acc_steps_d"))
        steps_form.addWidget(self.steps_box)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setAccessibleName(tr(self.language, "acc_progress_n"))
        steps_form.addWidget(self.progress)
        self.install_status = QLabel("")
        self.install_status.setObjectName("wizSubtitle")
        self.install_status.setWordWrap(True)
        steps_form.addWidget(self.install_status)
        layout.addWidget(steps_card)
        layout.addStretch(1)

        # The four cards need far more vertical space than the dialog has;
        # without a scroll area Qt crushes every label below its font height
        # and the texts overlap.  The scroll area keeps the natural heights.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll.setWidget(page)
        self.stack.addWidget(scroll)

    # --------------------------------------------------------------- language
    def _on_lang_changed(self, index):
        data = self.lang_combo.itemData(index)
        self._apply_language(data if data in ("en", "ar") else "en")

    def _apply_language(self, lang):
        self.language = lang
        rtl = lang == "ar"
        self.setLayoutDirection(
            Qt.LayoutDirection.RightToLeft if rtl else Qt.LayoutDirection.LeftToRight
        )

        self.setWindowTitle(tr(lang, "setup_title"))
        self.setAccessibleName(tr(lang, "setup_access"))
        self.setAccessibleDescription(tr(lang, "setup_access_d"))
        self.title_label.setText(APP_TITLE)
        self.subtitle_label.setText(tr(lang, "setup_access_d"))
        self.welcome_hint.setText(tr(lang, "welcome_hint"))
        self.lang_label.setText(tr(lang, "lbl_setup_language"))
        selected = self.lang_combo.currentData()
        self.lang_combo.blockSignals(True)
        self.lang_combo.setItemText(0, tr(lang, "iface_en"))
        self.lang_combo.setItemText(1, tr(lang, "iface_ar"))
        self.lang_combo.setCurrentIndex(1 if selected == "ar" else 0)
        self.lang_combo.blockSignals(False)
        self.lang_combo.setAccessibleName(tr(lang, "acc_lang_n"))
        self.lang_combo.setAccessibleDescription(tr(lang, "acc_lang_d"))
        self.banner.setAccessibleName(tr(lang, "welcome_access"))
        self.banner.setAccessibleDescription(tr(lang, "welcome_access_d"))

        self.install_title.setText(tr(lang, "install_title"))
        self.install_hint.setText(tr(lang, "install_hint"))
        self.radio_standard.setText(tr(lang, "mode_standard"))
        self.radio_standard.setAccessibleName(tr(lang, "mode_standard"))
        self.radio_standard.setAccessibleDescription(tr(lang, "mode_standard_d"))
        self.radio_portable.setText(tr(lang, "mode_portable"))
        self.radio_portable.setAccessibleName(tr(lang, "mode_portable"))
        self.radio_portable.setAccessibleDescription(tr(lang, "mode_portable_d"))
        self.radio_custom.setText(tr(lang, "mode_custom"))
        self.radio_custom.setAccessibleName(tr(lang, "mode_custom"))
        self.radio_custom.setAccessibleDescription(tr(lang, "mode_custom_d"))
        self.desc_standard.setText(tr(lang, "mode_standard_d"))
        self.desc_portable.setText(tr(lang, "mode_portable_d"))
        self.desc_custom.setText(tr(lang, "mode_custom_d"))
        self.folder_label.setText(tr(lang, "lbl_install_dir"))
        self.folder_edit.setAccessibleName(tr(lang, "acc_folder_n"))
        self.folder_edit.setAccessibleDescription(tr(lang, "acc_folder_d"))
        self.browse_button.setText(tr(lang, "btn_browse"))
        self.browse_button.setAccessibleName(tr(lang, "acc_browse_n"))
        self.browse_button.setAccessibleDescription(tr(lang, "acc_browse_d"))
        self.links_title.setText(tr(lang, "shortcuts_title"))
        self.start_menu_check.setText(tr(lang, "chk_start_menu"))
        self.desktop_check.setText(tr(lang, "chk_desktop"))
        self.model_check.setText(tr(lang, "chk_model"))
        self.launch_check.setText(tr(lang, "chk_launch"))
        for check, name_key, desc_key in (
            (self.start_menu_check, "acc_start_menu_n", "acc_start_menu_d"),
            (self.desktop_check, "acc_desktop_n", "acc_desktop_d"),
            (self.model_check, "acc_model_n", "acc_model_d"),
            (self.launch_check, "acc_launch_n", "acc_launch_d"),
        ):
            check.setAccessibleName(tr(lang, name_key))
            check.setAccessibleDescription(tr(lang, desc_key))
            check.setToolTip(tr(lang, desc_key))
        self.tools_title.setText(tr(lang, "tools_title"))
        self.recheck_button.setText(tr(lang, "btn_recheck"))
        self.recheck_button.setAccessibleName(tr(lang, "acc_recheck_n"))
        self.recheck_button.setAccessibleDescription(tr(lang, "acc_recheck_d"))
        self.tools_box.setAccessibleName(tr(lang, "acc_tools_n"))
        self.tools_box.setAccessibleDescription(tr(lang, "acc_tools_d"))
        self.back_button.setText(tr(lang, "btn_back"))
        self.back_button.setAccessibleName(tr(lang, "acc_back_n"))
        self.back_button.setAccessibleDescription(tr(lang, "acc_back_d"))
        self.exit_button.setText(tr(lang, "btn_exit"))
        self.exit_button.setAccessibleName(tr(lang, "acc_exit_n"))
        self.exit_button.setAccessibleDescription(tr(lang, "acc_exit_d"))
        self.progress.setAccessibleName(tr(lang, "acc_progress_n"))
        self.progress.setAccessibleDescription(
            tr(lang, "acc_progress_d", value=self.progress.value())
        )
        self.steps_box.setAccessibleName(tr(lang, "acc_steps_n"))
        self.steps_box.setAccessibleDescription(tr(lang, "acc_steps_d"))

        self._render_tools()
        self._retranslate_steps()
        self._sync_buttons()

    # ------------------------------------------------------------------ tools
    def _check_tools(self):
        import vt_install

        self.tools = vt_install.check_video_tools(bundled=self.installer_mode)
        # Only offer the download when something is genuinely missing; a model
        # shipped with the program is already there and needs no decision.
        self.model_check.setVisible(
            not self.installer_mode and not vt_install.model_is_local()
        )
        if self.tools.get("model") == "download on first use":
            self.model_check.setChecked(True)
        else:
            self.model_check.setChecked(False)
        self._render_tools()
        self._sync_buttons()
        return self.tools

    def _render_tools(self):
        while self.tools_layout.count():
            item = self.tools_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        if not self.tools:
            return
        rows = (
            ("tool_ffmpeg", self.tools.get("ffmpeg", "?")),
            ("tool_ffprobe", self.tools.get("ffprobe", "")),
            ("tool_pillow", self.tools.get("pillow", "?")),
            ("tool_font", self.tools.get("font", "?")),
            ("tool_model", self.tools.get("model", "?")),
        )
        ok = bool(self.tools.get("ok"))
        missing_state = tr(self.language, "tool_missing")
        for key, value in rows:
            value = str(value)
            if not value or value == "?":
                continue
            if value.startswith("ready") or value == "bundled":
                state = tr(self.language, "tool_ok")
                shown = value
            elif "download" in value:
                state = tr(self.language, "tool_download")
                shown = value
            elif value.startswith("optional"):
                # ffprobe is not required: probing runs through the bundled ffmpeg.
                state = tr(self.language, "tool_optional")
                shown = tr(self.language, "tool_not_installed")
            else:
                state = missing_state
                shown = value
            label = QLabel("{}: {} - {}".format(tr(self.language, key), shown, state))
            label.setObjectName("toolRow")
            label.setProperty("state", "failed" if state == missing_state else "done")
            label.style().unpolish(label)
            label.style().polish(label)
            label.setAccessibleName(tr(self.language, "acc_tools_n"))
            label.setAccessibleDescription(label.text())
            self.tools_layout.addWidget(label)
        if not ok:
            warning = QLabel(tr(self.language, "tools_missing"))
            warning.setObjectName("toolRow")
            warning.setProperty("state", "failed")
            warning.style().unpolish(warning)
            warning.style().polish(warning)
            warning.setAccessibleDescription(warning.text())
            self.tools_layout.addWidget(warning)

    # ------------------------------------------------------------- navigation
    def _on_browse(self):
        import vt_install

        start = self.folder_edit.text().strip() or vt_install.default_install_dir()
        chosen = QFileDialog.getExistingDirectory(self, tr(self.language, "acc_browse_d"), start)
        if chosen:
            self.folder_edit.setText(os.path.normpath(chosen))
            self.radio_custom.setChecked(True)

    def _on_mode_changed(self, _index, checked):
        if not checked:
            return
        mode = self._selected_mode()
        run_in_place = mode == MODE_PORTABLE and not self._payload_is_archive()
        self.folder_edit.setEnabled(mode != MODE_PORTABLE or run_in_place)
        self.browse_button.setEnabled(mode != MODE_PORTABLE or run_in_place)
        self.start_menu_check.setEnabled(mode != MODE_PORTABLE)
        self.desktop_check.setEnabled(mode != MODE_PORTABLE)
        current = self.folder_edit.text().strip()
        if not current or current == self._auto_folder:
            # only replace the folder while the user has not picked one
            self._auto_folder = self._default_folder()
            self.folder_edit.setText(self._auto_folder)
        if mode != MODE_PORTABLE and not (
            self.start_menu_check.isChecked() or self.desktop_check.isChecked()
        ):
            self.start_menu_check.setChecked(True)
        self._sync_buttons()

    def _on_back(self):
        if self.installing:
            return
        self.stack.setCurrentIndex(0)
        self._sync_buttons()
        self.banner.start()
        play_welcome_music()

    def _on_next(self):
        index = self.stack.currentIndex()
        if index == 0:
            # Nothing has to be accepted any more: the welcome page only
            # remembers the interface language and moves on.
            save_setup(self.language)
            stop_music()
            self.banner.stop()
            if getattr(self, "app_installed", False):
                # Already installed: this launch is only the welcome screen,
                # do not repeat the installation steps.
                self.accept()
                return
            self.stack.setCurrentIndex(1)
            if not self.tools:
                self._check_tools()
            self._sync_buttons()
            self.next_button.setFocus()
            return
        if self.install_finished:
            self.accept()
            return
        if not self.installing:
            self._start_install()

    def _sync_buttons(self, *_args):
        index = self.stack.currentIndex()
        lang = self.language
        self.back_button.setEnabled(index == 1 and not self.installing)
        self.exit_button.setEnabled(not self.installing)
        if index == 0:
            if getattr(self, "app_installed", False):
                self.next_button.setText(tr(lang, "btn_start"))
                self.next_button.setAccessibleName(tr(lang, "acc_finish_n"))
                self.next_button.setAccessibleDescription(tr(lang, "acc_finish_d"))
            else:
                self.next_button.setText(tr(lang, "btn_next"))
                self.next_button.setAccessibleName(tr(lang, "acc_next_n"))
                self.next_button.setAccessibleDescription(tr(lang, "acc_next_d"))
            self.next_button.setEnabled(True)
        elif self.installing:
            self.next_button.setText(tr(lang, "btn_install"))
            self.next_button.setEnabled(False)
            self.next_button.setAccessibleName(tr(lang, "acc_install_n"))
            self.next_button.setAccessibleDescription(tr(lang, "acc_install_d"))
        else:
            portable = self.mode_group.checkedId() == 1
            up_to_date = self._already_installed()
            if self.install_finished:
                self.next_button.setText(tr(lang, "btn_finish"))
                self.next_button.setAccessibleName(tr(lang, "acc_finish_n"))
                self.next_button.setAccessibleDescription(tr(lang, "acc_finish_d"))
            elif up_to_date:
                self.next_button.setText(tr(lang, "btn_start"))
                self.next_button.setAccessibleName(tr(lang, "acc_finish_n"))
                self.next_button.setAccessibleDescription(tr(lang, "acc_finish_d"))
            else:
                self.next_button.setText(
                    tr(lang, "btn_start") if portable else tr(lang, "btn_install")
                )
                self.next_button.setAccessibleName(tr(lang, "acc_install_n"))
                self.next_button.setAccessibleDescription(tr(lang, "acc_install_d"))
            self.next_button.setEnabled(True)

    # -------------------------------------------------------------- installing
    def _selected_mode(self) -> str:
        return (MODE_STANDARD, MODE_PORTABLE, MODE_CUSTOM)[self.mode_group.checkedId()]

    def _payload_is_archive(self) -> bool:
        """True when the payload is a compressed payload inside the setup exe."""
        return str(self.payload).lower().endswith(".lzma")

    def _default_folder(self) -> str:
        import vt_install

        if self._selected_mode() == MODE_PORTABLE:
            return vt_install.portable_dir()
        return self.install_dir or vt_install.default_install_dir()

    def _target_dir(self) -> str:
        import vt_install

        mode = self._selected_mode()
        if mode == MODE_PORTABLE and not self._payload_is_archive():
            # the program keeps running from the folder it was started from
            return os.path.dirname(os.path.abspath(self.payload)) or vt_install.portable_dir()
        folder = self.folder_edit.text().strip() or self._default_folder()
        return os.path.abspath(os.path.expandvars(os.path.expanduser(folder)))

    def _already_installed(self) -> bool:
        import vt_install

        if self._selected_mode() == MODE_PORTABLE:
            return False
        target = self._target_dir()
        if not target or not vt_install.payload_is_ready(vt_install.install_exe(target)):
            return False
        return bool(self.start_menu_check.isChecked() or self.desktop_check.isChecked())

    def _start_install(self):
        import vt_install

        self.install_finished = False
        self.installing = True
        self.progress.setValue(0)
        self.install_status.setText(tr(self.language, "install_hint"))
        self.install_status.setStyleSheet("color: #9a9aa4; font-weight: 400;")
        self._sync_buttons()

        mode = self._selected_mode()
        target = self._target_dir()
        want_start_menu = mode != MODE_PORTABLE and self.start_menu_check.isChecked()
        want_desktop = mode != MODE_PORTABLE and self.desktop_check.isChecked()
        want_model = (
            self.model_check.isChecked()
            and not vt_install.model_is_local()
            and not vt_install.model_is_cached()
        )
        payload = self.payload

        plan = {
            "mode": mode,
            "target": target,
            "payload": payload,
            "uninstaller": self.uninstaller,
            "archive": self._payload_is_archive(),
            "start_menu": want_start_menu,
            "desktop": want_desktop,
            "model": want_model,
        }

        for widget in self._step_rows:
            widget.setParent(None)
        self._step_rows = []
        self._steps = [
            InstallStep("step_folder", self._step_folder),
            InstallStep("step_payload", self._step_payload),
            InstallStep("step_shortcuts", self._step_shortcuts),
            InstallStep("step_register", self._step_register),
            InstallStep("step_tools", self._step_tools),
            InstallStep("step_final", self._step_final),
        ]
        for step in self._steps:
            label = QLabel("")
            label.setObjectName("stepRow")
            label.setProperty("state", "pending")
            self.steps_layout.addWidget(label)
            self._step_rows.append(label)
            self._render_step(len(self._step_rows) - 1)

        self.worker = InstallThread(self._steps, plan, self)
        self.worker.stepChanged.connect(self._on_step_changed)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished_ok.connect(self._on_install_done)
        self.worker.start()

    def _render_step(self, index):
        if index >= len(self._steps):
            return
        step = self._steps[index]
        state = step.state
        base = tr(self.language, step.key)
        if state == "pending":
            text = "{}  [{}]".format(base, tr(self.language, "state_pending"))
        elif state == "running":
            text = "{}  [{}]".format(base, tr(self.language, "state_running"))
        elif state == "failed":
            text = "{}  [{}]".format(
                base, tr(self.language, "install_failed", msg=step.message)[:120]
            )
        elif state == "skipped":
            text = "{}  [{}]".format(base, tr(self.language, "state_skipped"))
        else:
            text = "{}  [{}]".format(base, tr(self.language, "state_done"))
            if step.message:
                text += " - " + step.message
        label = self._step_rows[index]
        label.setText(text)
        label.setProperty("state", state)
        label.style().unpolish(label)
        label.style().polish(label)
        label.setAccessibleDescription(text)

    def _retranslate_steps(self):
        for index in range(len(self._steps)):
            self._render_step(index)

    def _on_step_changed(self, index, state, message):
        if index < len(self._steps):
            self._steps[index].state = state
            self._steps[index].message = message
            self._render_step(index)

    def _on_progress(self, value):
        self.progress.setValue(value)
        self.progress.setAccessibleDescription(
            tr(self.language, "acc_progress_d", value=value)
        )

    def _on_install_done(self, _note):
        import vt_install

        self.installing = False
        self.install_finished = True
        self.progress.setValue(100)
        self.progress.setAccessibleDescription(
            tr(self.language, "acc_progress_d", value=100)
        )
        failures = [step for step in self._steps if step.state == "failed"]
        if failures:
            self.install_status.setText(failures[0].message or tr(self.language, "install_done"))
            self.install_status.setStyleSheet("color: #ff8f8f; font-weight: 700;")
        elif self._selected_mode() == MODE_PORTABLE:
            self.install_status.setText(tr(self.language, "install_portable"))
            self.install_status.setStyleSheet("color: #7BE495; font-weight: 700;")
        else:
            self.install_status.setText(tr(self.language, "install_done"))
            self.install_status.setStyleSheet("color: #7BE495; font-weight: 700;")
        self.tools = vt_install.check_video_tools(bundled=self.installer_mode)
        self._render_tools()
        self._sync_buttons()

    # ------------------------------------------------------------- step bodies
    def _step_folder(self, worker):
        import vt_install

        plan = worker.plan
        if plan["mode"] == MODE_PORTABLE:
            return tr(self.language, "install_portable")
        os.makedirs(plan["target"], exist_ok=True)
        probe = os.path.join(plan["target"], ".write_test")
        with open(probe, "w", encoding="utf-8") as handle:
            handle.write("ok")
        os.remove(probe)
        return os.path.basename(plan["target"])

    def _step_payload(self, worker):
        import vt_install

        plan = worker.plan
        if plan["mode"] == MODE_PORTABLE and not plan["archive"]:
            return tr(self.language, "state_skipped")
        if not plan["archive"] and not vt_install.frozen_exe():
            # running from a source tree: there is no separate file to copy
            return tr(self.language, "state_skipped")
        source = plan["payload"]
        if not vt_install.payload_is_ready(source):
            raise RuntimeError("the application file is missing: %s" % source)

        if plan["archive"]:
            target = vt_install.unpack_payload(
                source,
                vt_install.install_exe(plan["target"]),
                progress=lambda value: worker.report(int(value * 0.9)),
            )
        else:
            target = vt_install.copy_payload(
                source, plan["target"], progress=lambda value: worker.report(int(value * 0.9))
            )

        if plan["uninstaller"]:
            vt_install.unpack_payload(plan["uninstaller"], self._uninstaller_path(plan))

        save_setup(
            self.language,
            install_dir=plan["target"],
            install_mode=plan["mode"],
            installed_version=vt_install.app_version(),
        )
        return os.path.basename(target)

    def _uninstaller_path(self, plan=None) -> str:
        import vt_install

        plan = plan or {"target": self._target_dir()}
        return os.path.join(plan["target"], vt_install.UNINSTALLER_NAME)

    def _step_shortcuts(self, worker):
        import vt_install

        plan = worker.plan
        if plan["mode"] == MODE_PORTABLE or not (plan["start_menu"] or plan["desktop"]):
            return tr(self.language, "step_skipped_shortcuts")
        target = vt_install.install_exe(plan["target"])
        uninstaller = self._uninstaller_path(plan)
        created = vt_install.create_shortcuts(
            target,
            uninstaller if os.path.exists(uninstaller) else "",
            start_menu=plan["start_menu"],
            desktop=plan["desktop"],
        )
        if created and created[0].startswith("shortcut error"):
            return created[0]
        return "%d shortcut(s)" % len(created)

    def _step_register(self, worker):
        import vt_install

        plan = worker.plan
        if plan["mode"] == MODE_PORTABLE:
            return tr(self.language, "state_skipped")
        size = vt_install.install_size_mb(plan["target"])
        result = vt_install.register_uninstall(
            plan["target"],
            size,
            uninstaller=(
                self._uninstaller_path(plan)
                if os.path.exists(self._uninstaller_path(plan))
                else ""
            ),
        )
        return result if result.startswith("registry") else "v" + vt_install.app_version()

    def _step_tools(self, worker):
        import vt_install

        report = vt_install.check_video_tools(bundled=self.installer_mode)
        if worker.plan.get("model") and not self.installer_mode:
            report["model"] = vt_install.download_model(
                "base", progress=lambda value: worker.report(int(value * 0.2))
            )
        if not report["ok"]:
            raise RuntimeError(
                "ffmpeg: %s, captions: %s, font: %s"
                % (report["ffmpeg"], report["pillow"], report["font"])
            )
        return "%s / %s" % (report["pillow"], report["font"])

    def _step_final(self, worker):
        import vt_install

        plan = worker.plan
        marker = os.path.join(vt_install.app_data_dir(), "installed.flag")
        try:
            with open(marker, "w", encoding="utf-8") as handle:
                handle.write(
                    "version={}\nmode={}\ndir={}\ntime={}\n".format(
                        vt_install.app_version(),
                        plan["mode"],
                        plan["target"],
                        time.time(),
                    )
                )
        except OSError:
            pass
        return tr(self.language, "step_already")

    # ------------------------------------------------------------------ close
    def _stop_extras(self, *_args):
        try:
            self.banner.stop()
        except Exception:
            pass
        stop_music()

    def _stop_worker(self):
        worker = self.worker
        if worker is not None and worker.isRunning():
            worker.cancel()
            worker.wait(3000)

    def closeEvent(self, event):
        self._stop_worker()
        self._stop_extras()
        super().closeEvent(event)

    def _center(self, width, height):
        _center(self, width, height)

    def should_launch(self) -> bool:
        if not self.installer_mode:
            return True
        return bool(self.launch_check.isChecked() and self.install_finished)


WELCOME_SECONDS = 3.0
EXIT_SECONDS = 3.0


class _WelcomePanel(QDialog):
    """First-run greeting with an explicit Continue button.

    Accessibility contract:

    * the exact welcome sentence is the accessible name of a focusable label,
      so the screen reader speaks it the moment the window opens;
    * focus then lands on the **Continue** button (Enter, Space, Escape or a
      click all dismiss the panel), so the user is never trapped and never has
      to guess what to press;
    * no timer closes the panel behind the user's back.
    """

    def __init__(self, language: str, seconds: float = WELCOME_SECONDS, parent=None):
        super().__init__(parent)
        self.language = language if language in ("en", "ar") else "en"
        self._seconds = max(0.0, float(seconds))

        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setWindowTitle(tr(self.language, "welcome_title"))
        self.setAccessibleName(WELCOME_TEXT)
        self.setAccessibleDescription(tr(self.language, "welcome_access_d"))
        self.setLayoutDirection(
            Qt.LayoutDirection.RightToLeft
            if self.language == "ar"
            else Qt.LayoutDirection.LeftToRight
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        self.banner = AnimatedBanner(WELCOME_TEXT, mode="welcome")
        self.banner.setAccessibleName(tr(self.language, "welcome_access"))
        self.banner.setAccessibleDescription(WELCOME_TEXT)
        root.addWidget(self.banner, 2)

        # The exact sentence: focused first so it is announced automatically.
        self.message = QLabel(WELCOME_TEXT)
        self.message.setObjectName("wizTitle")
        self.message.setWordWrap(True)
        self.message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message.setAccessibleName(WELCOME_TEXT)
        self.message.setAccessibleDescription(tr(self.language, "welcome_status_n"))
        self.message.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        root.addWidget(self.message)

        hint = QLabel(tr(self.language, "welcome_auto"))
        hint.setObjectName("wizSubtitle")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setAccessibleDescription(tr(self.language, "welcome_auto"))
        root.addWidget(hint)

        self.continue_button = QPushButton(tr(self.language, "btn_continue"))
        self.continue_button.setObjectName("welcomeContinue")
        self.continue_button.setAccessibleName(tr(self.language, "btn_continue_n"))
        self.continue_button.setAccessibleDescription(
            WELCOME_TEXT + ". " + tr(self.language, "btn_continue_d")
        )
        self.continue_button.setAutoDefault(True)
        self.continue_button.setDefault(True)
        self.continue_button.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(self.continue_button)
        row.addStretch(1)
        root.addLayout(row)

    # ----------------------------------------------------------------- window
    def showEvent(self, event):
        super().showEvent(event)
        # Our own window replaces the boot splash drawn by the bootloader.
        close_boot_splash()
        try:
            self.activateWindow()
            self.message.setFocus(Qt.FocusReason.OtherFocusReason)
        except Exception:  # noqa: BLE001 - announcement is best effort
            pass
        self.banner.start()
        play_welcome_music()
        # Some window managers only hand over focus after the first event
        # pass; make sure the announcement lands even then.
        QTimer.singleShot(0, self._claim_focus)
        # The sentence first (so it is spoken), then the Continue button, so
        # that focus ends up on the control the user is asked to press.
        QTimer.singleShot(900, self._land_on_continue)
        # The panel closes itself after a few seconds; the Continue button
        # (or Enter/Space/Escape) still closes it earlier.
        if self._seconds > 0:
            QTimer.singleShot(int(self._seconds * 1000), self._auto_close)

    def _auto_close(self):
        if self.isVisible():
            self.accept()

    def _claim_focus(self):
        if not self.isVisible():
            return
        try:
            if self.message.focusPolicy() != Qt.FocusPolicy.NoFocus:
                self.message.setFocus(Qt.FocusReason.OtherFocusReason)
        except Exception:  # noqa: BLE001 - announcement is best effort
            pass

    def _land_on_continue(self):
        if not self.isVisible():
            return
        try:
            self.continue_button.setFocus(Qt.FocusReason.OtherFocusReason)
        except Exception:  # noqa: BLE001 - focus is best effort
            pass

    def keyPressEvent(self, event):
        # Enter/Space activate the default Continue button; Escape dismisses.
        key = event.key()
        if key in (Qt.Key.Key_Escape, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        self.banner.stop()
        stop_music()
        super().closeEvent(event)

    def done(self, code):
        self.banner.stop()
        stop_music()
        super().done(code)


def welcome_already_shown() -> bool:
    """True when the first-run greeting has been acknowledged before."""
    try:
        return bool(load_setup().get("welcome_shown"))
    except Exception:  # noqa: BLE001 - never block start-up on a flag
        return False


def mark_welcome_shown() -> None:
    try:
        save_setup(saved_language() or "en", welcome_shown=True)
    except Exception:  # noqa: BLE001 - the flag is a convenience only
        logging.getLogger("vidtrans.setup").exception("welcome flag not saved")


def show_welcome_screen(app=None, seconds: float = WELCOME_SECONDS, force: bool = False) -> str:
    """Show the greeting, then return the interface language.

    The panel appears on every launch, closes itself after ``seconds`` (or
    when the user presses **Continue**, Enter, Space or Escape), and the main
    window opens afterwards.  A failure to build the panel is never fatal --
    the application simply starts.
    """
    language = saved_language() or "en"
    try:
        panel = _WelcomePanel(language, seconds)
        if app is not None and getattr(panel, "screen", None) is not None:
            _centre(panel)
        panel.exec()
        language = panel.language
        mark_welcome_shown()
    except Exception:  # noqa: BLE001 - the greeting must never block start-up
        logging.getLogger("vidtrans.setup").exception("the welcome screen could not be shown")
    return language if language in ("en", "ar") else "en"


def _centre(widget) -> None:
    """Place *widget* in the middle of the available screen area."""
    screen = widget.screen()
    if screen is None:
        return
    area = screen.availableGeometry()
    widget.move(
        area.x() + max(0, (area.width() - widget.width()) // 2),
        area.y() + max(0, (area.height() - widget.height()) // 2),
    )


def run_setup(app=None, mode="app", payload="", uninstaller="") -> tuple:
    """Show the welcome and install screens.  Returns ``(accepted, language)``.

    Only the installer uses this dialog: the application itself opens with
    :func:`show_welcome_screen` and never presents a licence.  A failure to
    build the dialog is never fatal, the caller simply continues.
    """
    try:
        wizard = SetupWizard(mode=mode, payload=payload, uninstaller=uninstaller)
        wizard.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        code = wizard.exec()
        return (code == QDialog.DialogCode.Accepted, wizard.language)
    except Exception:
        logging.getLogger("vidtrans.setup").exception("the setup wizard could not be shown")
        return True, saved_language() or "en"


# ------------------------------------------------------------------ exit screen
def show_exit_screen(app, on_finished) -> bool:
    """Goodbye message: the exact farewell sentence plus an OK button.

    The dialog is modal and waits for the user, so the sentence is always
    spoken by the screen reader and the program never closes before the
    message has been displayed.  Enter, Space, Escape or a click on OK all
    finish the program; nothing else can.
    """
    try:
        language = saved_language() or "en"
        box = QDialog()
        box.setModal(True)
        box.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        box.setWindowTitle(tr(language, "exit_title"))
        box.setAccessibleName(FAREWELL_TEXT)
        box.setAccessibleDescription(tr(language, "exit_hint"))
        box.setLayoutDirection(
            Qt.LayoutDirection.RightToLeft
            if language == "ar"
            else Qt.LayoutDirection.LeftToRight
        )

        root = QVBoxLayout(box)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        banner = AnimatedBanner(FAREWELL_TEXT, mode="exit")
        banner.setAccessibleName(FAREWELL_TEXT)
        banner.setAccessibleDescription(FAREWELL_TEXT)
        root.addWidget(banner, 2)

        message = QLabel(FAREWELL_TEXT)
        message.setObjectName("wizTitle")
        message.setWordWrap(True)
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message.setAccessibleName(FAREWELL_TEXT)
        message.setAccessibleDescription(tr(language, "welcome_status_n"))
        message.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        root.addWidget(message)

        hint = QLabel(tr(language, "exit_hint"))
        hint.setObjectName("wizSubtitle")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setAccessibleDescription(tr(language, "exit_hint"))
        root.addWidget(hint)

        ok_button = QPushButton(tr(language, "btn_ok"))
        ok_button.setAccessibleName(tr(language, "btn_ok_n"))
        ok_button.setAccessibleDescription(FAREWELL_TEXT + ". " + tr(language, "exit_hint"))
        ok_button.setAutoDefault(True)
        ok_button.setDefault(True)
        ok_button.clicked.connect(box.accept)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(ok_button)
        buttons.addStretch(1)
        root.addLayout(buttons)

        box.resize(640, 340)
        _centre(box)
        box.show()
        box.raise_()
        box.activateWindow()
        banner.start()
        play_farewell_music()
        # The sentence first (so it is spoken automatically), then focus lands
        # on the OK button the user is asked to press.
        message.setFocus(Qt.FocusReason.OtherFocusReason)
        QTimer.singleShot(0, lambda: message.setFocus(Qt.FocusReason.OtherFocusReason))
        QTimer.singleShot(900, lambda: ok_button.setFocus(Qt.FocusReason.OtherFocusReason))
        # The goodbye screen closes itself after a few seconds; the OK button
        # (or Enter/Space/Escape) still closes it earlier.
        QTimer.singleShot(int(EXIT_SECONDS * 1000), box.accept)
        box.exec()
        banner.stop()
        stop_music()
        box.close()
        on_finished()
        return True
    except Exception:
        logging.getLogger("vidtrans.setup").exception("the exit message could not be shown")
        return False
