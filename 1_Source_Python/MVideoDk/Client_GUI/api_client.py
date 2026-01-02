# ==========================================================
# Client_GUI/api_client.py  ✅ v20 — Cliente REST GUI ↔ Servidor
# ==========================================================
"""
Cliente REST centralizado para la GUI de MVideoDk.

🚀 Mejoras v20:
- Código limpiado y unificado.
- Comentarios actualizados y más descriptivos.
- Encabezado de versión estandarizado.
- Eliminados prints innecesarios (solo logs).
- Se mantiene TODO el comportamiento original.

Funcionalidad:
- Lee configuración mediante AppConfig.
- Gestiona sesión HTTP reutilizable.
- Maneja reintentos y errores de red.
- Proporciona métodos REST de alto nivel para la GUI.
"""

from __future__ import annotations
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import requests
from requests import Response, Session

from Core.logger import LoggerFactory
from Core.app_config import AppConfig


# ==========================================================
# 🔧 Inicialización / Paths / Session
# ==========================================================

# ROOT dinámico compatible con PyInstaller
if getattr(sys, "frozen", False):
    ROOT_DIR = Path(sys.executable).parent
else:
    ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

log = LoggerFactory.get_logger("API_CLIENT")

# Cache global
_session: Optional[Session] = None
_cached_token: Optional[str] = None
_cached_base_url: Optional[str] = None
_last_alive_state: Optional[bool] = None


# ==========================================================
# ⚙️ Configuración (AppConfig)
# ==========================================================
def _cfg() -> AppConfig:
    """Instancia única de AppConfig (thread-safe)."""
    cfg = AppConfig()
    cfg.initialize()
    return cfg


def _token_path() -> Path:
    """Ruta del token.key según lo definido en AppConfig."""
    return Path(_cfg().get_token_path()).resolve()


def _load_token() -> str:
    """Lee el contenido de token.key; error si está vacío o no existe."""
    tpath = _token_path()
    if not tpath.exists():
        log.error(f"⚠️ token.key no encontrado en {tpath}")
        raise FileNotFoundError(f"token.key no encontrado en {tpath}")

    token = tpath.read_text(encoding="utf-8").strip()
    if not token:
        raise ValueError("token.key vacío o ilegible.")

    return token


def _get_base_url() -> str:
    """Devuelve la URL base del servidor (cacheada)."""
    global _cached_base_url
    if _cached_base_url is None:
        try:
            _cached_base_url = _cfg().get_server_url()
        except Exception as e:
            log.error(f"Error obteniendo URL del servidor: {e}")
            _cached_base_url = "http://127.0.0.1:8000"
    return _cached_base_url


def _get_session() -> Session:
    """Devuelve una sesión HTTP persistente (para reducir overhead)."""
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({"Accept": "application/json"})
    return _session


def _get_auth_headers() -> Dict[str, str]:
    """Cabecera Authorization: Bearer <token>."""
    global _cached_token
    if _cached_token is None:
        _cached_token = _load_token()
    return {"Authorization": f"Bearer {_cached_token}"}


# ==========================================================
# 🌐 Manejador general de peticiones
# ==========================================================
def _request_json(
    method: str,
    path: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    timeout_s: float = 8.0,
    retries: int = 2,
    backoff_s: float = 0.8,
    require_auth: bool = True,
) -> Tuple[bool, Any, int]:
    """
    Envía una petición HTTP al servidor y devuelve:
        (ok: bool, payload: Any, status_code: int)

    - ok=True si status 2xx.
    - Maneja errores de red, reintentos y respuestas no JSON.
    """
    url = _get_base_url().rstrip("/") + path
    sess = _get_session()
    headers: Dict[str, str] = {}

    if require_auth:
        headers.update(_get_auth_headers())

    for attempt in range(retries + 1):
        try:
            resp: Response = sess.request(
                method=method.upper(),
                url=url,
                params=params,
                json=json_body,
                headers=headers,
                timeout=timeout_s,
            )

            # 2xx
            if 200 <= resp.status_code < 300:
                try:
                    return True, resp.json(), resp.status_code
                except Exception:
                    return True, resp.text, resp.status_code

            # Auth rechazada
            if resp.status_code in (401, 403):
                log.warning(f"🚫 Auth rechazada en {path}: {resp.text}")
                return False, {"detail": "No autorizado"}, resp.status_code

            # Otros códigos
            try:
                data = resp.json()
            except Exception:
                data = {"detail": resp.text or "HTTP error"}

            log.warning(f"⚠️ HTTP {resp.status_code} → {data}")
            return False, data, resp.status_code

        except requests.exceptions.RequestException as e:
            log.warning(f"[Intento {attempt+1}] Falla de red en {path}: {e}")
            if attempt < retries:
                time.sleep(backoff_s * (attempt + 1))
            else:
                return False, {"detail": "Servidor no disponible"}, 0


# ==========================================================
# 🧠 API base
# ==========================================================
def ping() -> Tuple[bool, Any, int]:
    """Ping simple al servidor (sin autenticación)."""
    return _request_json("GET", "/api/ping", require_auth=False)


