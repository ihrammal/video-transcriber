"""vt_settings.py -- the Preferences dialog: which engine transcribes, which
one translates, and the API keys that go with them.

Design rules:

* Every control carries an AccessibleName / AccessibleDescription in the active
  interface language, so NVDA, JAWS and Narrator announce the same words that
  are painted on the screen.
* Nothing in here may crash the application: a missing key, a malformed key or
  an unreachable network produces a translated ``QMessageBox`` and, where it
  makes sense, an automatic fall back to the free local engine.
* The dialog never blocks: "Test key" runs in its own thread and reports back
  through a signal.
"""

from __future__ import annotations

import logging
import os

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QCheckBox,
    QTabWidget,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import vt_prefs
from vt_i18n import tr

log = logging.getLogger("vidtrans.settings")

ENGINE_KEYS = ("local", "openai", "groq", "gemini")

# Where a user can create a key for each provider (opened by "Get API key").
KEY_URLS = {
    "openai": "https://platform.openai.com/api-keys",
    "groq": "https://console.groq.com/keys",
    "gemini": "https://aistudio.google.com/app/apikey",
}


class KeyTestThread(QThread):
    finished = Signal(bool, str)

    def __init__(self, engine, key, lang="en", parent=None):
        super().__init__(parent)
        self.engine = engine
        self.key = key
        self.lang = lang

    def run(self):
        try:
            import vt_api

            ok, message = vt_api.test_key(self.engine, self.key, self.lang)
        except Exception as exc:  # noqa: BLE001 - a dead test must never close the dialog
            log.exception("API key test failed")
            ok, message = False, str(exc)
        self.finished.emit(ok, message)


