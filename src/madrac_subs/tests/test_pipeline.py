"""Tests for pipeline stages, queue, and worker modules."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from madrac.pipeline.stages.base import PipelineStage, StageResult
from madrac.pipeline.stages.format import FormatStage, Subtitulo, _to_srt, _to_vtt, _to_ass
from madrac.pipeline.queue import QueueManager, QueueEntry, ProcessingState


# ============================================================================
# StageResult
# ============================================================================

class TestStageResult:
    def test_success(self):
        r = StageResult(True, {"key": "val"})
        assert r.success is True
        assert r.data["key"] == "val"
        assert r.error is None

    def test_failure(self):
        r = StageResult(False, error="oops")
        assert r.success is False
        assert r.error == "oops"

    def test_defaults(self):
        r = StageResult(True)
        assert r.data == {}
        assert r.error is None


# ============================================================================
# PipelineStage base
# ============================================================================

class TestPipelineStage:
    def test_execute_raises(self):
        s = PipelineStage()
        s.name = "test"
        with pytest.raises(NotImplementedError):
            s.execute("id", {}, lambda *a: None, lambda *a: None, lambda: False)

    def test_rollback_does_nothing(self):
        s = PipelineStage()
        s.rollback({})  # should not raise


# ============================================================================
# Subtitle formatting helpers
# ============================================================================

class TestSubtitleFormatting:
    @pytest.fixture
    def subs(self):
        return [
            Subtitulo(1, 0.0, 1.5, "Hello world"),
            Subtitulo(2, 2.0, 4.5, "Second line"),
        ]

    def test_srt_format(self, subs):
        result = _to_srt(subs)
        assert "1\n00:00:00,000 --> 00:00:01,500\nHello world\n" in result
        assert "2\n00:00:02,000 --> 00:00:04,500\nSecond line\n" in result

    def test_vtt_format(self, subs):
        result = _to_vtt(subs)
        assert result.startswith("WEBVTT")
        assert "00:00:00.000 --> 00:00:01.500" in result

    def test_ass_format(self, subs):
        result = _to_ass(subs)
        assert "[Script Info]" in result
        assert "Dialogue: 0," in result
        assert "Hello world" in result

    def test_subtitulo_to_srt(self):
        s = Subtitulo(5, 61.5, 123.0, "Test")
        result = s.to_srt()
        assert "5\n" in result
        assert "00:01:01,500 --> 00:02:03,000" in result


# ============================================================================
# FormatStage
# ============================================================================

class TestFormatStage:
    @pytest.fixture
    def stage(self):
        return FormatStage()

    def test_no_segments(self, stage):
        result = stage.execute("id", {}, lambda *a: None, lambda *a: None, lambda: False)
        assert result.success is False
        assert "segments" in result.error.lower()

    @pytest.fixture
    def context(self, tmp_path):
        return {
            "segments": [
                {"start": 0.0, "end": 1.0, "text": "Hello"},
                {"start": 1.0, "end": 2.0, "text": "World"},
            ],
            "file_stem": "test_output",
        }

    @patch("madrac.pipeline.stages.format.get_config")
    def test_writes_srt(self, mock_get_config, stage, context, tmp_path):
        mock_get_config.side_effect = lambda key, default=None: {
            "salida.formato": "srt",
            "salida.directorio": str(tmp_path),
            "traduccion.idioma_destino": "es",
        }.get(key, default)

        result = stage.execute("id", context, lambda *a: None, lambda *a: None, lambda: False)
        assert result.success is True
        out = tmp_path / "test_output.srt"
        assert out.exists()
        assert "Hello" in out.read_text("utf-8")

    @patch("madrac.pipeline.stages.format.get_config")
    def test_writes_vtt(self, mock_get_config, stage, context, tmp_path):
        mock_get_config.side_effect = lambda key, default=None: {
            "salida.formato": "vtt",
            "salida.directorio": str(tmp_path),
            "traduccion.idioma_destino": "es",
        }.get(key, default)

        result = stage.execute("id", context, lambda *a: None, lambda *a: None, lambda: False)
        assert result.success is True
        out = tmp_path / "test_output.vtt"
        assert out.exists()
        assert "WEBVTT" in out.read_text("utf-8")

    def test_get_output_dir_with_config(self):
        with patch("madrac.pipeline.stages.format.get_config") as mc:
            mc.side_effect = lambda k, d=None: str(tempfile.gettempdir()) if k == "salida.directorio" else d
            result = FormatStage._get_output_dir({"ruta": __file__})
            assert result == tempfile.gettempdir()

    def test_get_output_dir_fallback_to_file_parent(self):
        with patch("madrac.pipeline.stages.format.get_config") as mc:
            mc.return_value = ""
            result = FormatStage._get_output_dir({"ruta": __file__})
            assert result == str(Path(__file__).parent)


# ============================================================================
# QueueManager
# ============================================================================

class TestQueueManager:
    @pytest.fixture
    def qm(self, tmp_path):
        path = tmp_path / "queue.json"
        return QueueManager(str(path))

    def test_add(self, qm):
        entry = qm.add("/path/to/video.mp4")
        assert entry.id
        assert entry.ruta == "/path/to/video.mp4"
        assert entry.state == ProcessingState.PENDING
        assert qm.count() == 1

    def test_add_emits_event(self, qm):
        events = []
        qm._bus.subscribe("queue.added", lambda data: events.append(data))
        qm.add("/test.mp4")
        assert len(events) == 1

    def test_remove(self, qm):
        e = qm.add("/a.mp4")
        assert qm.remove(e.id) is True
        assert qm.count() == 0

    def test_get(self, qm):
        e = qm.add("/b.mp4")
        assert qm.get(e.id) is not None
        assert qm.get("nonexistent") is None

    def test_set_state(self, qm):
        e = qm.add("/c.mp4")
        qm.set_state(e.id, ProcessingState.PROCESSING)
        assert qm.get(e.id).state == ProcessingState.PROCESSING
        qm.set_state(e.id, ProcessingState.COMPLETED)
        assert qm.get(e.id).state == ProcessingState.COMPLETED

    def test_next_pending_returns_none_if_active(self, qm):
        qm.add("/a.mp4")
        qm.add("/b.mp4")
        qm.set_state(qm.list_all()[0].id, ProcessingState.PROCESSING)
        nxt = qm.next_pending()
        # MAX_ACTIVE_PIPELINES=1: no new item while one is PROCESSING
        assert nxt is None

    def test_next_pending_returns_pending_if_none_active(self, qm):
        qm.add("/a.mp4")
        qm.add("/b.mp4")
        qm.set_state(qm.list_all()[0].id, ProcessingState.COMPLETED)
        nxt = qm.next_pending()
        assert nxt is not None
        assert nxt.ruta == "/b.mp4"

    def test_list_all_order(self, qm):
        a = qm.add("/a.mp4")
        b = qm.add("/b.mp4")
        items = qm.list_all()
        assert [i.id for i in items] == [a.id, b.id]

    def test_clear_completed(self, qm):
        a = qm.add("/a.mp4")
        b = qm.add("/b.mp4")
        qm.set_state(a.id, ProcessingState.COMPLETED)
        qm.set_state(b.id, ProcessingState.FAILED)
        assert qm.clear_completed() == 2
        assert qm.count() == 0

    def test_requeue_failed(self, qm):
        a = qm.add("/a.mp4")
        qm.set_state(a.id, ProcessingState.FAILED)
        assert qm.requeue_failed() == 1
        assert qm.get(a.id).state == ProcessingState.PENDING
        assert qm.get(a.id).error is None

    def test_cancel(self, qm):
        a = qm.add("/a.mp4")
        assert qm.cancel(a.id) is True
        assert qm.get(a.id).state == ProcessingState.CANCELLED

    def test_set_progress(self, qm):
        a = qm.add("/a.mp4")
        qm.set_progress(a.id, 50.0, "transcribe")
        assert qm.get(a.id).progress == 50.0
        assert qm.get(a.id).stage == "transcribe"

    def test_persist(self, tmp_path):
        path = tmp_path / "queue.json"
        qm1 = QueueManager(str(path))
        qm1.add("/persist.mp4")
        qm1.save()
        qm2 = QueueManager(str(path))
        assert qm2.count() == 1
        assert qm2.list_all()[0].ruta == "/persist.mp4"


# ============================================================================
# Worker
# ============================================================================

class TestPipelineWorker:
    @pytest.fixture
    def worker(self):
        from madrac.pipeline.worker import PipelineWorker
        return PipelineWorker()

    @pytest.fixture
    def qm(self, tmp_path):
        path = tmp_path / "queue.json"
        return QueueManager(str(path))

    def test_cancel(self, worker):
        worker.cancel()
        assert worker._should_cancel() is True

    def test_pause_resume(self, worker):
        worker.pause()
        assert worker._paused_event.is_set() is False
        worker.resume()
        assert worker._paused_event.is_set() is True

    def test_set_queue(self, worker, qm):
        worker.set_queue(qm)
        assert worker._queue_manager is qm

    def test_set_stages(self, worker):
        stages = [MagicMock(), MagicMock()]
        worker.set_stages(stages)
        assert worker._stages == stages

    def test_emit_log(self, worker):
        msgs = []
        worker._bus.subscribe("worker.log", lambda data: msgs.append(data))
        worker._emit_log("test message")
        assert any("test message" in m.get("message", "") for m in msgs)


# ============================================================================
# AudioExtractionStage
# ============================================================================

class TestAudioExtractionStage:
    @pytest.fixture
    def stage(self):
        from madrac.pipeline.stages import AudioExtractionStage
        return AudioExtractionStage()

    def test_no_path(self, stage):
        result = stage.execute("id", {}, lambda *a: None, lambda *a: None, lambda: False)
        assert result.success is False

    def test_file_not_found(self, stage):
        result = stage.execute("id", {"ruta": "/nonexistent/file.mp4"},
                               lambda *a: None, lambda *a: None, lambda: False)
        assert result.success is False

    @pytest.fixture
    def audio_file(self, tmp_path):
        f = tmp_path / "test.mp3"
        f.write_bytes(b"\xff\xfb" * 100)  # valid-ish mp3 header
        return str(f)

    def test_valid_audio_file(self, stage, audio_file):
        result = stage.execute("id", {"ruta": audio_file},
                               lambda *a: None, lambda *a: None, lambda: False)
        # Without ffmpeg, duration is 0 but file should be accepted
        assert result.success is True
        assert "audio_path" in result.data


# ============================================================================
# TranscribeStage
# ============================================================================

class TestTranscribeStage:
    @pytest.fixture
    def stage(self):
        from madrac.pipeline.stages import TranscribeStage
        return TranscribeStage()

    def test_no_audio_path(self, stage):
        result = stage.execute("id", {}, lambda *a: None, lambda *a: None, lambda: False)
        assert result.success is False

    def test_no_model_loaded(self, stage):
        result = stage.execute("id", {"audio_path": "/nonexistent.wav"},
                               lambda *a: None, lambda *a: None, lambda: False)
        assert result.success is False


# ============================================================================
# CommunityStage
# ============================================================================

class TestCommunityStage:
    @pytest.fixture
    def stage(self):
        from madrac.pipeline.stages import CommunityStage
        return CommunityStage()

    def test_disabled_by_default(self, stage):
        result = stage.execute("id", {}, lambda *a: None, lambda *a: None, lambda: False)
        assert result.success is True
        assert result.data.get("used_community") is False


# ============================================================================
# TranslateStage
# ============================================================================

class TestTranslateStage:
    @pytest.fixture
    def stage(self):
        from madrac.pipeline.stages import TranslateStage
        return TranslateStage()

    def test_no_segments(self, stage):
        result = stage.execute("id", {}, lambda *a: None, lambda *a: None, lambda: False)
        assert result.success is True
        assert result.data.get("translated") is False

    @patch("madrac.pipeline.stages.translate.get_config")
    @patch("madrac.pipeline.stages.translate.get_logger")
    def test_disabled(self, mock_log, mock_config, stage):
        mock_config.return_value = False
        result = stage.execute("id", {"segments": [{"text": "hi"}]},
                               lambda *a: None, lambda *a: None, lambda: False)
        assert result.success is True
        assert result.data.get("translated") is False


# ============================================================================
# Hardening tests: crash recovery, atomic save, metrics, plugins, threading
# ============================================================================

class TestCrashRecovery:
    def test_processing_reverts_to_pending(self, tmp_path):
        qm = QueueManager(str(tmp_path / "queue.json"))
        e = qm.add("/crash.mp4")
        qm.set_state(e.id, ProcessingState.PROCESSING)
        qm.save()

        qm2 = QueueManager(str(tmp_path / "queue.json"))
        recovered = qm2.get(e.id)
        assert recovered is not None
        assert recovered.state == ProcessingState.PENDING
        assert recovered.error is not None
        assert "crash" in recovered.error.lower()

    def test_no_corruption_on_clean_states(self, tmp_path):
        qm = QueueManager(str(tmp_path / "queue2.json"))
        a = qm.add("/a.mp4")
        b = qm.add("/b.mp4")
        qm.set_state(a.id, ProcessingState.COMPLETED)
        qm.set_state(b.id, ProcessingState.FAILED)
        qm.save()

        qm2 = QueueManager(str(tmp_path / "queue2.json"))
        assert qm2.get(a.id).state == ProcessingState.COMPLETED
        assert qm2.get(b.id).state == ProcessingState.FAILED


class TestAtomicSave:
    def test_tmp_file_does_not_persist(self, tmp_path):
        qm = QueueManager(str(tmp_path / "queue_atomic.json"))
        qm.add("/test.mp4")
        qm.save()
        # tmp file should be cleaned up after successful write
        tmp = tmp_path / "queue_atomic.json.tmp"
        assert not tmp.exists()

    def test_save_is_readable(self, tmp_path):
        qm = QueueManager(str(tmp_path / "queue_read.json"))
        e = qm.add("/persist.mp4")
        qm.set_state(e.id, ProcessingState.COMPLETED)
        qm.save()
        data = (tmp_path / "queue_read.json").read_text("utf-8")
        import json
        parsed = json.loads(data)
        assert len(parsed["items"]) == 1
        assert parsed["items"][0]["state"] == "COMPLETED"


class TestMetrics:
    def test_collector_empty(self):
        from madrac.pipeline.stages.metrics import MetricsCollector
        mc = MetricsCollector()
        m = mc.build()
        assert m.total_s == 0.0
        assert len(m.stages) == 0

    def test_collector_one_stage(self):
        from madrac.pipeline.stages.metrics import MetricsCollector
        mc = MetricsCollector()
        mc.reset("item1")
        mc.stage_start("test_stage")
        import time
        time.sleep(0.01)
        mc.stage_end()
        m = mc.build()
        assert len(m.stages) == 1
        assert m.stages[0].stage == "test_stage"
        assert m.stages[0].item_id == "item1"
        assert m.stages[0].duration_s > 0.0

    def test_collector_multiple_stages(self):
        from madrac.pipeline.stages.metrics import MetricsCollector
        mc = MetricsCollector()
        mc.reset("item2")
        mc.stage_start("audio")
        mc.stage_end()
        mc.stage_start("transcribe")
        mc.stage_end()
        m = mc.build(audio_duration_s=100.0)
        assert len(m.stages) == 2
        assert m.audio_duration_s == 100.0
        assert m.rtf >= 0.0

    def test_format_log(self):
        from madrac.pipeline.stages.metrics import StageMetrics, PipelineMetrics
        pm = PipelineMetrics(
            stages=[
                StageMetrics(stage="audio", duration_s=1.5, item_id="x"),
                StageMetrics(stage="transcribe", duration_s=30.0, item_id="x"),
            ],
            total_s=31.5, audio_duration_s=60.0, rtf=0.525, ram_peak_mb=500.0,
        )
        from madrac.pipeline.stages.metrics import MetricsCollector
        mc = MetricsCollector()
        text = mc.format_log(pm)
        assert "audio" in text
        assert "transcribe" in text
        assert "rtf" in text


class TestPipelineStageCleanup:
    def test_cleanup_does_nothing(self):
        from madrac.pipeline.stages.base import PipelineStage
        s = PipelineStage()
        s.name = "test"
        s.cleanup()  # should not raise

    def test_cleanup_called_after_execute(self):
        from madrac.pipeline.stages.base import PipelineStage, StageResult
        class TestStage(PipelineStage):
            name = "test"
            cleaned_up = False
            def execute(self, *args, **kwargs):
                return StageResult(True)
            def cleanup(self):
                TestStage.cleaned_up = True
        s = TestStage()
        s.execute("id", {}, lambda *a: None, lambda *a: None, lambda: False)
        s.cleanup()
        assert TestStage.cleaned_up is True


class TestPluginAPI:
    def test_plugin_api_version_default(self):
        from madrac.core.plugins.api import MadracPlugin
        assert MadracPlugin.api_version == 1

    def test_plugin_name_required(self):
        from madrac.core.plugins.api import MadracPlugin
        class BadPlugin(MadracPlugin):
            pass
        import pytest
        with pytest.raises(ValueError, match="name"):
            BadPlugin()

    def test_plugin_good(self):
        from madrac.core.plugins.api import MadracPlugin, PluginAPI
        class GoodPlugin(MadracPlugin):
            name = "test_good"
            version = "1.0.0"
        p = GoodPlugin()
        assert p.name == "test_good"
        # initialize should not raise
        api = PluginAPI("test_good", "1.0.0")
        p.initialize(api)  # no-op base implementation

    def test_register_stage(self):
        from madrac.core.plugins.api import PluginAPI
        api = PluginAPI("test", "1.0")
        class FakeStage:
            pass
        api.register_stage("ocr", FakeStage)
        regs = api.get_registered_stages()
        assert len(regs) == 1
        assert regs[0]["name"] == "ocr"


class TestPluginManager:
    def test_discover_no_plugins(self, tmp_path):
        from madrac.core.plugins.manager import PluginManager
        mgr = PluginManager([tmp_path / "nonexistent"])
        handles = mgr.discover_all()
        assert len(handles) == 0

    def test_init_failed_plugin_continues(self, tmp_path):
        from madrac.core.plugins.manager import PluginManager, PluginState
        mgr = PluginManager([tmp_path])
        # Create a plugin dir with a broken module
        plugin_dir = tmp_path / "broken_plugin"
        plugin_dir.mkdir()
        (plugin_dir / "__init__.py").write_text(
            "from madrac.core.plugins.api import MadracPlugin\n"
            "class BrokenPlugin(MadracPlugin):\n"
            "    name = 'broken'\n"
            "    version = '0.1'\n"
            "    def initialize(self, api):\n"
            "        raise RuntimeError('init failed')\n"
        )
        mgr.discover_all()
        mgr.init_all()
        plug = mgr.get_plugin("broken")
        assert plug is not None
        assert plug.state == PluginState.FAILED


class TestQueueGuard:
    def test_next_pending_blocked_by_active(self, tmp_path):
        qm = QueueManager(str(tmp_path / "guard.json"))
        a = qm.add("/active.mp4")
        qm.add("/pending.mp4")
        qm.set_state(a.id, ProcessingState.PROCESSING)
        assert qm.next_pending() is None

    def test_next_pending_after_completion(self, tmp_path):
        qm = QueueManager(str(tmp_path / "guard2.json"))
        a = qm.add("/first.mp4")
        qm.set_state(a.id, ProcessingState.COMPLETED)
        b = qm.add("/second.mp4")
        nxt = qm.next_pending()
        assert nxt is not None
        assert nxt.id == b.id

    def test_queue_close_flushes(self, tmp_path):
        qm = QueueManager(str(tmp_path / "flush.json"))
        qm.add("/flush.mp4")
        qm.close()
        assert (tmp_path / "flush.json").exists()


class TestConfigSalida:
    def test_salida_defaults_loaded(self):
        from madrac.config import get_config_manager
        cfg = get_config_manager()
        assert cfg.get("salida.formato", "") == "srt"
        assert cfg.get("salida.directorio", "MISSING") == ""

    def test_salida_in_schema(self):
        from madrac.config.schema import _TYPE_SCHEMA
        assert "salida.formato" in _TYPE_SCHEMA
        assert "salida.directorio" in _TYPE_SCHEMA


class TestMAX_ACTIVE_PIPELINES:
    def test_constant_exists(self):
        from madrac.pipeline import MAX_ACTIVE_PIPELINES
        assert MAX_ACTIVE_PIPELINES == 1
