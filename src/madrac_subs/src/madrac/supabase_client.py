"""
Supabase client for MADRAC-SUBS V3 (auth + community API).
Async OAuth login via QTimer polling so the UI never freezes.
"""

import base64
import hashlib
import json
import logging
import secrets
import re
import time
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, parse_qs

import requests

from PySide6.QtCore import QObject, Signal, QTimer

from .core.paths import get_cache_dir
from .core import read_text, write_text, write_binary, read_json, write_json

logger = logging.getLogger("madrac.supabase")

SUPABASE_URL = "https://fypmjtesckrgboorjibl.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZ5cG1qdGVzY2tyZ2Jvb3JqaWJsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzkyMTIwOTksImV4cCI6MjA5NDc4ODA5OX0.B9hnQ0PUd6ccXmemvQ62lWcz5iR-7QlNC_a70sWZtMA"


def _pkce_pair() -> tuple:
    verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


class _CallbackHandler(BaseHTTPRequestHandler):
    _code = None
    _event = threading.Event()

    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        code = params.get("code", [None])[0]
        if code:
            self.__class__._code = code
            self.__class__._event.set()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h3>Autenticacion completada.</h3>"
                b"<p>Puedes cerrar esta pestana.</p></body></html>"
            )
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<html><body><h3>Error de autenticacion</h3></body></html>")

    def log_message(self, fmt, *args):
        pass


def _obtener_codigo_oauth(puerto: int, timeout: int = 120) -> Optional[str]:
    """Bloqueante — solo usado internamente en el polling timer."""
    servidor = HTTPServer(("127.0.0.1", puerto), _CallbackHandler)
    _CallbackHandler._code = None
    _CallbackHandler._event.clear()
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    try:
        if not _CallbackHandler._event.wait(timeout=timeout):
            return None
        return _CallbackHandler._code
    finally:
        servidor.shutdown()


def _puerto_libre() -> int:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _ruta_sesion() -> Path:
    return get_cache_dir() / "sesion.json"