def is_server_alive(max_retries: int = 2, delay_s: float = 0.7) -> bool:
    """
    Realiza ping con reintentos y cachea el último estado.
    Útil para evitar spam de logs.
    """
    global _last_alive_state

    for attempt in range(max_retries + 1):
        ok, _, _ = ping()
        if ok:
            if _last_alive_state is not True:
                log.info("Servidor disponible nuevamente ✅")
            _last_alive_state = True
            return True

        time.sleep(delay_s * (attempt + 1))

    if _last_alive_state is not False:
        log.warning("Servidor inaccesible ❌ (tras reintentos)")

    _last_alive_state = False
    return False


# ==========================================================
# ✳️ Envío de URL
# ==========================================================
def send_url(url: str, source: str = "GUI", mode: str = "VIDEO") -> Any:
    """
    Envía una nueva tarea de descarga al servidor.
    mode:
        - "VIDEO"
        - "PLAYLIST"
    """
    ok, data, _ = _request_json(
        "POST",
        "/api/queue",
        json_body={"url": url, "source": source, "mode": mode},
    )
    if not ok:
        raise ConnectionError(data.get("detail", "Error desconocido"))
    return data


# ==========================================================
# 📋 Estado de tareas
# ==========================================================
def get_status(limit: int = 50, offset: int = 0) -> Any:
    """Obtiene listado extendido de tareas apto para la GUI."""
    ok, data, code = _request_json(
        "GET",
        "/api/status",
        params={"limit": limit, "offset": offset},
    )

    if not ok:
        log.warning(f"Error obteniendo estado ({code}): {data}")
        return []

    items = data.get("items", data) if isinstance(data, dict) else data
    if not isinstance(items, list):
        return []

    return [
        {
            "id": it.get("id"),
            "source_prefix": it.get("source_prefix"),
            "local_id": it.get("local_id"),
            "source": it.get("source"),
            "url": it.get("url"),
            "filename": it.get("filename"),
            "mode": (it.get("mode") or "VIDEO").upper(),
            "progress": it.get("progress", 0),
            "status": it.get("status", ""),
            "error_msg": it.get("error_msg", ""),
            "filepath": it.get("filepath", ""),
        }
        for it in items
    ]


# ==========================================================
# 🔧 Controles del worker
# ==========================================================
def send_control(action: str, task_id: Optional[int] = None) -> Any:
    """
    Envía órdenes administrativas al worker del servidor.
    Acciones:
        - pause_worker
        - resume_worker
        - restart_worker
        - cancel_current
        - restart_all
        - retry
        - delete
    """
    valid_actions = [
        "pause_worker",
        "resume_worker",
        "retry",
        "delete",
        "cancel_current",
        "restart_all",
        "restart_worker",
    ]

    if action not in valid_actions:
        raise ValueError(f"Acción '{action}' no soportada.")

    body: Dict[str, Any] = {"action": action}
    if task_id is not None:
        body["task_id"] = task_id

    ok, data, _ = _request_json("POST", "/api/control", json_body=body)
    if not ok:
        raise ConnectionError(data.get("detail", "Error en control"))
    return data


def worker_state() -> Any:
    """Devuelve el estado operacional del worker."""
    ok, data, _ = _request_json("GET", "/api/worker_state")
    if not ok:
        raise ConnectionError(data.get("detail", "Error al obtener estado del worker"))
    return data


# ==========================================================
# 🧩 Wrappers amigables para la GUI
# ==========================================================
def api_ping() -> bool:
    """Wrapper simple: True si el servidor responde al ping."""
    ok, _, _ = ping()
    return ok


def api_queue(url: str, source: str = "GUI", mode: str = "VIDEO"):
    """Wrapper GUI: devuelve (ok, mensaje)."""
    try:
        data = send_url(url, source, mode)
        msg = (
            data.get("detail", "URL encolada correctamente.")
            if isinstance(data, dict)
            else "URL encolada correctamente."
        )
        return True, msg
    except Exception as e:
        log.warning(f"api_queue falló: {e}")
        return False, str(e)


def api_status(limit: int = 50, offset: int = 0):
    """Wrapper GUI: devuelve (ok, lista | error)."""
    try:
        items = get_status(limit=limit, offset=offset)
        return True, items
    except Exception as e:
        log.warning(f"api_status falló: {e}")
        return False, str(e)


def api_control(action: str, task_id: Optional[int] = None):
    """Wrapper GUI: devuelve (ok, mensaje)."""
    try:
        data = send_control(action, task_id)
        msg = (
            data.get("detail", "Acción ejecutada correctamente.")
            if isinstance(data, dict)
            else "Acción ejecutada correctamente."
        )
        return True, msg
    except Exception as e:
        log.warning(f"api_control falló: {e}")
        return False, str(e)


def api_worker_state():
    """Wrapper GUI para estado del worker."""
    try:
        data = worker_state()
        return True, data
    except Exception as e:
        log.warning(f"api_worker_state falló: {e}")
        return False, str(e)
