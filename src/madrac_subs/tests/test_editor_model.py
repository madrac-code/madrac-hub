"""Tests for editor_model.py — SubtitleEntry, SubtitleDocument, HistoryStack."""

from pathlib import Path
from madrac.utils.editor_model import (
    SubtitleEntry,
    SubtitleDocument,
    HistoryStack,
)


def _make_doc(entries=None):
    if entries is None:
        entries = [
            SubtitleEntry(1, 1000, 3000, "Hola"),
            SubtitleEntry(2, 4000, 6000, "Mundo"),
            SubtitleEntry(3, 7000, 9000, "Foo bar"),
        ]
    return SubtitleDocument(entries=entries)


class TestSubtitleEntry:
    def test_duration_ms(self):
        e = SubtitleEntry(1, 1000, 3000, "test")
        assert e.duration_ms() == 2000

    def test_duration_zero(self):
        e = SubtitleEntry(1, 1000, 500, "bad")
        assert e.duration_ms() == 0

    def test_as_tuple(self):
        e = SubtitleEntry(1, 1000, 3000, "test")
        assert e.as_tuple() == (1, 1000, 3000, "test")

    def test_clone(self):
        e = SubtitleEntry(1, 1000, 3000, "test")
        c = e.clone()
        assert c is not e
        assert c.as_tuple() == e.as_tuple()


class TestSubtitleDocument:
    def test_count(self):
        doc = _make_doc()
        assert doc.count() == 3

    def test_duration_ms(self):
        doc = _make_doc()
        assert doc.duration_ms() == 8000

    def test_duration_empty(self):
        doc = SubtitleDocument()
        assert doc.duration_ms() == 0

    def test_get_found(self):
        doc = _make_doc()
        e = doc.get(2)
        assert e is not None
        assert e.text == "Mundo"

    def test_get_not_found(self):
        doc = _make_doc()
        assert doc.get(99) is None

    def test_sort(self):
        entries = [
            SubtitleEntry(3, 7000, 9000, "C"),
            SubtitleEntry(1, 1000, 3000, "A"),
            SubtitleEntry(2, 4000, 6000, "B"),
        ]
        doc = SubtitleDocument(entries=entries)
        doc.sort()
        assert [e.start_ms for e in doc.entries] == [1000, 4000, 7000]
        assert [e.text for e in doc.entries] == ["A", "B", "C"]

    def test_renumber(self):
        doc = _make_doc()
        doc.entries[0].index = 99
        doc.renumber()
        assert [e.index for e in doc.entries] == [1, 2, 3]

    def test_shift_positive(self):
        doc = _make_doc()
        doc.shift(500)
        assert doc.entries[0].start_ms == 1500
        assert doc.entries[0].end_ms == 3500

    def test_shift_negative(self):
        doc = _make_doc()
        doc.shift(-500)
        assert doc.entries[0].start_ms == 500
        assert doc.entries[0].end_ms == 2500

    def test_shift_clamps_zero(self):
        doc = _make_doc()
        doc.shift(-99999)
        assert doc.entries[0].start_ms == 0
        assert doc.entries[0].end_ms == 0

    def test_clone(self):
        doc = _make_doc()
        c = doc.clone()
        assert c is not doc
        assert c.count() == doc.count()
        assert c.entries[0] is not doc.entries[0]

    def test_validate_clean(self):
        doc = _make_doc()
        warnings = doc.validate()
        assert warnings == []

    def test_validate_negative_start(self):
        doc = _make_doc()
        doc.entries[0].start_ms = -100
        warnings = doc.validate()
        assert any("start_ms < 0" in w for w in warnings)

    def test_validate_end_before_start(self):
        doc = _make_doc()
        doc.entries[0].end_ms = 500
        warnings = doc.validate()
        assert any("end_ms" in w and "start_ms" in w for w in warnings)

    def test_validate_overlap(self):
        doc = _make_doc()
        doc.entries[0].end_ms = 4500
        warnings = doc.validate()
        assert any("Overlap" in w for w in warnings)

    def test_validate_empty_text(self):
        doc = _make_doc()
        doc.entries[0].text = "   "
        warnings = doc.validate()
        assert any("empty text" in w for w in warnings)

    def test_has_overlaps_true(self):
        doc = _make_doc()
        doc.entries[0].end_ms = 4500
        assert doc.has_overlaps()

    def test_has_overlaps_false(self):
        doc = _make_doc()
        assert not doc.has_overlaps()


class TestHistoryStack:
    def test_push_and_undo(self):
        doc = _make_doc()
        stack = HistoryStack()
        stack.push(doc)
        doc.entries[0].text = "Changed"
        restored = stack.undo(doc)
        assert restored is not None
        assert restored.entries[0].text == "Hola"

    def test_redo(self):
        doc = _make_doc()
        stack = HistoryStack()
        stack.push(doc)
        doc.entries[0].text = "Changed"
        stack.undo(doc)
        redone = stack.redo(doc)
        assert redone is not None
        assert redone.entries[0].text == "Changed"

    def test_undo_empty(self):
        stack = HistoryStack()
        assert stack.undo(_make_doc()) is None

    def test_redo_empty(self):
        stack = HistoryStack()
        assert stack.redo(_make_doc()) is None

    def test_push_clears_future(self):
        doc = _make_doc()
        stack = HistoryStack()
        stack.push(doc)
        stack.undo(doc)
        stack.push(doc)
        assert not stack.can_redo()

    def test_can_undo_redo(self):
        doc = _make_doc()
        stack = HistoryStack()
        assert not stack.can_undo()
        assert not stack.can_redo()
        stack.push(doc)
        assert stack.can_undo()
        stack.undo(doc)
        assert stack.can_redo()

    def test_clear(self):
        doc = _make_doc()
        stack = HistoryStack()
        stack.push(doc)
        stack.clear()
        assert not stack.can_undo()
        assert not stack.can_redo()

    def test_max_size(self):
        stack = HistoryStack(_max=3)
        for _ in range(5):
            stack.push(_make_doc())
        assert len(stack._past) == 3
