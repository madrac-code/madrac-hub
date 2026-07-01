"""Tests for editor_operations.py — pure editing functions."""

import pytest

from madrac.utils.editor_model import SubtitleEntry, SubtitleDocument
from madrac.utils.editor_operations import (
    shift_times,
    change_fps,
    merge_entries,
    split_entry,
    remove_entry,
    insert_entry,
    renumber,
    find_text,
    replace_text,
    trim_trailing_spaces,
    adjust_duration,
)


def _make_doc():
    entries = [
        SubtitleEntry(1, 1000, 3000, "Hola mundo"),
        SubtitleEntry(2, 4000, 6000, "Segunda linea"),
        SubtitleEntry(3, 7000, 9000, "Tercer elemento"),
    ]
    return SubtitleDocument(entries=entries)


class TestShiftTimes:
    def test_positive(self):
        doc = _make_doc()
        shift_times(doc, 500)
        assert doc.entries[0].start_ms == 1500

    def test_negative(self):
        doc = _make_doc()
        shift_times(doc, -500)
        assert doc.entries[0].start_ms == 500

    def test_clamp_zero(self):
        doc = _make_doc()
        shift_times(doc, -99999)
        assert doc.entries[0].start_ms == 0

    def test_sets_modified(self):
        doc = _make_doc()
        doc.modified = False
        shift_times(doc, 100)
        assert doc.modified


class TestChangeFps:
    def test_doubles_times(self):
        doc = _make_doc()
        change_fps(doc, 30, 60)
        assert doc.entries[0].start_ms == 2000
        assert doc.entries[0].end_ms == 6000

    def test_halves_times(self):
        doc = _make_doc()
        change_fps(doc, 60, 30)
        assert doc.entries[0].start_ms == 500

    def test_sets_modified(self):
        doc = _make_doc()
        doc.modified = False
        change_fps(doc, 30, 60)
        assert doc.modified

    def test_noop_same_fps(self):
        doc = _make_doc()
        change_fps(doc, 25, 25)
        assert doc.entries[0].start_ms == 1000


class TestMergeEntries:
    def test_merges_two_entries(self):
        doc = _make_doc()
        ok = merge_entries(doc, 1, 2)
        assert ok
        assert doc.count() == 2
        assert doc.entries[0].text == "Hola mundo\nSegunda linea"
        assert doc.entries[0].end_ms == 6000

    def test_renumbers_after_merge(self):
        doc = _make_doc()
        merge_entries(doc, 1, 2)
        assert [e.index for e in doc.entries] == [1, 2]

    def test_invalid_first(self):
        doc = _make_doc()
        assert not merge_entries(doc, 99, 2)

    def test_invalid_second(self):
        doc = _make_doc()
        assert not merge_entries(doc, 1, 99)

    def test_sets_modified(self):
        doc = _make_doc()
        doc.modified = False
        merge_entries(doc, 1, 2)
        assert doc.modified


class TestSplitEntry:
    def test_splits_at_midpoint(self):
        doc = _make_doc()  # entry 1: 1000-3000
        ok = split_entry(doc, 1, 2000)
        assert ok
        assert doc.count() == 4
        assert doc.entries[0].start_ms == 1000
        assert doc.entries[0].end_ms < 2000
        assert doc.entries[1].start_ms > 2000

    def test_fails_before_start(self):
        doc = _make_doc()
        assert not split_entry(doc, 1, 500)

    def test_fails_after_end(self):
        doc = _make_doc()
        assert not split_entry(doc, 1, 5000)

    def test_fails_invalid_index(self):
        doc = _make_doc()
        assert not split_entry(doc, 99, 2000)

    def test_renumbers_after_split(self):
        doc = _make_doc()
        split_entry(doc, 1, 2000)
        assert [e.index for e in doc.entries] == [1, 2, 3, 4]

    def test_sets_modified(self):
        doc = _make_doc()
        doc.modified = False
        split_entry(doc, 1, 2000)
        assert doc.modified


class TestRemoveEntry:
    def test_removes_by_index(self):
        doc = _make_doc()
        ok = remove_entry(doc, 2)
        assert ok
        assert doc.count() == 2
        assert all(e.text != "Segunda linea" for e in doc.entries)

    def test_renumbers_after_remove(self):
        doc = _make_doc()
        remove_entry(doc, 1)
        assert [e.index for e in doc.entries] == [1, 2]

    def test_invalid_index(self):
        doc = _make_doc()
        assert not remove_entry(doc, 99)

    def test_sets_modified(self):
        doc = _make_doc()
        doc.modified = False
        remove_entry(doc, 1)
        assert doc.modified


