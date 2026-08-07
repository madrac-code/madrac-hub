"""Workspace tools for MADRAC MCP — subtitle editing and export.

Provides tools for:
- Workspace inspection (info, list, segments)
- Speaker renaming
- Subtitle segment editing
- SRT export
"""

from typing import Any

from madrac.workspace.shared import SharedWorkspace, list_workspaces as list_workspaces_fn


def get_workspace_info(app_state: dict[str, Any]):
    async def _get_workspace_info(job_id: str) -> dict:
        """
        Get metadata and artifact status for a job workspace.

        Args:
            job_id: Job ID (sha256-<hash>)

        Returns:
            Workspace metadata including artifact status, or {"error": "..."}
        """
        try:
            ws = SharedWorkspace.from_job_id(job_id)
            meta = ws.load_metadata()
            if not meta:
                return {"error": f"Workspace not found: {job_id}"}

            has_audio = ws.has_whisper_audio()
            has_full = ws.has_full_audio()
            has_segments = ws.has_segments()
            has_stems = ws.has_stems()

            return {
                "job_id": job_id,
                "metadata": meta,
                "artifacts": {
                    "whisper_audio": has_audio,
                    "full_audio": has_full,
                    "segments": has_segments,
                    "stems": has_stems,
                },
            }
        except FileNotFoundError:
            return {"error": f"Workspace not found: {job_id}"}
        except Exception as e:
            return {"error": str(e)}
    return _get_workspace_info


def list_workspaces(app_state: dict[str, Any]):
    async def _list_workspaces() -> dict:
        """
        List all available job workspaces with artifact status.

        Returns:
            {"workspaces": [{"job_id": "...", "artifacts": {...}}, ...]}
        """
        try:
            job_ids = list_workspaces_fn()
            workspaces = []
            for jid in job_ids:
                ws = SharedWorkspace.from_job_id(jid)
                meta = ws.load_metadata() or {}
                workspaces.append({
                    "job_id": jid,
                    "source_video": meta.get("source_video", ""),
                    "updated_at": meta.get("updated_at", 0),
                    "artifacts": {
                        "whisper_audio": ws.has_whisper_audio(),
                        "full_audio": ws.has_full_audio(),
                        "segments": ws.has_segments(),
                        "stems": ws.has_stems(),
                    },
                })
            return {"workspaces": workspaces}
        except Exception as e:
            return {"error": str(e)}
    return _list_workspaces


def get_segments(app_state: dict[str, Any]):
    async def _get_segments(job_id: str) -> dict:
        """
        Get all transcription segments for a job.

        Returns:
            {"segments": [{"id": 0, "start": 0.0, "end": 1.0, "text": "..."}, ...]}
            or {"error": "..."}
        """
        try:
            ws = SharedWorkspace.from_job_id(job_id)
            data = ws.load_segments()
            if not data:
                return {"error": f"No segments found in workspace: {job_id}"}
            segments = data.get("segments", [])
            return {
                "job_id": job_id,
                "segments": [
                    {"id": i, "start": s["start"], "end": s["end"], "text": s["text"]}
                    for i, s in enumerate(segments)
                ],
            }
        except FileNotFoundError:
            return {"error": f"Workspace not found: {job_id}"}
        except Exception as e:
            return {"error": str(e)}
    return _get_segments


def rename_speaker(app_state: dict[str, Any]):
    async def _rename_speaker(job_id: str, speaker_id: int, name: str) -> dict:
        """
        Rename a speaker track in a workspace.

        Args:
            job_id: Job ID (sha256-<hash>)
            speaker_id: Speaker track index
            name: New speaker name

        Returns:
            {"success": True, "speaker_id": N, "name": "..."}
            or {"error": "..."}
        """
        try:
            ws = SharedWorkspace.from_job_id(job_id)
            meta = ws.load_metadata() or {}
            speakers = meta.get("speakers", {})

            if str(speaker_id) not in speakers:
                return {"error": f"Speaker {speaker_id} not found in workspace"}

            old_name = speakers[str(speaker_id)]
            speakers[str(speaker_id)] = name
            ws.update_metadata(speakers=speakers)

            return {
                "success": True,
                "job_id": job_id,
                "speaker_id": speaker_id,
                "old_name": old_name,
                "new_name": name,
            }
        except FileNotFoundError:
            return {"error": f"Workspace not found: {job_id}"}
        except Exception as e:
            return {"error": str(e)}
    return _rename_speaker