class SupabaseClient(QObject):
    """Supabase auth + community API client (async login)."""

    loginFinished = Signal(bool)
    loginError = Signal(str)

    def __init__(self):
        super().__init__()
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._user: Optional[Dict[str, Any]] = None
        self._online = False
        self._oauth_timer: Optional[QTimer] = None
        self._oauth_server: Optional[HTTPServer] = None
        self._oauth_start: float = 0.0
        self._storage_url = f"{SUPABASE_URL}/storage/v1/object/subtitle-files/"
        self._restaurar_sesion()

    # ── Sesion ───────────────────────────────────────────────

    def _restaurar_sesion(self) -> None:
        ruta = _ruta_sesion()
        if not ruta.exists():
            return
        try:
            datos = read_json(ruta)
            self._access_token = datos.get("access_token")
            self._refresh_token = datos.get("refresh_token")
            self._user = datos.get("user")
            if self._access_token and self._validar_token():
                self._online = True
                logger.info("Sesion restaurada: %s", self._user.get("email", "?"))
            else:
                self._limpiar_sesion()
        except (json.JSONDecodeError, KeyError):
            self._limpiar_sesion()

    def _guardar_sesion(self) -> None:
        ruta = _ruta_sesion()
        ruta.parent.mkdir(parents=True, exist_ok=True)
        write_json(ruta, {
            "access_token": self._access_token,
            "refresh_token": self._refresh_token,
            "user": self._user,
        })

    def _limpiar_sesion(self) -> None:
        self._access_token = None
        self._refresh_token = None
        self._user = None
        self._online = False
        ruta = _ruta_sesion()
        if ruta.exists():
            ruta.unlink()

    def _validar_token(self) -> bool:
        if not self._access_token:
            return False
        try:
            resp = requests.get(
                f"{SUPABASE_URL}/auth/v1/user",
                headers={
                    "apikey": SUPABASE_ANON_KEY,
                    "Authorization": f"Bearer {self._access_token}",
                },
                timeout=10,
            )
            if resp.status_code == 200:
                return True
            if resp.status_code == 401 and self._refresh_token:
                return self._refrescar()
            return False
        except requests.RequestException:
            return False

    def _refrescar(self) -> bool:
        try:
            resp = requests.post(
                f"{SUPABASE_URL}/auth/v1/token?grant_type=refresh_token",
                headers={
                    "apikey": SUPABASE_ANON_KEY,
                    "Content-Type": "application/json",
                },
                json={"refresh_token": self._refresh_token},
                timeout=10,
            )
            if resp.status_code == 200:
                datos = resp.json()
                self._access_token = datos["access_token"]
                self._refresh_token = datos.get("refresh_token", self._refresh_token)
                self._user = datos.get("user", self._user)
                self._guardar_sesion()
                return True
        except requests.RequestException as e:
            logger.warning("Error refrescando token: %s", e)
        return False

    # ── Auth (async via QTimer poll) ─────────────────────────

    def login_google_async(self) -> None:
        """Non-blocking OAuth login. Emits loginFinished(bool) when done."""
        if self._oauth_timer and self._oauth_timer.isActive():
            return

        self._oauth_verifier, challenge = _pkce_pair()
        puerto = _puerto_libre()
        redirect = f"http://127.0.0.1:{puerto}"
        auth_url = (
            f"{SUPABASE_URL}/auth/v1/authorize"
            f"?provider=google"
            f"&redirect_to={redirect}"
            f"&response_type=code"
            f"&code_challenge={challenge}"
            f"&code_challenge_method=s256"
            f"&scope=email%20profile"
        )

        _CallbackHandler._code = None
        _CallbackHandler._event.clear()
        self._oauth_server = HTTPServer(("127.0.0.1", puerto), _CallbackHandler)
        threading.Thread(target=self._oauth_server.serve_forever, daemon=True).start()

        webbrowser.open(auth_url)

        self._oauth_start = time.monotonic()
        self._oauth_timer = QTimer(self)
        self._oauth_timer.setInterval(100)
        self._oauth_timer.timeout.connect(self._poll_oauth)
        self._oauth_timer.start()

    def _poll_oauth(self) -> None:
        if _CallbackHandler._event.is_set():
            self._oauth_timer.stop()
            self._oauth_timer = None
            codigo = _CallbackHandler._code
            if self._oauth_server:
                self._oauth_server.shutdown()
                self._oauth_server = None
            ok = self._exchange_code(codigo, self._oauth_verifier)
            self._oauth_verifier = None
            self.loginFinished.emit(ok)
        elif time.monotonic() - self._oauth_start > 120:
            self._oauth_timer.stop()
            self._oauth_timer = None
            if self._oauth_server:
                self._oauth_server.shutdown()
                self._oauth_server = None
            logger.warning("Autenticacion cancelada o timeout")
            self.loginFinished.emit(False)

    def _exchange_code(self, codigo: str, verifier: str) -> bool:
        try:
            resp = requests.post(
                f"{SUPABASE_URL}/auth/v1/token?grant_type=pkce",
                headers={
                    "apikey": SUPABASE_ANON_KEY,
                    "Content-Type": "application/json",
                },
                json={
                    "auth_code": codigo,
                    "code_verifier": verifier,
                },
                timeout=15,
            )
            if resp.status_code != 200:
                logger.warning("Error al intercambiar codigo: %s", resp.text)
                return False
            datos = resp.json()
            self._access_token = datos["access_token"]
            self._refresh_token = datos.get("refresh_token")
            self._user = datos.get("user", {})
            self._online = True
            self._guardar_sesion()
            logger.info("Autenticacion exitosa: %s", self._user.get("email", "?"))
            return True
        except requests.RequestException as e:
            logger.warning("Error de red en autenticacion: %s", e)
            self.loginError.emit(str(e))
            return False

    def login_sync(self) -> bool:
        """Bloqueante — para casos donde no hay Qt loop."""
        verifier, challenge = _pkce_pair()
        puerto = _puerto_libre()
        redirect = f"http://127.0.0.1:{puerto}"
        auth_url = (
            f"{SUPABASE_URL}/auth/v1/authorize"
            f"?provider=google"
            f"&redirect_to={redirect}"
            f"&response_type=code"
            f"&code_challenge={challenge}"
            f"&code_challenge_method=s256"
            f"&scope=email%20profile"
        )
        webbrowser.open(auth_url)
        codigo = _obtener_codigo_oauth(puerto)
        if not codigo:
            return False
        return self._exchange_code(codigo, verifier)

    def logout(self) -> None:
        if self._access_token:
            try:
                requests.post(
                    f"{SUPABASE_URL}/auth/v1/logout",
                    headers={
                        "apikey": SUPABASE_ANON_KEY,
                        "Authorization": f"Bearer {self._access_token}",
                    },
                    timeout=5,
                )
            except requests.RequestException as e:
                logger.warning("Error en logout: %s", e)
        self._limpiar_sesion()
        logger.info("Sesion cerrada")

    def is_logged_in(self) -> bool:
        return self._online and self._access_token is not None

    def get_user(self) -> Optional[Dict[str, Any]]:
        return self._user

    def get_nombre(self) -> str:
        if not self._user:
            return "Desconectado"
        meta = self._user.get("user_metadata", {})
        return meta.get("full_name") or self._user.get("email", "Usuario")

    def compartir_subtitulo_simple(self, hash: str, nombre: str, contenido: str) -> bool:
        """Simple sharing: hash + name + content (no video context)."""
        if not self.is_logged_in():
            logger.warning("No autenticado para compartir")
            return False
        try:
            safe_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", f"{nombre}.srt")
            filename = f"{hash}_{safe_name}"

            self._ensure_profile()

            storage_resp = requests.post(
                f"{SUPABASE_URL}/storage/v1/object/subtitle-files/{filename}",
                headers={
                    "Authorization": f"Bearer {self._access_token}",
                    "Content-Type": "application/x-subrip",
                },
                data=contenido.encode("utf-8"),
                timeout=30,
            )
            upload_ok = storage_resp.status_code in (200, 201)
            if not upload_ok and storage_resp.status_code == 400:
                try:
                    upload_ok = storage_resp.json().get("error") == "Duplicate"
                except (ValueError, KeyError):
                    pass
            if not upload_ok:
                logger.warning("Error al subir SRT: %s", storage_resp.text)
                return False

            user_id = (self._user or {}).get("id", "")
            db_resp = requests.post(
                f"{SUPABASE_URL}/rest/v1/subtitles",
                headers=self._headers_auth(),
                json={
                    "file_hash": hash,
                    "filename": filename,
                    "language": "es",
                    "version": 1,
                    "user_id": user_id,
                },
                timeout=10,
            )
            if db_resp.status_code not in (200, 201):
                logger.warning("Error al registrar subtitulo: %s", db_resp.text)
                return False
            logger.info("Subtitulo compartido: %s", filename)
            return True
        except requests.RequestException as e:
            logger.warning("Error de red al compartir: %s", e)
            return False

    # ── API Comunidad ────────────────────────────────────────

    def _headers_auth(self) -> dict:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "apikey": SUPABASE_ANON_KEY,
            "Content-Type": "application/json",
        }

    def _ensure_profile(self) -> bool:
        uid = (self._user or {}).get("id")
        if not uid:
            return False
        try:
            headers = self._headers_auth()
            headers["Prefer"] = "resolution=merge-duplicates"
            resp = requests.post(
                f"{SUPABASE_URL}/rest/v1/profiles",
                headers=headers,
                json={"id": uid, "display_name": self.get_nombre()},
                timeout=10,
            )
            return resp.status_code in (200, 201, 409)
        except requests.RequestException as e:
            logger.debug("Error al crear perfil: %s", e)
            return False

    def _obtener_ultima_version(self, video_hash: str, idioma: str) -> int:
        uid = (self._user or {}).get("id", "")
        if not uid:
            return 0
        try:
            resp = requests.get(
                f"{SUPABASE_URL}/rest/v1/subtitles",
                headers=self._headers_auth(),
                params={
                    "file_hash": f"eq.{video_hash}",
                    "language": f"eq.{idioma}",
                    "user_id": f"eq.{uid}",
                    "select": "version",
                    "order": "version.desc",
                    "limit": 1,
                },
                timeout=10,
            )
            if resp.status_code == 200 and resp.json():
                return resp.json()[0]["version"]
        except requests.RequestException:
            pass
        return 0

    def compartir_subtitulo(
        self,
        ruta_srt: Path,
        video_hash: str,
        video_nombre: str,
        duracion_seg: float,
        tamano_bytes: int,
        idioma: str = "es",
        es_revision_manual: bool = False,
        word_count: int = 0,
        avg_confidence: float = 0.0,
        # NUEVOS metadatos de normalizacion (todos opcionales)
        season: Optional[int] = None,
        episode: Optional[int] = None,
        year: Optional[int] = None,
        title_clean: Optional[str] = None,
        resolution: Optional[str] = None,
        fps: Optional[float] = None,
        bitrate: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        video_codec: Optional[str] = None,
        audio_codec: Optional[str] = None,
        container: Optional[str] = None,
        release_group: Optional[str] = None,
        source_type: Optional[str] = None,
        parse_confidence: Optional[float] = None,
        normalization_version: Optional[str] = None,
    ) -> bool:
        if not self.is_logged_in():
            logger.warning("No autenticado para compartir")
            return False
        if not ruta_srt.exists():
            logger.warning("SRT no encontrado: %s", ruta_srt)
            return False
        try:
            safe_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", ruta_srt.name)
            filename = f"{video_hash}_{safe_name}"
            content_type = "application/x-subrip"

            self._ensure_profile()

            with open(ruta_srt, "rb") as f:
                storage_resp = requests.post(
                    f"{SUPABASE_URL}/storage/v1/object/subtitle-files/{filename}",
                    headers={
                        "Authorization": f"Bearer {self._access_token}",
                        "Content-Type": content_type,
                    },
                    data=f.read(),
                    timeout=30,
                )
            upload_ok = storage_resp.status_code in (200, 201)
            if not upload_ok and storage_resp.status_code == 400:
                try:
                    upload_ok = storage_resp.json().get("error") == "Duplicate"
                except (ValueError, KeyError):
                    pass
            if not upload_ok:
                logger.warning("Error al subir SRT: %s", storage_resp.text)
                return False

            version = self._obtener_ultima_version(video_hash, idioma) + 1
            user_id = (self._user or {}).get("id", "")

            json_data: Dict[str, Any] = {
                "file_hash": video_hash,
                "filename": filename,
                "language": idioma,
                "duration_sec": duracion_seg,
                "file_size": tamano_bytes,
                "original_video_name": video_nombre,
                "version": version,
                "is_manual_revision": es_revision_manual,
                "word_count": word_count,
                "avg_confidence": avg_confidence,
                "source": "whisper" if not es_revision_manual else "manual",
                "user_id": user_id,
            }
            for k, v in [
                ("season", season), ("episode", episode), ("year", year),
                ("title_clean", title_clean), ("resolution", resolution),
                ("fps", fps), ("bitrate", bitrate),
                ("width", width), ("height", height),
                ("video_codec", video_codec), ("audio_codec", audio_codec),
                ("container", container), ("release_group", release_group),
                ("source_type", source_type), ("parse_confidence", parse_confidence),
                ("normalization_version", normalization_version),
            ]:
                if v is not None:
                    json_data[k] = v

            db_resp = requests.post(
                f"{SUPABASE_URL}/rest/v1/subtitles",
                headers=self._headers_auth(),
                json=json_data,
                timeout=10,
            )
            if db_resp.status_code not in (200, 201):
                logger.warning("Error al registrar subtitulo: %s", db_resp.text)
                return False
            logger.info("Subtitulo compartido: %s (v%d)", filename, version)
            return True
        except requests.RequestException as e:
            logger.warning("Error de red al compartir: %s", e)
            return False

    def buscar_por_hash(
        self,
        video_hash: str,
        idioma: str = "es",
        duracion_seg: float = 0.0,
        tolerancia_seg: float = 3.0,
    ) -> list:
        try:
            params = {
                "file_hash": f"eq.{video_hash}",
                "language": f"eq.{idioma}",
                "status": "eq.published",
                "select": (
                    "id,filename,language,duration_sec,file_size,original_video_name,"
                    "download_count,version,is_manual_revision,avg_confidence,word_count,user_id,created_at"
                ),
                "order": "version.desc,download_count.desc",
            }
            resp = requests.get(
                f"{SUPABASE_URL}/rest/v1/subtitles",
                headers=self._headers_auth(),
                params=params,
                timeout=10,
            )
            if resp.status_code == 200:
                results: list = resp.json()
                if duracion_seg > 0 and tolerancia_seg > 0:
                    results = [
                        r
                        for r in results
                        if abs((r.get("duration_sec") or 0) - duracion_seg) <= tolerancia_seg
                    ]
                return results
            logger.warning("buscar_por_hash: status=%d", resp.status_code)
        except requests.RequestException as e:
            logger.warning("Error al buscar subtitulos: %s", e)
        return []

    def descargar_subtitulo(self, subtitle_id: str, destino: Path) -> bool:
        if not self.is_logged_in():
            logger.warning("No autenticado para descargar")
            return False
        try:
            registro = requests.get(
                f"{SUPABASE_URL}/rest/v1/subtitles",
                headers=self._headers_auth(),
                params={"id": f"eq.{subtitle_id}", "select": "filename", "limit": 1},
                timeout=10,
            )
            if registro.status_code != 200 or not registro.json():
                return False
            filename = registro.json()[0]["filename"]
            storage_resp = requests.get(
                f"{SUPABASE_URL}/storage/v1/object/subtitle-files/{filename}",
                headers={
                    "Authorization": f"Bearer {self._access_token}",
                    "apikey": SUPABASE_ANON_KEY,
                },
                timeout=30,
            )
            if storage_resp.status_code != 200:
                logger.warning("Error al descargar SRT: %s", storage_resp.text)
                return False
            write_binary(destino, storage_resp.content)
            requests.post(
                f"{SUPABASE_URL}/rest/v1/subtitle_downloads",
                headers=self._headers_auth(),
                json={
                    "subtitle_id": subtitle_id,
                    "user_id": (self._user or {}).get("id", ""),
                },
                timeout=10,
            )
            logger.info("Subtitulo descargado: %s -> %s", filename, destino)
            return True
        except requests.RequestException as e:
            logger.warning("Error al descargar subtitulo: %s", e)
            return False

    def obtener_estadisticas(self) -> dict:
        try:
            resp = requests.get(
                f"{SUPABASE_URL}/rest/v1/subtitles",
                headers={
                    "apikey": SUPABASE_ANON_KEY,
                    "Content-Type": "application/json",
                },
                params={"select": "id,download_count,created_at"},
                timeout=10,
            )
            if resp.status_code == 200:
                datos: list = resp.json()
                return {
                    "total": len(datos),
                    "descargas": sum(d.get("download_count", 0) for d in datos),
                }
        except requests.RequestException as e:
            logger.warning("Error obteniendo estadisticas: %s", e)
        return {"total": 0, "descargas": 0}


CLIENTE = SupabaseClient()
