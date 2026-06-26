#!/usr/bin/env python3
"""Diagnóstico directo: ejecuta el pipeline sin API."""
import asyncio
import sys, io, os, time
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Add src to path
src = str(Path(r"D:\madrac-dubs\venv\Scripts\python.exe").resolve().parent.parent.parent / "src")
sys.path.insert(0, src)

os.environ["MADRAC_OPERATING_MODE"] = "standalone"
os.environ["MADRAC_SKIP_VALIDATION"] = "true"

from madrac_dubbing.pipeline.models import DubbingJob, DubbingConfig, DubbingStatus
from madrac_dubbing.pipeline.dubbing_pipeline import DubbingPipeline

def on_progress(job):
    print(f"  [{job.progress_pct}%] {job.message}", flush=True)

def on_log(msg):
    pass

pipeline = DubbingPipeline(on_progress=on_progress, on_log=on_log)

config = DubbingConfig(language="es")
job = DubbingJob(
    job_id="test-001",
    video_path=Path(r"D:\De Noorderlingen (1992) de brief in de bus bezorgen (Alex van Warmerdam).mp4"),
    srt_path=Path(r"D:\De Noorderlingen (1992) de brief in de bus bezorgen (Alex van Warmerdam).srt"),
    output_path=Path(r"D:\_dub_direct_test.mkv"),
    config=config,
)

print("Starting pipeline...", flush=True)
try:
    ok = pipeline.process(job)
    print(f"Result: {'OK' if ok else 'FAIL'}", flush=True)
    if job.error:
        print(f"Error: {job.error}", flush=True)
except Exception as e:
    print(f"Exception: {type(e).__name__}: {e}", flush=True)
    import traceback
    traceback.print_exc()
