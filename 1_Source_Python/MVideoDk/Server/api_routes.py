# ==========================================================
# Server/api_routes.py  ✅ v20 — Rutas principales de la API
# ==========================================================
"""
Rutas oficiales del servidor FastAPI de MVideoDK.

Incluye:
- Autenticación Bearer Token (Server/security)
- Inserción y consulta de tareas de descarga
- Exposición segura de estado y configuración
- Soporte para extensión del navegador (endpoint público)

Totalmente compatible con GUI, servidor y extensión actuales.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from Server.security import verify_token, get_token_digest
from Server.database import Database
from Core.logger import LoggerFactory
from Core.utils import is_valid_url
from Core.app_config import AppConfig
from Config.default_config import get_source_prefix  # Prefijos tipo “G”, “C”, etc.


# ==========================================================
# ⚙️ CONFIGURACIÓN GLOBAL DE API
# ==========================================================
cfg = AppConfig()
cfg.initialize()

logger = LoggerFactory.get_logger("API")
router = APIRouter(prefix="/api", tags=["MVideoDk API"])
security = HTTPBearer()
db = Database()

SERVER_NAME = cfg.get("server", "name", fallback="MVideoDk Central Server")
SERVER_URL = cfg.get_server_url()

logger.info(f"✅ API inicializada en {SERVER_URL}")


# ==========================================================
# 📦 MODELOS PYDANTIC
# ==========================================================
class QueueRequest(BaseModel):
    """Payload del POST /api/queue."""
    url: str
    source: str = "UNKNOWN"
    mode: Optional[str] = "VIDEO"  # VIDEO o PLAYLIST


class TaskItem(BaseModel):
    """Representación serializable de un registro de tarea."""
    id: int
    url: str
    status: str
    progress: float
    source: str
    added_at: str
    error_msg: Optional[str] = None
    retry_count: Optional[int] = None
    completed_at: Optional[str] = None
    filename: Optional[str] = None
    filepath: Optional[str] = None
    local_id: Optional[int] = None
    source_prefix: Optional[str] = None
    mode: Optional[str] = None


# ==========================================================
# 🔒 AUTENTICACIÓN BEARER
# ==========================================================
def auth_required(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> bool:
    """
    Dependencia global para proteger rutas con Bearer Token.
    Lanza 401 si el token es inválido.
    """
    token = credentials.credentials
    if not verify_token(token):
        logger.warning("Acceso no autorizado detectado en la API.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autorizado"
        )
    return True


# ==========================================================
# 🔎 PING / ESTADO DEL SERVIDOR
# ==========================================================
@router.get("/ping")
def ping():
    """Endpoint de vida de servidor (sin auth)."""
    digest = get_token_digest()
    return {
        "status": "ok",
        "server": SERVER_NAME,
        "server_url": SERVER_URL,
        "token_digest": (digest[:20] + "...") if digest else None,
    }


# ==========================================================
# 📥 ENCOLADO DE DESCARGAS
# ==========================================================
@router.post("/queue")
def enqueue(payload: QueueRequest, auth: bool = Depends(auth_required)):
    """
    Agrega una nueva tarea a la cola de descargas.

    Ejemplo JSON:
        {
            "url": "https://...",
            "source": "GUI",
            "mode": "VIDEO"
        }
    """
    logger.debug("🟡 /api/queue llamado")

    url = (payload.url or "").strip()
    source = (payload.source or "UNKNOWN").strip() or "UNKNOWN"
    mode = (payload.mode or "VIDEO").strip().upper()

    logger.debug(f"Payload recibido → url={url}, source={source}, mode={mode}")

    # Validación de modo
    if mode not in ("VIDEO", "PLAYLIST"):
        logger.warning(f"Modo inválido '{mode}', usando VIDEO.")
        mode = "VIDEO"

    # Validación de URL
    if not url:
        raise HTTPException(status_code=400, detail="URL requerida")
    if not is_valid_url(url):
        raise HTTPException(status_code=400, detail="URL inválida")

    # Prefijo de fuente
    source_prefix = get_source_prefix(source)

    # Insertar en DB
    try:
        task_id = db.add_task(url, source, mode)
    except Exception as e:
        logger.error(f"Error al agregar tarea: {e}")
        raise HTTPException(status_code=500, detail=f"Error DB: {e}")

    # Gestionar duplicados
    if task_id is None:
        logger.info("URL duplicada no agregada.")
        return {"detail": "Duplicado o ya en cola"}

    logger.info(
        f"Tarea encolada #{task_id} ({source_prefix}) desde {source}, mode={mode}"
    )
    return {"task_id": task_id, "detail": "OK"}


# ==========================================================
# 📊 ESTADO DE LA COLA (PAGINADO)
# ==========================================================
@router.get("/status")
def get_status(
    limit: int = 50,
    offset: int = 0,
    auth: bool = Depends(auth_required),
):
    """Devuelve tareas existentes en la cola, paginadas."""
    tasks = db.list_tasks(limit=limit, offset=offset)
    items: List[dict] = []

    for row in tasks:
        items.append({
            "id": row[0],
            "url": row[1],
            "status": row[2],
            "progress": row[3],
            "source": row[4],
            "added_at": row[5],
            "error_msg": row[6],
            "retry_count": row[7] if len(row) > 7 else None,
            "completed_at": row[8] if len(row) > 8 else None,
            "filename": row[9] if len(row) > 9 else None,
            "filepath": row[10] if len(row) > 10 else None,
            "local_id": row[11] if len(row) > 11 else None,
            "source_prefix": row[12] if len(row) > 12 else None,
            "mode": row[13] if len(row) > 13 else None,
        })

    return {"items": items}


# ==========================================================
# 🧮 CONTADORES POR FUENTE
# ==========================================================
@router.get("/counters")
def get_counters(auth: bool = Depends(auth_required)):
    """Devuelve el contador de IDs locales por fuente (GUI, EXT, MOBILE…)."""
    try:
        with db._connect() as conn:
            c = conn.cursor()
            c.execute("SELECT source, last_local_id FROM counters")
            rows = c.fetchall()
        return {
            "counters": [
                {"source": src, "last_local_id": lid}
                for src, lid in rows
            ]
        }
    except Exception as e:
        logger.error(f"Error consultando contadores: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


# ==========================================================
# 🔧 CONFIG PARA EXTENSIÓN DEL NAVEGADOR (NO REQUIERE AUTH)
# ==========================================================
@router.get("/ext/config")
def get_extension_config():
    """
    Devuelve la configuración mínima requerida por la extensión.
    No requiere token para ser consultado.
    """
    cfg = AppConfig()
    server_url = cfg.get_server_url()

    try:
        token = cfg.get_token_path().read_text(encoding="utf-8").strip()
    except Exception:
        token = ""

    return {
        "server_url": server_url,
        "scheme": cfg.get("server", "scheme"),
        "host": cfg.get("server", "host"),
        "port": cfg.get("server", "port"),
        "token": token,
    }