class TestInsertEntry:
    def test_inserts_new_entry(self):
        doc = _make_doc()
        new = SubtitleEntry(0, 2500, 3500, "Insertado")
        insert_entry(doc, new)
        assert doc.count() == 4
        assert any(e.text == "Insertado" for e in doc.entries)

    def test_renumbers_after_insert(self):
        doc = _make_doc()
        insert_entry(doc, SubtitleEntry(0, 2500, 3500, "Nuevo"))
        assert [e.index for e in doc.entries] == [1, 2, 3, 4]

    def test_sorts_by_time(self):
        doc = _make_doc()
        insert_entry(doc, SubtitleEntry(0, 500, 800, "Temprano"))
        assert doc.entries[0].start_ms == 500


class TestRenumber:
    def test_renumbers_all(self):
        doc = _make_doc()
        doc.entries[0].index = 99
        doc.entries[2].index = 42
        renumber(doc)
        assert [e.index for e in doc.entries] == [1, 2, 3]


class TestFindText:
    def test_finds_existing_text(self):
        doc = _make_doc()
        results = find_text(doc, "Mundo")
        assert len(results) == 1
        assert results[0][0] == 1

    def test_not_found(self):
        doc = _make_doc()
        results = find_text(doc, "xyz")
        assert results == []

    def test_case_insensitive_by_default(self):
        doc = _make_doc()
        results = find_text(doc, "mundo")
        assert len(results) == 1

    def test_case_sensitive(self):
        doc = _make_doc()
        results = find_text(doc, "mundo", case_sensitive=True)
        assert len(results) == 1
        results = find_text(doc, "MUNDO", case_sensitive=True)
        assert results == []

    def test_finds_multiple(self):
        doc = _make_doc()
        doc.entries[1].text = "Hola otra vez"
        results = find_text(doc, "Hola")
        assert len(results) == 2


class TestReplaceText:
    def test_replaces_all_occurrences(self):
        doc = _make_doc()
        doc.entries[0].text = "Hola hola hola"
        count = replace_text(doc, "hola", "adios", case_sensitive=False)
        assert count == 1
        assert "adios adios adios" in doc.entries[0].text

    def test_case_sensitive(self):
        doc = _make_doc()
        count = replace_text(doc, "mundo", "world")
        assert count == 1
        assert doc.entries[0].text == "Hola world"

    def test_no_match(self):
        doc = _make_doc()
        count = replace_text(doc, "xyz", "abc")
        assert count == 0

    def test_sets_modified_on_match(self):
        doc = _make_doc()
        doc.modified = False
        replace_text(doc, "Mundo", "World")
        assert doc.modified

    def test_does_not_set_modified_on_no_match(self):
        doc = _make_doc()
        doc.modified = False
        replace_text(doc, "xyz", "abc")
        assert not doc.modified


class TestTrimTrailingSpaces:
    def test_trims_lines(self):
        doc = _make_doc()
        doc.entries[0].text = "Hola   \nMundo  "
        count = trim_trailing_spaces(doc)
        assert count == 1
        assert doc.entries[0].text == "Hola\nMundo"

    def test_no_change(self):
        doc = _make_doc()
        count = trim_trailing_spaces(doc)
        assert count == 0

    def test_sets_modified(self):
        doc = _make_doc()
        doc.entries[0].text = "foo  "
        doc.modified = False
        trim_trailing_spaces(doc)
        assert doc.modified


class TestAdjustDuration:
    def test_extends_short(self):
        doc = _make_doc()
        doc.entries[0].end_ms = doc.entries[0].start_ms + 500
        count = adjust_duration(doc, min_ms=1500, max_ms=7000)
        assert count == 1
        assert doc.entries[0].duration_ms() >= 1500

    def test_truncates_long(self):
        doc = _make_doc()
        doc.entries[0].end_ms = doc.entries[0].start_ms + 99999
        count = adjust_duration(doc, min_ms=1500, max_ms=7000)
        assert count == 1
        assert doc.entries[0].duration_ms() <= 7000

    def test_no_change(self):
        doc = _make_doc()
        count = adjust_duration(doc, min_ms=1000, max_ms=5000)
        assert count == 0
