"""DubbingManager — launches DUBS, submits jobs, polls progress."""

import logging
import os
import socket
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("madrac.dubbing.manager")

HEALTH_TIMEOUT_S = 45
HEALTH_INTERVAL_S = 1
POLL_INTERVAL_S = 2


def _find_free_port() -> int:
    """Bind to port 0 and return the assigned free port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class DubbingManager(QObject):
    """Manages the lifecycle of a DUBS subprocess and dubbing jobs.

    Signals
    -------
    health_check_passed()
    health_check_failed(error: str)
    job_progress(pct: int, status: str, message: str)
    job_completed(output_path: str)
    job_failed(error: str)
    """

    health_check_passed = Signal()
    health_check_failed = Signal(str)
    job_progress = Signal(int, str, str)
    job_completed = Signal(str)
    job_failed = Signal(str)

    def __init__(self, dubs_python_path: str = "", parent: QObject = None):
        super().__init__(parent)
        self._dubs_python_path = dubs_python_path or sys.executable
        self._process: Optional[subprocess.Popen] = None
        self._requests = None
        self._port = _find_free_port()
        self._api_base = f"http://127.0.0.1:{self._port}"

    def _ensure_requests(self):
        if self._requests is None:
            import requests as _r
            self._requests = _r

    # ------------------------------------------------------------------
    # Subprocess lifecycle
    # ------------------------------------------------------------------

    def launch_dubs(self) -> bool:
        """Start the DUBS API subprocess and wait for health check.

        Returns True if the API responds within HEALTH_TIMEOUT_S.
        """
        if self._process and self._process.poll() is None:
            logger.info("DUBS subprocess already running")
            return True

        python_path = Path(self._dubs_python_path).resolve()
        base = python_path.parent.parent.parent

        # Buscar el directorio raíz de PYTHONPATH donde madrac_dubbing sea importable
        # Monorepo: PYTHONPATH=.../src/madrac_dubbing/src → package en .../src/madrac_dubbing/src/madrac_dubbing
        # Standalone: PYTHONPATH=.../src → package en .../src/madrac_dubbing
        pythonpath_candidates = [
            base / "src" / "madrac_dubbing" / "src",        # dev: monorepo layout
            base / "src",                                  # dev: standalone layout
            base / "opt" / "madrac-hub" / "src" / "madrac_dubbing" / "src",  # AppImage monorepo
            base / "opt" / "madrac-hub" / "src",            # AppImage standalone
        ]

        src_path = None
        for pp in pythonpath_candidates:
            if (pp / "madrac_dubbing").is_dir() or (pp / "madrac_dubbing" / "__init__.py").exists():
                src_path = pp
                break

        if src_path is None:
            self.health_check_failed.emit(
                f"madrac_dubbing package not found (tried: {[str(p) for p in pythonpath_candidates]})"
            )
            return False
        # Build minimal env — full copy of os.environ can cause [Errno 22] on Windows
        _current_pp = os.environ.get("PYTHONPATH", "")
        _pythonpath = str(src_path)
        if _current_pp:
            _pythonpath = f"{_pythonpath}:{_current_pp}"
        env = {"PYTHONPATH": _pythonpath}
        for _k in ("PATH", "LD_LIBRARY_PATH", "SYSTEMROOT", "TEMP", "TMP",
                   "USERPROFILE", "APPDATA", "LOCALAPPDATA", "COMSPEC", "PATHEXT"):
            _v = os.environ.get(_k)
            if _v is not None:
                env[_k] = _v

        cmd = [str(python_path), "-m", "madrac_dubbing", "api", "--port", str(self._port)]
        cwd = str(src_path.parent)
        logger.info("Launching DUBS: %s", " ".join(cmd))

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                cwd=cwd,
                env=env,
            )
        except FileNotFoundError:
            self.health_check_failed.emit(f"Python not found: {self._dubs_python_path}")
            return False
        except Exception as e:
            logger.error("[DUB] Popen failed: %s", e)
            logger.error(traceback.format_exc())
            self.health_check_failed.emit(str(e))
            return False

        ok = self._wait_for_health()
        if ok:
            self._start_stderr_thread()
        return ok

    def _wait_for_health(self) -> bool:
        deadline = time.time() + HEALTH_TIMEOUT_S
        _last_log = time.time()
        while time.time() < deadline:
            if self._process is not None and self._process.poll() is not None:
                stderr = self._read_stderr()[:300]
                self.health_check_failed.emit(f"DUBS exited early: {stderr}")
                return False
            try:
                self._ensure_requests()
                resp = self._requests.get(f"{self._api_base}/health", timeout=3)
                if resp.status_code == 200 and resp.json().get("status") == "ok":
                    logger.info("DUBS health check passed")
                    time.sleep(1)  # dar tiempo a Flask para terminar init
                    self.health_check_passed.emit()
                    return True
            except self._requests.exceptions.ConnectionError:
                pass
            except OSError as _e:
                if _e.errno != 22:
                    logger.debug("Health check OSError %d: %s", _e.errno, _e)
            except Exception as _e:
                logger.debug("Health check error: %s: %s", type(_e).__name__, _e)
            # Log progress every 5s
            if time.time() - _last_log >= 5:
                elapsed = round(time.time() - (deadline - HEALTH_TIMEOUT_S))
                logger.debug("Health check waiting… %ds elapsed / %ds timeout", elapsed, HEALTH_TIMEOUT_S)
                _last_log = time.time()
            time.sleep(HEALTH_INTERVAL_S)

        error = self._read_stderr()
        self.health_check_failed.emit(error or "Health check timeout")
        return False

    def _read_stderr(self) -> str:
        if self._process and self._process.stderr:
            try:
                return self._process.stderr.read(4096).decode("utf-8", errors="replace")
            except Exception:
                return ""
        return ""

    def _start_stderr_thread(self):
        def _pipe():
            try:
                for line in self._process.stderr:
                    decoded = line.decode("utf-8", errors="replace").rstrip()
                    if decoded:
                        logger.warning("[DUBS stderr] %s", decoded)
            except Exception:
                pass
        t = threading.Thread(target=_pipe, daemon=True)
        t.start()

    # ------------------------------------------------------------------
    # Job lifecycle
    # ------------------------------------------------------------------

    def submit_job(
        self,
        video_path: str,
        srt_path: str,
        output_path: str,
        config: dict,
    ) -> Optional[str]:
        """Submit a dubbing job and return the job_id, or None on failure."""
        self._ensure_requests()
        payload = {
            "video_path": video_path,
            "srt_path": srt_path,
            "output_path": output_path,
            "config": config,
        }

        for attempt in range(5):
            try:
                resp = self._requests.post(f"{self._api_base}/dubbing", json=payload, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                return data.get("job_id")
            except OSError as _e:
                if _e.errno == 22 and attempt < 4:
                    logger.debug("submit_job retry %d/5: OSError 22", attempt + 1)
                    time.sleep(2)
                    continue
                raise
            except Exception as e:
                if attempt < 4:
                    logger.debug("submit_job retry %d/5: %s", attempt + 1, e)
                    time.sleep(2)
                    continue
                logger.error("[DUB] submit_job failed after 5 attempts: %s", e)
                logger.error(traceback.format_exc())
                self.job_failed.emit(f"Submit failed: {e}")
                return None

    def poll_job(self, job_id: str) -> dict:
        """Poll a job and return the full response dict.

        Emits job_progress / job_completed / job_failed as appropriate.
        """
        self._ensure_requests()
        try:
            resp = self._requests.get(f"{self._api_base}/dubbing/{job_id}", timeout=5)
            resp.raise_for_status()
            data = resp.json()
        except OSError as e:
            if e.errno == 22:
                raise
            raise
        except Exception as e:
            logger.error("[DUB] poll_job failed: %s", e)
            logger.error(traceback.format_exc())
            self.job_failed.emit(f"Poll failed: {e}")
            return {}

        status = data.get("status", "")
        progress = data.get("progress_pct", 0)
        message = data.get("message", "")

        if status == "failed":
            error = data.get("error", "Unknown error")
            self.job_failed.emit(error)
        elif status == "completed":
            output_path = data.get("output_path", "")
            self.job_completed.emit(output_path)
        else:
            self.job_progress.emit(progress, status, message)

        return data

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def shutdown(self):
        """Terminate the DUBS subprocess if running."""
        if self._process and self._process.poll() is None:
            logger.info("Shutting down DUBS subprocess")
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception:
                logger.warning("Force killing DUBS subprocess")
                self._process.kill()
        self._process = None
