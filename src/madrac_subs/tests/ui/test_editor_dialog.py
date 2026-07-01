"""Tests for EditorDialog — requires Qt (offscreen) + temp files."""

import os
import tempfile
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import Qt

from madrac.utils.editor_io import load_srt
from madrac.ui.dialogs.editor_dialog import EditorDialog
from madrac.ui.dialogs.search_dialog import SearchDialog

SRT_SAMPLE = """1
00:00:01,000 --> 00:00:03,000
Hola mundo

2
00:00:05,000 --> 00:00:07,000
Segunda linea
"""


class TestEditorDialog:
    def test_open_displays_entries(self, qtbot):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "test.srt"
            p.write_text(SRT_SAMPLE, encoding="utf-8")
            dlg = EditorDialog(str(p))
            qtbot.addWidget(dlg)
            assert dlg._model.rowCount() == 2
            assert dlg._doc.count() == 2

    def test_title_shows_filename(self, qtbot):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "test.srt"
            p.write_text(SRT_SAMPLE, encoding="utf-8")
            dlg = EditorDialog(str(p))
            qtbot.addWidget(dlg)
            assert "test.srt" in dlg.windowTitle()

    def test_title_shows_modified_flag(self, qtbot):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "test.srt"
            p.write_text(SRT_SAMPLE, encoding="utf-8")
            dlg = EditorDialog(str(p))
            qtbot.addWidget(dlg)
            assert "*" not in dlg.windowTitle()
            idx = dlg._model.index(0, 4)
            dlg._model.setData(idx, "Editado", Qt.EditRole)
            assert "*" in dlg.windowTitle()

    def test_save_preserves_content(self, qtbot):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "test.srt"
            p.write_text(SRT_SAMPLE, encoding="utf-8")
            dlg = EditorDialog(str(p))
            qtbot.addWidget(dlg)
            idx = dlg._model.index(0, 4)
            dlg._model.setData(idx, "Editado", Qt.EditRole)
            dlg._on_save()
            reloaded = load_srt(str(p))
            assert reloaded.entries[0].text == "Editado"

    def test_undo_restores_text(self, qtbot):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "test.srt"
            p.write_text(SRT_SAMPLE, encoding="utf-8")
            dlg = EditorDialog(str(p))
            qtbot.addWidget(dlg)
            idx = dlg._model.index(0, 4)
            dlg._model.setData(idx, "Cambiado", Qt.EditRole)
            dlg._on_undo()
            assert dlg._doc.entries[0].text == "Hola mundo"

    def test_redo_restores_change(self, qtbot):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "test.srt"
            p.write_text(SRT_SAMPLE, encoding="utf-8")
            dlg = EditorDialog(str(p))
            qtbot.addWidget(dlg)
            idx = dlg._model.index(0, 4)
            dlg._model.setData(idx, "Cambiado", Qt.EditRole)
            dlg._on_undo()
            dlg._on_redo()
            assert dlg._doc.entries[0].text == "Cambiado"

    def test_search_dialog_opens(self, qtbot):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "test.srt"
            p.write_text(SRT_SAMPLE, encoding="utf-8")
            dlg = EditorDialog(str(p))
            qtbot.addWidget(dlg)
            search_dlg = SearchDialog(dlg._doc, dlg)
            qtbot.addWidget(search_dlg)
            assert search_dlg.windowTitle() == "Buscar / Reemplazar"
