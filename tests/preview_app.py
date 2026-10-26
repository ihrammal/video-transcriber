"""Launch the working source with an isolated profile for manual accessibility QA."""
import os
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
os.environ["LOCALAPPDATA"] = str(root / "test-results" / "manual-profile")
from PySide6.QtWidgets import QApplication
from vid_trans_app import MainWindow
import vt_a11y
import vt_secrets

vt_secrets.is_available = lambda: False

app = QApplication([])
vt_a11y.update(sounds=False, show_welcome=False, show_farewell=False)
window = MainWindow("ar" if "--ar" in sys.argv else "en")
window.show()
app.exec()
