"""Tests for editor_io.py — load/save SRT, VTT, ASS."""

import tempfile
from pathlib import Path

import pytest

from madrac.utils.editor_model import SubtitleEntry, SubtitleDocument
from madrac.utils.editor_io import (
    load_srt,
    save_srt,
    load_vtt,
    save_vtt,
    load_ass,
    save_ass,
    detect_format,
    _parse_timestamp,
    _ts_srt,
    _ts_vtt,
    _ts_ass,
    _clean_text,
)


_SRT_SAMPLE = """1
00:00:01,000 --> 00:00:03,000
Hola mundo

2
00:00:05,000 --> 00:00:07,000
Segunda linea

3
00:00:10,000 --> 00:00:12,000
Tercer elemento
"""

_VTT_SAMPLE = """WEBVTT

00:00:01.000 --> 00:00:03.000
Hola mundo

00:00:05.000 --> 00:00:07.000
Segunda linea
"""

_ASS_SAMPLE = """[Script Info]
ScriptType: v4.00+

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:01.00,0:00:03.00,Default,,0,0,0,,Hola mundo
Dialogue: 0,0:00:05.00,0:00:07.00,Default,,0,0,0,,Segunda linea
"""


class TestTimestampHelpers:
    def test_parse_timestamp(self):
        assert _parse_timestamp("00:00:01,000") == 1000
        assert _parse_timestamp("00:01:30,500") == 90500

    def test_ts_srt(self):
        assert _ts_srt(1000) == "00:00:01,000"
        assert _ts_srt(90500) == "00:01:30,500"

    def test_ts_vtt(self):
        assert _ts_vtt(1000) == "00:00:01.000"

    def test_ts_ass(self):
        assert _ts_ass(1000) == "0:0:01.00"

    def test_clean_text_removes_html(self):
        assert _clean_text("Hello <b>world</b>") == "Hello world"

    def test_clean_text_removes_ass_tags(self):
        assert _clean_text(r"Hello {\b1}world{\b0}") == "Hello world"

    def test_clean_text_strips(self):
        assert _clean_text("  hello  ") == "hello"


class TestLoadSrt:
    def test_loads_three_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "test.srt"
            p.write_text(_SRT_SAMPLE, encoding="utf-8")
            doc = load_srt(str(p))
        assert doc.count() == 3
        assert doc.entries[0].text == "Hola mundo"
        assert doc.entries[0].start_ms == 1000
        assert doc.entries[1].start_ms == 5000

    def test_sets_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "test.srt"
            p.write_text(_SRT_SAMPLE, encoding="utf-8")
            doc = load_srt(str(p))
        assert doc.path is not None
        assert "test.srt" in str(doc.path)

    def test_not_modified(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "test.srt"
            p.write_text(_SRT_SAMPLE, encoding="utf-8")
            doc = load_srt(str(p))
        assert not doc.modified

    def test_bom_handling(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "test.srt"
            p.write_bytes(b"\xef\xbb\xbf" + _SRT_SAMPLE.encode("utf-8"))
            doc = load_srt(str(p))
        assert doc.count() == 3

    def test_empty_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "empty.srt"
            p.write_text("", encoding="utf-8")
            doc = load_srt(str(p))
        assert doc.count() == 0


class TestSaveSrt:
    def test_saves_and_reloads(self):
        doc = SubtitleDocument(
            entries=[
                SubtitleEntry(1, 1000, 3000, "Hola"),
                SubtitleEntry(2, 4000, 6000, "Mundo"),
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            out = str(Path(tmp) / "out.srt")
            save_srt(doc, out)
            reloaded = load_srt(out)
            assert reloaded.count() == 2
            assert reloaded.entries[0].text == "Hola"
            assert reloaded.entries[0].start_ms == 1000

    def test_clears_modified_flag(self):
        doc = SubtitleDocument(entries=[SubtitleEntry(1, 1000, 3000, "X")])
        doc.modified = True
        with tempfile.TemporaryDirectory() as tmp:
            save_srt(doc, str(Path(tmp) / "out.srt"))
        assert not doc.modified

    def test_uses_doc_path(self):
        doc = SubtitleDocument(
            entries=[SubtitleEntry(1, 1000, 3000, "X")],
        )
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "test.srt"
            doc.path = p
            save_srt(doc)
            assert p.exists()


class TestLoadVtt:
    def test_loads_two_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "test.vtt"
            p.write_text(_VTT_SAMPLE, encoding="utf-8")
            doc = load_vtt(str(p))
        assert doc.count() == 2
        assert doc.entries[0].text == "Hola mundo"

    def test_empty_vtt_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "empty.vtt"
            p.write_text("WEBVTT", encoding="utf-8")
            doc = load_vtt(str(p))
        assert doc.count() == 0


class TestSaveVtt:
    def test_saves_and_reloads(self):
        doc = SubtitleDocument(
            entries=[
                SubtitleEntry(1, 1000, 3000, "Hola"),
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            out = str(Path(tmp) / "out.vtt")
            save_vtt(doc, out)
            content = Path(out).read_text(encoding="utf-8")
        assert content.startswith("WEBVTT")
        assert "Hola" in content
        assert ".000" in content


class TestLoadAss:
    def test_loads_two_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "test.ass"
            p.write_text(_ASS_SAMPLE, encoding="utf-8")
            doc = load_ass(str(p))
        assert doc.count() == 2
        assert doc.entries[0].text == "Hola mundo"

    def test_empty_ass(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "empty.ass"
            p.write_text("[Script Info]\n", encoding="utf-8")
            doc = load_ass(str(p))
        assert doc.count() == 0


class TestSaveAss:
    def test_saves_and_reloads(self):
        doc = SubtitleDocument(
            entries=[SubtitleEntry(1, 1000, 3000, "Prueba")]
        )
        with tempfile.TemporaryDirectory() as tmp:
            out = str(Path(tmp) / "out.ass")
            save_ass(doc, out)
            reloaded = load_ass(out)
        assert reloaded.count() == 1
        assert reloaded.entries[0].text == "Prueba"


class TestDetectFormat:
    def test_srt(self):
        assert detect_format("file.srt") == "srt"

    def test_vtt(self):
        assert detect_format("file.vtt") == "vtt"

    def test_ass(self):
        assert detect_format("file.ass") == "ass"

    def test_ssa(self):
        assert detect_format("file.ssa") == "ass"

    def test_unknown(self):
        assert detect_format("file.txt") == "srt"
