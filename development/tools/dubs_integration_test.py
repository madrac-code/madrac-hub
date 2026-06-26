#!/usr/bin/env python3
"""
dubs_integration_test.py

Standalone validation script for the MADRAC DUBS pipeline.
Launches madrac-dubbing.exe as a subprocess, submits a dubbing job,
and validates the output.

Usage:
    python dubs_integration_test.py ^
        --dubs-exe D:\madrac-dubs\madrac-dubbing.exe ^
        --video D:\videos\test.mp4 ^
        --srt D:\videos\test.srt

Exits 0 on success, 1 on failure.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

try:
    import requests as http_lib
    HAS_REQUESTS = True
except ImportError:
    import urllib.request as http_lib
    import urllib.error
    HAS_REQUESTS = False


API_PORT = 5000
API_BASE = f"http://127.0.0.1:{API_PORT}"
HEALTH_CHECK_TIMEOUT_S = 15
HEALTH_CHECK_INTERVAL_S = 1
POLL_INTERVAL_S = 2
JOB_TIMEOUT_S = 600  # 10 minutes

_dubs_process = None


def timestamp() -> str:
    return datetime.now(timezone.utc).strftime("[%H:%M:%S]")


def log(msg: str):
    print(f"{timestamp()} {msg}", flush=True)


def http_get(path: str):
    url = f"{API_BASE}{path}"
    if HAS_REQUESTS:
        resp = http_lib.get(url, timeout=5)
        resp.raise_for_status()
        return resp.json()
    else:
        req = http_lib.Request(url)
        with http_lib.urlopen(req, timeout=5) as r:
            return json.loads(r.read().decode())


def http_post(path: str, payload: dict):
    url = f"{API_BASE}{path}"
    data = json.dumps(payload).encode("utf-8")
    if HAS_REQUESTS:
        resp = http_lib.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()
    else:
        req = http_lib.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        with http_lib.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())


def launch_dubs(exe_path: str) -> subprocess.Popen:
    log(f"Launching: {exe_path} api --port {API_PORT}")
    return subprocess.Popen(
        [exe_path, "api", "--port", str(API_PORT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )


def wait_for_health(proc: subprocess.Popen) -> bool:
    deadline = time.time() + HEALTH_CHECK_TIMEOUT_S
    while time.time() < deadline:
        try:
            resp = http_get("/health")
            if resp.get("status") == "ok":
                log("DUBS health check passed")
                return True
        except Exception:
            pass
        time.sleep(HEALTH_CHECK_INTERVAL_S)

    log("DUBS health check FAILED — reading stderr:")
    try:
        _, stderr = proc.communicate(timeout=3)
        log(stderr.decode("utf-8", errors="replace"))
    except Exception:
        log("(could not read stderr)")
    return False


def poll_job(job_id: str):
    deadline = time.time() + JOB_TIMEOUT_S
    while time.time() < deadline:
        try:
            resp = http_get(f"/dubbing/{job_id}")
        except Exception as e:
            log(f"Poll error: {e}")
            time.sleep(POLL_INTERVAL_S)
            continue

        status = resp.get("status", "unknown")
        progress = resp.get("progress_pct", 0)
        message = resp.get("message", "")
        log(f"Job {job_id[:8]} | {status} | {progress}% | {message}")

        if status == "completed":
            return resp
        if status == "failed":
            log(f"❌ Job failed: {resp.get('error', 'unknown error')}")
            return None

        time.sleep(POLL_INTERVAL_S)

    log("⏱ Timeout exceeded")
    return None


def cleanup():
    global _dubs_process
    if _dubs_process and _dubs_process.poll() is None:
        log("Terminating DUBS subprocess")
        _dubs_process.terminate()
        try:
            _dubs_process.wait(timeout=5)
        except Exception:
            log("Force killing DUBS subprocess")
            _dubs_process.kill()
        _dubs_process = None


def main():
    global _dubs_process

    parser = argparse.ArgumentParser(description="Validate DUBS integration pipeline")
    parser.add_argument("--dubs-exe", required=True, help="Path to madrac-dubbing.exe")
    parser.add_argument("--video", required=True, help="Path to test video file")
    parser.add_argument("--srt", required=True, help="Path to test .srt file")
    args = parser.parse_args()

    for path, label in [(args.dubs_exe, "DUBS exe"), (args.video, "Video"), (args.srt, "SRT")]:
        if not os.path.isfile(path):
            log(f"❌ {label} not found: {path}")
            sys.exit(1)

    video_dir = os.path.dirname(os.path.abspath(args.video))
    video_stem = os.path.splitext(os.path.basename(args.video))[0]
    output_path = os.path.join(video_dir, f"{video_stem}_dubbed.mkv")

    log("=== MADRAC DUBS Integration Test ===")
    log(f"DUBS exe: {args.dubs_exe}")
    log(f"Video:    {args.video}")
    log(f"SRT:      {args.srt}")
    log(f"Output:   {output_path}")
    log("")

    try:
        _dubs_process = launch_dubs(args.dubs_exe)

        if not wait_for_health(_dubs_process):
            cleanup()
            sys.exit(1)

        payload = {
            "video_path": args.video,
            "srt_path": args.srt,
            "output_path": output_path,
            "config": {
                "language": "es",
                "voice": "female",
                "reduce_vocals": 0.3,
            },
        }

        log("Submitting dubbing job...")
        try:
            result = http_post("/dubbing", payload)
        except Exception as e:
            log(f"❌ POST /dubbing failed: {e}")
            cleanup()
            sys.exit(1)

        job_id = result.get("job_id")
        log(f"Job submitted: {job_id}")

        final = poll_job(job_id)
        if final is None:
            cleanup()
            sys.exit(1)

        if not os.path.isfile(output_path):
            log(f"❌ Output file not found: {output_path}")
            cleanup()
            sys.exit(1)

        output_size = os.path.getsize(output_path)
        log(f"✅ Integration test passed. Output: {output_path} ({output_size:,} bytes)")

    except KeyboardInterrupt:
        log("\nInterrupted by user")
        cleanup()
        sys.exit(1)
    finally:
        cleanup()

    sys.exit(0)


if __name__ == "__main__":
    main()
