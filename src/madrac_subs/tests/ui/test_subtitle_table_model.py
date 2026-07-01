"""Tests for SubtitleTableModel — requires Qt (offscreen)."""

import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import Qt, QModelIndex

from madrac.utils.editor_model import SubtitleEntry, SubtitleDocument
from madrac.ui.models.subtitle_table_model import SubtitleTableModel, _ms_to_str, _parse_ms


def _make_doc():
    entries = [
        SubtitleEntry(1, 1000, 3000, "Hola"),
        SubtitleEntry(2, 4000, 6000, "Mundo"),
        SubtitleEntry(3, 7000, 9000, "Tercero"),
    ]
    return SubtitleDocument(entries=entries)


class TestSubtitleTableModel:
    def test_row_count(self):
        model = SubtitleTableModel(_make_doc())
        assert model.rowCount() == 3

    def test_row_count_empty(self):
        model = SubtitleTableModel(SubtitleDocument())
        assert model.rowCount() == 0

    def test_column_count(self):
        model = SubtitleTableModel(_make_doc())
        assert model.columnCount() == 5

    def test_header_data(self):
        model = SubtitleTableModel(_make_doc())
        assert model.headerData(0, Qt.Horizontal, Qt.DisplayRole) == "#"
        assert model.headerData(4, Qt.Horizontal, Qt.DisplayRole) == "Texto"

    def test_data_index_column(self):
        model = SubtitleTableModel(_make_doc())
        idx = model.index(0, 0)
        assert model.data(idx, Qt.DisplayRole) == "1"

    def test_data_text_column(self):
        model = SubtitleTableModel(_make_doc())
        idx = model.index(0, 4)
        assert model.data(idx, Qt.DisplayRole) == "Hola"

    def test_data_start_time(self):
        model = SubtitleTableModel(_make_doc())
        idx = model.index(0, 1)
        val = model.data(idx, Qt.DisplayRole)
        assert "00:00:01,000" in val

    def test_data_end_time(self):
        model = SubtitleTableModel(_make_doc())
        idx = model.index(0, 2)
        val = model.data(idx, Qt.DisplayRole)
        assert "00:00:03,000" in val

    def test_data_duration(self):
        model = SubtitleTableModel(_make_doc())
        idx = model.index(0, 3)
        val = model.data(idx, Qt.DisplayRole)
        assert "2.0s" in val

    def test_edit_text(self, qtbot):
        model = SubtitleTableModel(_make_doc())
        idx = model.index(0, 4)
        assert model.setData(idx, "Editado", Qt.EditRole)
        assert model.data(idx, Qt.DisplayRole) == "Editado"
        assert model.doc.modified

    def test_edit_start_time_valid(self, qtbot):
        model = SubtitleTableModel(_make_doc())
        idx = model.index(0, 1)
        assert model.setData(idx, "00:00:00,500", Qt.EditRole)
        assert model.doc.entries[0].start_ms == 500

    def test_edit_start_time_invalid_after_end(self, qtbot):
        model = SubtitleTableModel(_make_doc())
        idx = model.index(0, 1)
        assert not model.setData(idx, "00:00:05,000", Qt.EditRole)

    def test_edit_end_time_valid(self, qtbot):
        model = SubtitleTableModel(_make_doc())
        idx = model.index(0, 2)
        assert model.setData(idx, "00:00:03,500", Qt.EditRole)
        assert model.doc.entries[0].end_ms == 3500

    def test_edit_end_time_invalid_before_start(self, qtbot):
        model = SubtitleTableModel(_make_doc())
        idx = model.index(0, 2)
        assert not model.setData(idx, "00:00:00,500", Qt.EditRole)

    def test_readonly_columns_not_editable(self):
        model = SubtitleTableModel(_make_doc())
        assert not model.flags(model.index(0, 0)) & Qt.ItemIsEditable
        assert not model.flags(model.index(0, 3)) & Qt.ItemIsEditable

    def test_editable_columns(self):
        model = SubtitleTableModel(_make_doc())
        assert model.flags(model.index(0, 1)) & Qt.ItemIsEditable
        assert model.flags(model.index(0, 2)) & Qt.ItemIsEditable
        assert model.flags(model.index(0, 4)) & Qt.ItemIsEditable

    def test_user_role_returns_index(self):
        model = SubtitleTableModel(_make_doc())
        idx = model.index(1, 0)
        assert model.data(idx, Qt.UserRole) == 2

    def test_invalid_index_returns_none(self):
        model = SubtitleTableModel(_make_doc())
        assert model.data(QModelIndex()) is None


class TestTimestampHelpers:
    def test_ms_to_str(self):
        assert _ms_to_str(1000) == "00:00:01,000"
        assert _ms_to_str(3661000) == "01:01:01,000"

    def test_parse_ms(self):
        assert _parse_ms("00:00:01,000") == 1000
        assert _parse_ms("00:01:30,500") == 90500

    def test_parse_ms_invalid(self):
        assert _parse_ms("not a time") == -1