def edit_subtitle_segment(app_state: dict[str, Any]):
    async def _edit_subtitle_segment(
        job_id: str,
        segment_id: int,
        new_text: str,
    ) -> dict:
        """
        Edit the text of a specific subtitle segment in a workspace.
        Changes are persisted to segments.json immediately.

        Args:
            job_id: Job ID (sha256-<hash>)
            segment_id: Segment index (0-based, from get_segments)
            new_text: New text content for this segment

        Returns:
            {"success": True, "segment_id": N, "old_text": "...",
             "new_text": "..."}
            or {"error": "..."}
        """
        try:
            ws = SharedWorkspace.from_job_id(job_id)
            data = ws.load_segments()
            if not data:
                return {"error": f"No segments found in workspace: {job_id}"}

            segments = data.get("segments", [])

            if segment_id < 0 or segment_id >= len(segments):
                return {"error": f"Segment {segment_id} not found"}

            old_text = segments[segment_id]["text"]
            segments[segment_id]["text"] = new_text

            # Preserve language and source from original
            language = data.get("language", "")
            source = data.get("source", "edited")

            ws.save_segments(segments, language=language, source=source)

            return {
                "success": True,
                "job_id": job_id,
                "segment_id": segment_id,
                "old_text": old_text,
                "new_text": new_text,
            }
        except FileNotFoundError:
            return {"error": f"Workspace not found: {job_id}"}
        except Exception as e:
            return {"error": str(e)}
    return _edit_subtitle_segment


def export_srt(app_state: dict[str, Any]):
    async def _export_srt(
        job_id: str,
        output_path: str = "",
    ) -> dict:
        """
        Export segments from workspace as a .srt file.

        Args:
            job_id: Job ID (sha256-<hash>)
            output_path: Optional absolute path for output .srt file.
                        If empty, saves next to the source video
                        as <source_name>_edited.srt

        Returns:
            {"success": True, "srt_path": "...", "segment_count": N}
            or {"error": "..."}
        """
        try:
            from pathlib import Path

            ws = SharedWorkspace.from_job_id(job_id)
            data = ws.load_segments()
            if not data:
                return {"error": f"No segments in workspace: {job_id}"}

            segments = data.get("segments", [])

            if output_path:
                srt_path = Path(output_path)
            else:
                meta = ws.load_metadata()
                source = meta.get("source", {})
                source_path = Path(source.get("path", ""))
                if source_path.exists():
                    srt_path = source_path.with_suffix("").parent / \
                        f"{source_path.stem}_edited.srt"
                else:
                    srt_path = ws.root / "output.srt"

            srt_path.parent.mkdir(parents=True, exist_ok=True)

            def ms_to_srt_time(seconds: float) -> str:
                ms = int(seconds * 1000)
                h = ms // 3600000
                ms %= 3600000
                m = ms // 60000
                ms %= 60000
                s = ms // 1000
                ms %= 1000
                return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

            lines = []
            for seg in segments:
                lines.append(str(seg.get("id", 0) + 1))
                start = ms_to_srt_time(seg["start"])
                end = ms_to_srt_time(seg["end"])
                lines.append(f"{start} --> {end}")
                lines.append(seg["text"].strip())
                lines.append("")

            srt_content = "\n".join(lines)
            srt_path.write_text(srt_content, encoding="utf-8")

            return {
                "success": True,
                "srt_path": str(srt_path),
                "segment_count": len(segments),
            }
        except FileNotFoundError:
            return {"error": f"Workspace not found: {job_id}"}
        except Exception as e:
            return {"error": str(e)}
    return _export_srt


__all__ = [
    "get_workspace_info",
    "list_workspaces",
    "get_segments",
    "rename_speaker",
    "edit_subtitle_segment",
    "export_srt",
]