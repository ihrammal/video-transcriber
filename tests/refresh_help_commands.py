"""Refresh generated command tables in the two language guides."""
import html
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["LOCALAPPDATA"] = str(ROOT / "test-results" / "help-profile")
from PySide6.QtWidgets import QApplication
from vid_trans_app import MainWindow
import vt_secrets
vt_secrets.is_available = lambda: False
app = QApplication([])

for language in ("en", "ar"):
    window = MainWindow(language)
    rows = []
    for action, key in window._action_map:
        sequence = action.shortcut().toString()
        if sequence:
            rows.append("<tr><td>" + html.escape(window.t(key).replace("&", ""))
                        + "</td><td><kbd>" + html.escape(sequence) + "</kbd></td></tr>")
    title = "Current commands and keyboard shortcuts" if language == "en" else "الأوامر الحالية واختصارات لوحة المفاتيح"
    note = ("Accessibility, recovery, text size, and automatic update options are in Preferences. "
            "Tools offers batch transcription. Audio recordings can be rendered as captioned MP4 files with a plain background."
            if language == "en" else
            "توجد خيارات إمكانية الوصول والاستعادة وحجم النص والتحديثات التلقائية ضمن التفضيلات. "
            "تتيح قائمة الأدوات تفريغ مجموعة ملفات. يمكن إنشاء فيديو بالتسميات من التسجيلات الصوتية على خلفية بسيطة.")
    section = '<section id="current-commands"><h2>' + title + "</h2><p>" + note + "</p><table><tbody>" + "".join(rows) + "</tbody></table></section>"
    for folder in ("resources/help", "help"):
        for path in (ROOT / folder).rglob("*.html"):
            lang = "ar" if "ar" in path.parts or path.stem.endswith("_ar") else "en"
            if lang == language:
                source = path.read_text(encoding="utf-8")
                source = re.sub(r'<section id="current-commands">.*?</section>', lambda _: section, source, flags=re.S)
                path.write_text(source, encoding="utf-8")
    window.deleteLater()
    app.processEvents()
