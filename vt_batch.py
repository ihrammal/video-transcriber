"""Keyboard-accessible serial transcription queue, using the existing worker."""
import json
import os
from pathlib import Path
import tempfile
import shutil

import srt
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QDialog, QFileDialog, QHBoxLayout, QLabel, QListWidget,
                              QMessageBox, QProgressBar, QPushButton, QScrollArea, QVBoxLayout, QWidget)

from vt_i18n import tr
from vt_workers import TranscriptionThread


class BatchDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.lang = parent.current_lang
        self.paths = []
        self.states = []
        self.output_folder = ""
        self.worker = None
        self.running = False
        self.index = 0
        self.stopping = False
        self.report = []
        self.setWindowTitle(self.t("batch_title"))
        self.setAccessibleName(self.t("batch_title"))
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if self.lang == "ar" else Qt.LayoutDirection.LeftToRight)
        root = QVBoxLayout(self)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        page = QWidget(scroll)
        scroll.setWidget(page)
        root.addWidget(scroll)
        layout = QVBoxLayout(page)
        hint = QLabel(self.t("batch_hint"))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.list = QListWidget(self)
        self.list.setAccessibleName(self.t("batch_list"))
        layout.addWidget(self.list)
        row = QHBoxLayout()
        self.add_button = QPushButton(self.t("batch_add"))
        self.add_button.clicked.connect(self.choose_files)
        self.remove_button = QPushButton(self.t("batch_remove"))
        self.remove_button.clicked.connect(self.remove_selected)
        self.folder_button = QPushButton(self.t("batch_folder"))
        self.folder_button.clicked.connect(self.choose_folder)
        for button in (self.add_button, self.remove_button, self.folder_button):
            row.addWidget(button)
        layout.addLayout(row)
        self.output_label = QLabel(self.t("batch_output", path=""))
        self.output_label.setWordWrap(True)
        layout.addWidget(self.output_label)
        self.progress = QProgressBar()
        self.progress.setAccessibleName(self.t("batch_title"))
        layout.addWidget(self.progress)
        self.status = QLabel(self.t("batch_hint"))
        self.status.setWordWrap(True)
        self.status.setAccessibleName(self.t("acc_status_n"))
        layout.addWidget(self.status)
        buttons = QHBoxLayout()
        self.start_button = QPushButton(self.t("batch_start"))
        self.start_button.clicked.connect(self.start_queue)
        self.stop_button = QPushButton(self.t("batch_cancel"))
        self.stop_button.clicked.connect(self.stop_queue)
        self.stop_button.setEnabled(False)
        self.close_button = QPushButton(self.t("batch_close"))
        self.close_button.clicked.connect(self.close)
        for button in (self.start_button, self.stop_button, self.close_button):
            buttons.addWidget(button)
        layout.addLayout(buttons)
        for button in self.findChildren(QPushButton):
            button.setAutoDefault(False)
            button.setAccessibleName(button.text())
        self.resize(760, 560)
        import vt_a11y
        vt_a11y.apply_descriptions(self)

    def t(self, key, **values):
        return tr(self.lang, key, **values)

    def add_paths(self, paths):
        if self.running:
            return
        existing = {os.path.normcase(os.path.abspath(path)) for path in self.paths}
        for path in paths:
            normalized = os.path.normcase(os.path.abspath(path))
            if normalized not in existing and os.path.isfile(path):
                self.paths.append(os.path.abspath(path))
                self.states.append(self.t("batch_waiting"))
                self.list.addItem(self.t("batch_item", name=os.path.basename(path), state=self.states[-1]))
                existing.add(normalized)

    def choose_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, self.t("dlg_open_video"), "", self.t("dlg_video_filter"))
        self.add_paths(paths)

    def remove_selected(self):
        if self.running:
            return
        row = self.list.currentRow()
        if row >= 0:
            self.list.takeItem(row)
            del self.paths[row]
            del self.states[row]

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, self.t("batch_folder_title"), self.output_folder)
        if folder:
            self.output_folder = folder
            self.output_label.setText(self.t("batch_output", path=folder))

    def start_queue(self):
        if self.running:
            return
        if not self.paths or not os.path.isdir(self.output_folder):
            QMessageBox.information(self, self.t("batch_title"), self.t("batch_empty"))
            return
        choice = self.parent()._engine_choice("transcribe")
        if choice is None:
            return
        import vt_prefs
        prefs = vt_prefs.normalized(vt_prefs.load())
        self.engine, self.api_key, _ = choice
        self.model = prefs["whisper_model"] if self.engine == "local" else prefs[self.engine + "_model"]
        self.language = self.parent().language_combo.currentData()
        try:
            self.destination = Path(tempfile.mkdtemp(prefix="batch-", dir=self.output_folder))
        except OSError as error:
            QMessageBox.warning(self, self.t("batch_title"), str(error))
            return
        self.index = 0
        self.stopping = False
        self.report = []
        self.running = True
        self.progress.setRange(0, len(self.paths))
        self.progress.setValue(0)
        for button in (self.add_button, self.remove_button, self.folder_button, self.start_button):
            button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self._next()

    def _state(self, index, state):
        self.states[index] = state
        self.list.item(index).setText(self.t("batch_item", name=os.path.basename(self.paths[index]), state=state))

    def _next(self):
        if not self.running:
            return
        if self.stopping or self.index >= len(self.paths):
            self.running = False
            if self.stopping:
                for index in range(self.index, len(self.paths)):
                    self._state(index, self.t("batch_cancelled"))
            saved = sum(item.get("saved", False) for item in self.report)
            message = self.t("batch_complete", done=saved, total=len(self.paths))
            self.status.setText(message)
            self.parent().announce(message)
            self.api_key = ""
            self.stop_button.setEnabled(False)
            for button in (self.add_button, self.remove_button, self.folder_button, self.start_button):
                button.setEnabled(True)
            return
        self._state(self.index, self.t("batch_working"))
        self.status.setText(self.list.item(self.index).text())
        self.parent().announce(self.status.text())
        self._recorded = False
        self._work_dir = None
        try:
            work = tempfile.mkdtemp(prefix="batch-audio-", dir=self.parent().temp_dir)
        except OSError as error:
            self._failed(str(error))
            self._finished()
            return
        self._work_dir = Path(work)
        self.worker = TranscriptionThread(self.paths[self.index], "", self.language, work,
                                          model_name=self.model, lang=self.lang,
                                          engine=self.engine, api_key=self.api_key)
        self.worker.completed.connect(self._completed)
        self.worker.failed.connect(self._failed)
        self.worker.finished.connect(self._finished)
        self._recorded = False
        self.worker.start()

    def _completed(self, subtitles, detected, audio):
        if self.stopping:
            self._failed(self.t("batch_cancelled"))
            return
        stem = "%03d_%s" % (self.index + 1, Path(self.paths[self.index]).stem[:80])
        text_path = self.destination / (stem + ".txt")
        subtitle_path = self.destination / (stem + ".srt")
        try:
            text_path.write_text("\n".join(sub.content for sub in subtitles) + "\n", encoding="utf-8")
            subtitle_path.write_text(srt.compose(subtitles), encoding="utf-8-sig")
        except OSError as error:
            self._failed(str(error))
            return
        self.report.append({"source": self.paths[self.index], "saved": True, "language": detected,
                            "text": text_path.name, "subtitles": subtitle_path.name})
        self._recorded = True
        self._state(self.index, self.t("batch_done"))

    def _failed(self, message):
        if self._recorded:
            return
        self._recorded = True
        self.report.append({"source": self.paths[self.index], "saved": False, "error": str(message)})
        self._state(self.index, self.t("batch_cancelled") if self.stopping else self.t("batch_failed", error=message))

    def _finished(self):
        if not self._recorded:
            self._failed(self.t("batch_cancelled"))
        if self.worker is not None:
            self.worker.deleteLater()
        self.worker = None
        root = Path(self.parent().temp_dir).resolve()
        work = self._work_dir.resolve() if self._work_dir else None
        if work and work != root and work.is_relative_to(root):
            shutil.rmtree(work, ignore_errors=True)
        self.index += 1
        self.progress.setValue(self.index)
        try:
            (self.destination / "batch-report.json").write_text(json.dumps(self.report, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            self.parent().announce(self.t("msg_recovery_failed"))
        QTimer.singleShot(0, self._next)

    def stop_queue(self):
        self.stopping = True
        if self.worker:
            self.worker.requestInterruption()
            self.status.setText(self.t("batch_stopping"))
            self.stop_button.setEnabled(False)

    def reject(self):
        if self.running:
            self.stop_queue()
            return
        super().reject()

    def closeEvent(self, event):
        if self.running:
            self.stop_queue()
            event.ignore()
        else:
            event.accept()