class SettingsDialog(QDialog):
    """Speech engine + API key preferences."""

    def __init__(self, lang="en", parent=None):
        super().__init__(parent)
        self.lang = lang or "en"
        from vt_i18n import configure_qt_language
        configure_qt_language(self.lang)
        self._tester = None
        self._engine_group = QButtonGroup(self)
        self._model_group = QButtonGroup(self)
        self._translate_group = QButtonGroup(self)
        self._engine_radios = {}
        self._model_radios = {}
        self._translate_radios = {}
        self._key_edits = {}
        self._key_buttons = {}
        self._cloud_models = {}
        self._cloud_model_labels = {}

        self._build()
        self._load()
        self.retranslate(self.lang)

    # ------------------------------------------------------------------ build
    def _build(self):
        self.setModal(True)
        self.setMinimumWidth(560)
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget(self)
        layout.addWidget(self.tabs)
        self.navigation_hint = QLabel(self.t("settings_tabs_hint"))
        self.navigation_hint.setWordWrap(True)
        layout.addWidget(self.navigation_hint)
        self._pages = []
        for key in ("general", "speech", "keys", "accessibility"):
            page = QWidget(self.tabs)
            page_layout = QVBoxLayout(page)
            scroll = QScrollArea(self)
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            scroll.setWidget(page)
            # Keep Tab on actionable controls, rather than an unnamed scroll
            # container that NVDA announces only as "grouping".
            scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            page.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.tabs.addTab(scroll, self.t("settings_tab_" + key))
            self._pages.append(page_layout)
        general, speech, keys_page, accessibility = self._pages
        self.interface_choice = QComboBox(self)
        self.interface_choice.addItem(self.t("iface_en"), "en")
        self.interface_choice.addItem("العربية", "ar")
        self.interface_choice.setCurrentIndex(1 if self.lang == "ar" else 0)
        general_form = QFormLayout()
        self.interface_label = QLabel(self.t("lbl_interface_lang"))
        self.interface_label.setBuddy(self.interface_choice)
        general_form.addRow(self.interface_label, self.interface_choice)
        general.addLayout(general_form)
        self.timestamps_choice = QCheckBox(self.t("act_timestamps").replace("&", ""))
        self.timestamps_choice.setChecked(vt_prefs.load().get("show_timestamps", "true") != "false")
        general.addWidget(self.timestamps_choice)
        import update_checker
        self.auto_update_choice = QCheckBox(self.t("act_auto_update").replace("&", ""))
        self.auto_update_choice.setChecked(bool(update_checker.load_settings().get("auto_check", True)))
        general.addWidget(self.auto_update_choice)
        self.recovery_choice = QCheckBox(self.t("lbl_recover_session"))
        self.recovery_choice.setChecked(vt_prefs.load().get("recover_session", "true") != "false")
        general.addWidget(self.recovery_choice)
        self.text_size_choice = QComboBox(self)
        for size in (100, 125, 150, 175, 200):
            self.text_size_choice.addItem(str(size) + "%", str(size))
        self.text_size_choice.setCurrentIndex(max(0, self.text_size_choice.findData(vt_prefs.load().get("text_size", "100"))))
        self.text_size_label = QLabel(self.t("lbl_text_size"))
        self.text_size_label.setBuddy(self.text_size_choice)
        general_form.addRow(self.text_size_label, self.text_size_choice)
        self.text_size_choice.setAccessibleName(self.t("lbl_text_size"))
        self.text_size_choice.setAccessibleDescription(self.t("desc_text_size"))
        general.addStretch()
        import vt_a11y
        temporary, self.accessibility_checks = vt_a11y.build_dialog(lang=self.lang)
        for box in self.accessibility_checks.values():
            accessibility.addWidget(box)
        temporary.deleteLater()
        accessibility.addStretch()

        # ---------------------------------------------- transcription engine
        self.engine_box = QGroupBox(self)
        self.engine_layout = QVBoxLayout(self.engine_box)
        for key in ENGINE_KEYS:
            radio = QRadioButton(self.engine_box)
            radio.setProperty("engine_key", key)
            radio.toggled.connect(self._on_engine_changed)
            self._engine_group.addButton(radio)
            self._engine_radios[key] = radio
            self.engine_layout.addWidget(radio)
        speech.addWidget(self.engine_box)

        # ------------------------------------------------- local model choice
        self.model_box = QGroupBox(self)
        self.model_layout = QVBoxLayout(self.model_box)
        for key in vt_prefs.WHISPER_MODELS:
            radio = QRadioButton(self.model_box)
            radio.setProperty("model_key", key)
            self._model_group.addButton(radio)
            self._model_radios[key] = radio
            self.model_layout.addWidget(radio)
        speech.addWidget(self.model_box)

        # ---------------------------------------------------------- API keys
        # One provider at a time: pick the provider and its key row (with the
        # Show key, Test key and Get API key buttons) appears.  Choosing a
        # cloud engine above switches this selector automatically.
        self.keys_box = QGroupBox(self)
        keys_root = QVBoxLayout(self.keys_box)
        provider_row = QHBoxLayout()
        self.provider_label = QLabel(self.keys_box)
        self._provider_combo = QComboBox(self.keys_box)
        for engine in ("openai", "groq", "gemini"):
            self._provider_combo.addItem(engine, engine)
        self._provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        provider_row.addWidget(self.provider_label)
        provider_row.addWidget(self._provider_combo, 1)
        keys_root.addLayout(provider_row)

        self.keys_form = QFormLayout()
        self.keys_form.setContentsMargins(0, 0, 0, 0)
        keys_root.addLayout(self.keys_form)
        self._get_buttons = {}
        self._key_holders = {}
        for engine in ("openai", "groq", "gemini"):
            holder = QWidget(self.keys_box)
            holder_layout = QVBoxLayout(holder)
            row = QHBoxLayout()
            holder_layout.addLayout(row)
            row.setContentsMargins(0, 0, 0, 0)
            edit = QLineEdit(holder)
            edit.setEchoMode(QLineEdit.EchoMode.Password)
            edit.setClearButtonEnabled(True)
            show = QPushButton(holder)
            show.setCheckable(True)
            show.toggled.connect(lambda checked, e=edit, b=show: self._toggle_key(e, b, checked))
            test = QPushButton(holder)
            test.clicked.connect(lambda _checked=False, e=engine: self._on_test_key(e))
            get = QPushButton(holder)
            get.clicked.connect(lambda _checked=False, e=engine: self._on_get_key(e))
            row.addWidget(edit, 1)
            row.addWidget(show)
            row.addWidget(test)
            row.addWidget(get)
            model_row = QFormLayout()
            model_label = QLabel(self.t("lbl_cloud_model"), holder)
            model_combo = QComboBox(holder)
            model_combo.setEditable(True)
            choices = {
                "openai": ("whisper-1",),
                "groq": ("whisper-large-v3", "whisper-large-v3-turbo"),
                "gemini": ("gemini-2.5-flash",),
            }[engine]
            model_combo.addItems(choices)
            model_label.setBuddy(model_combo)
            model_row.addRow(model_label, model_combo)
            holder_layout.addLayout(model_row)
            self._cloud_models[engine] = model_combo
            self._cloud_model_labels[engine] = model_label
            self.keys_form.addRow("", holder)
            self._key_edits[engine] = edit
            self._key_buttons[engine] = (show, test)
            self._get_buttons[engine] = get
            self._key_holders[engine] = holder
        keys_page.addWidget(self.keys_box)
        keys_page.addStretch()

        # -------------------------------------------------- translation engine
        self.translate_box = QGroupBox(self)
        self.translate_layout = QVBoxLayout(self.translate_box)
        for key in ENGINE_KEYS:
            radio = QRadioButton(self.translate_box)
            radio.setProperty("translate_key", key)
            radio.toggled.connect(self._on_translate_changed)
            self._translate_group.addButton(radio)
            self._translate_radios[key] = radio
            self.translate_layout.addWidget(radio)
        speech.addWidget(self.translate_box)
        speech.addStretch()

        # -------------------------------------------------------------- footer
        self.note = QLabel(self)
        self.note.setWordWrap(True)
        self.note.setTextFormat(Qt.TextFormat.PlainText)
        keys_page.addWidget(self.note)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.save_button = QPushButton(self)
        self.save_button.clicked.connect(self._on_save)
        self.cancel_button = QPushButton(self)
        self.cancel_button.clicked.connect(self.reject)
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.cancel_button)
        layout.addLayout(buttons)

        previous = None
        tab_order = (
            [self._engine_radios[key] for key in ENGINE_KEYS]
            + [self._model_radios[key] for key in vt_prefs.WHISPER_MODELS]
            + [self._provider_combo]
            + [self._key_edits[key] for key in ("openai", "groq", "gemini")]
            + [self._key_buttons[key][0] for key in ("openai", "groq", "gemini")]
            + [self._key_buttons[key][1] for key in ("openai", "groq", "gemini")]
            + [self._get_buttons[key] for key in ("openai", "groq", "gemini")]
            + list(self._cloud_models.values())
            + [self._translate_radios[key] for key in ENGINE_KEYS]
            + [self.save_button, self.cancel_button]
        )
        for widget in tab_order:
            if previous is not None:
                self.setTabOrder(previous, widget)
            previous = widget

    # -------------------------------------------------------------- load/save
    def _load(self):
        data = vt_prefs.normalized(vt_prefs.load())
        self._engine_radios[data["transcribe_engine"]].setChecked(True)
        self._model_radios[data["whisper_model"]].setChecked(True)
        self._translate_radios[data["translate_engine"]].setChecked(True)
        for engine in ("openai", "groq", "gemini"):
            self._key_edits[engine].setText(data[engine + "_api_key"])
            self._cloud_models[engine].setCurrentText(data[engine + "_model"])
        # Start on the provider the user actually works with: the chosen
        # cloud engine, else the first provider that already has a key.
        provider = next(
            (key for key in (data["transcribe_engine"], data["translate_engine"])
             if key != "local"),
            None,
        )
        if provider is None:
            provider = next(
                (key for key in ("openai", "groq", "gemini")
                 if data.get(key + "_api_key")),
                "openai",
            )
        self._select_provider(provider)
        self._on_engine_changed()

    def collect(self) -> dict:
        engine = next(
            (key for key, radio in self._engine_radios.items() if radio.isChecked()),
            "local",
        )
        model = next(
            (key for key, radio in self._model_radios.items() if radio.isChecked()),
            "base",
        )
        translate = next(
            (key for key, radio in self._translate_radios.items() if radio.isChecked()),
            "local",
        )
        data = {
            "transcribe_engine": engine,
            "whisper_model": model,
            "translate_engine": translate,
            "show_timestamps": "true" if self.timestamps_choice.isChecked() else "false",
            "text_size": self.text_size_choice.currentData(),
            "recover_session": "true" if self.recovery_choice.isChecked() else "false",
        }
        for name, edit in self._key_edits.items():
            data[name + "_api_key"] = edit.text().strip()
            data[name + "_model"] = self._cloud_models[name].currentText().strip() or vt_prefs.DEFAULTS[name + "_model"]
        return data

    # --------------------------------------------------------------- callbacks
    def _toggle_key(self, edit, button, checked):
        button.setText(self.t("btn_show_key") if not checked else self.t("btn_hide_key"))
        edit.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )

    def _on_engine_changed(self, *_args):
        engine = next(
            (key for key, radio in self._engine_radios.items() if radio.isChecked()),
            "local",
        )
        self.model_box.setEnabled(engine == "local")
        # Picking a cloud engine brings its key row forward, with the Show key,
        # Test key and Get API key buttons for that provider.
        if engine != "local":
            self._select_provider(engine)

    def _on_translate_changed(self, *_args):
        engine = next(
            (key for key, radio in self._translate_radios.items() if radio.isChecked()),
            "local",
        )
        if engine != "local":
            self._select_provider(engine)

    def _on_provider_changed(self, index):
        engine = self._provider_combo.itemData(index)
        self._show_provider(engine if engine in self._key_holders else "openai")

    def _select_provider(self, engine):
        if engine not in self._key_holders:
            return
        for index in range(self._provider_combo.count()):
            if self._provider_combo.itemData(index) == engine:
                if self._provider_combo.currentIndex() != index:
                    self._provider_combo.setCurrentIndex(index)
                else:
                    self._show_provider(engine)
                return

    def _show_provider(self, engine):
        for name, holder in self._key_holders.items():
            holder.setVisible(name == engine)
        edit = self._key_edits.get(engine)
        if edit is not None:
            edit.setEnabled(True)

    def _on_test_key(self, engine):
        key = self._key_edits[engine].text().strip()
        if not key:
            QMessageBox.warning(
                self,
                self.t("title_settings_error"),
                self.t("err_api_key_missing", engine=self._label(engine)),
            )
            return
        if self._tester is not None and self._tester.isRunning():
            return
        show, test = self._key_buttons[engine]
        test.setEnabled(False)
        self.note.setText(self.t("msg_key_testing", engine=self._label(engine)))
        self._tester = KeyTestThread(engine, key, self.lang, self)
        self._tester.finished.connect(
            lambda ok, msg, t=test: self._on_test_done(ok, msg, t)
        )
        self._tester.start()

    def _on_test_done(self, ok, message, button):
        button.setEnabled(True)
        self.note.setText(message)
        self.note.setAccessibleDescription(message)
        import vt_a11y
        vt_a11y.apply_descriptions(self.note)
        # The result dialog is the single announcement of this result.
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Information if ok else QMessageBox.Icon.Warning)
        box.setWindowTitle(self.t("title_settings_error") if not ok else self.t("dlg_settings_title"))
        box.setText(message)
        box.exec()

    def _on_get_key(self, engine):
        """Open the provider page where a new API key can be created."""
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        url = KEY_URLS.get(engine)
        message = self.t("msg_key_opened", engine=self._label(engine))
        opened = False
        if url:
            try:
                opened = bool(QDesktopServices.openUrl(QUrl(url)))
            except Exception:  # noqa: BLE001 - reported below
                log.exception("the key page could not be opened")
        if not opened:
            QMessageBox.warning(
                self, self.t("btn_get_key"), url or self.t("msg_key_opened", engine=self._label(engine))
            )
            return
        parent = self.parent()
        if parent is not None and hasattr(parent, "announce"):
            try:
                parent.announce(message)
            except Exception:  # noqa: BLE001 - announcing is best effort
                pass
        else:
            QMessageBox.information(self, self.t("btn_get_key"), message)
        self.note.setText(message)

    def _on_save(self):
        data = self.collect()
        problems = vt_prefs.validate(data, self.lang)
        if problems:
            lines = "\n".join("- " + message for _field, message in problems)
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Warning)
            box.setWindowTitle(self.t("title_settings_error"))
            box.setText(lines)
            use_local = box.addButton(self.t("btn_use_local"), QMessageBox.ButtonRole.AcceptRole)
            keep = box.addButton(self.t("btn_keep_editing"), QMessageBox.ButtonRole.RejectRole)
            box.setDefaultButton(keep)
            box.exec()
            if box.clickedButton() is use_local:
                data["transcribe_engine"] = "local"
                data["translate_engine"] = "local"
                problems = []
            else:
                return
        if not vt_prefs.save(data):
            QMessageBox.warning(
                self,
                self.t("title_settings_error"),
                self.t("err_prefs_save"),
            )
            return
        import update_checker
        update_checker.set_auto_check(self.auto_update_choice.isChecked())
        import vt_setup
        vt_setup.save_setup(self.interface_choice.currentData())
        self.saved_data = data
        import vt_a11y
        vt_a11y.save({key: box.isChecked() for key, box in self.accessibility_checks.items()})
        if self.parent() is not None:
            parent = self.parent()
            parent.interface_combo.setCurrentIndex(self.interface_choice.currentIndex())
            parent.timestamps_check.setChecked(self.timestamps_choice.isChecked())
            vt_a11y.apply(parent)
            if hasattr(parent, "update_recovery_preference"):
                parent.update_recovery_preference()
        self.accept()

    # ---------------------------------------------------------------- helpers
    def _label(self, engine):
        return {
            "local": self.t("lbl_engine_local"),
            "openai": "OpenAI",
            "groq": "Groq",
            "gemini": "Google Gemini",
        }.get(engine, engine)

    def t(self, key, **kwargs):
        text = tr(self.lang, key, **kwargs)
        if text == key:
            from vid_trans_app import tr as app_tr
            return app_tr(self.lang, key, **kwargs)
        return text

    def retranslate(self, lang):
        self.lang = lang or self.lang
        self.setWindowTitle(self.t("dlg_settings_title"))
        self.setAccessibleName(self.t("dlg_settings_title"))
        self.setAccessibleDescription(self.t("dlg_settings_d"))
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if self.lang == "ar" else Qt.LayoutDirection.LeftToRight)
        for index, key in enumerate(("general", "speech", "keys", "accessibility")):
            self.tabs.setTabText(index, self.t("settings_tab_" + key))
        self.tabs.setAccessibleName(self.t("dlg_settings_title"))
        self.tabs.setAccessibleDescription(self.t("settings_tabs_hint"))
        self.navigation_hint.setText(self.t("settings_tabs_hint"))
        for index in range(self.tabs.count()):
            title = self.tabs.tabText(index)
            self.tabs.widget(index).setAccessibleName(title)
            self.tabs.widget(index).widget().setAccessibleName(title)
        self.auto_update_choice.setText(self.t("act_auto_update").replace("&", ""))
        self.auto_update_choice.setAccessibleName(self.auto_update_choice.text())

        self.engine_box.setTitle(self.t("grp_engine"))
        self.engine_box.setAccessibleDescription(self.t("grp_engine_d"))
        for key, radio in self._engine_radios.items():
            radio.setText(self.t("lbl_engine_" + key))
            radio.setAccessibleName(self.t("acc_engine_%s_n" % key))
            radio.setAccessibleDescription(self.t("acc_engine_%s_d" % key))

        self.model_box.setTitle(self.t("lbl_model_group"))
        self.model_box.setAccessibleDescription(self.t("lbl_model_group_d"))
        for key, radio in self._model_radios.items():
            radio.setText(self.t("model_" + key))
            radio.setAccessibleName(self.t("lbl_model_group") + ": " + self.t("model_" + key))
            radio.setAccessibleDescription(self.t("acc_model_group_d"))

        self.keys_box.setTitle(self.t("lbl_api_keys"))
        self.keys_box.setAccessibleDescription(self.t("lbl_api_keys_d"))
        self.provider_label.setText(self.t("lbl_key_provider"))
        self.provider_label.setBuddy(self._provider_combo)
        self._provider_combo.setAccessibleName(self.t("acc_key_provider_n"))
        self._provider_combo.setAccessibleDescription(self.t("acc_key_provider_d"))
        for index in range(self._provider_combo.count()):
            engine = self._provider_combo.itemData(index)
            self._provider_combo.setItemText(index, self._label(engine))
        for engine, edit in self._key_edits.items():
            self._cloud_model_labels[engine].setText(self.t("lbl_cloud_model"))
            self._cloud_models[engine].setAccessibleName(self.t("lbl_cloud_model") + " - " + self._label(engine))
            self._cloud_models[engine].setAccessibleDescription(self.t("cloud_model_hint"))
            edit.setAccessibleName(self.t("lbl_key_" + engine))
            edit.setAccessibleDescription(
                self.t("acc_key_d", engine=self._label(engine))
            )
            edit.setPlaceholderText(self.t("ph_key"))
            show, test = self._key_buttons[engine]
            show.setText(self.t("btn_show_key"))
            show.setAccessibleName(self.t("btn_show_key") + " - " + self._label(engine))
            test.setText(self.t("btn_test_key"))
            test.setAccessibleName(self.t("acc_test_key_n"))
            test.setAccessibleDescription(self.t("acc_test_key_d", engine=self._label(engine)))
            get = self._get_buttons[engine]
            get.setText(self.t("btn_get_key"))
            get.setAccessibleName(self.t("acc_get_key_n") + " - " + self._label(engine))
            get.setAccessibleDescription(
                self.t("acc_get_key_d", engine=self._label(engine))
            )
            get.setToolTip(self.t("acc_get_key_d", engine=self._label(engine)))

        self.translate_box.setTitle(self.t("grp_translate"))
        self.translate_box.setAccessibleDescription(self.t("grp_translate_d"))
        for key, radio in self._translate_radios.items():
            label_key = "lbl_translation_free" if key == "local" else "lbl_engine_" + key
            radio.setText(self.t(label_key))
            radio.setAccessibleName(self.t(label_key))
            radio.setAccessibleDescription(self.t("grp_translate_d"))

        self.note.setText(self.t("lbl_api_keys_d"))
        self.save_button.setText(self.t("btn_save"))
        self.save_button.setAccessibleName(self.t("acc_save_n"))
        self.save_button.setAccessibleDescription(self.t("acc_save_d"))
        self.cancel_button.setText(self.t("btn_cancel_dialog"))
        self._on_engine_changed()
        import vt_a11y
        vt_a11y.apply_descriptions(self)


def open_settings(lang="en", parent=None) -> dict | None:
    """Show the dialog and return the saved preferences (or ``None``)."""
    dialog = SettingsDialog(lang=lang, parent=parent)
    if dialog.exec():
        return getattr(dialog, "saved_data", None)
    return None
