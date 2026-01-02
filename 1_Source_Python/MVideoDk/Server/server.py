# ==========================================================
# Server/server.py  ✅ v20 — Servidor central + Worker (lifespan)
# ==========================================================
"""
Servidor central de MVideoDk — API + control de descargas.

Características:
- Configuración dinámica vía AppConfig (host, puerto, etc.).
- Worker dedicado para procesar la cola de descargas.
- Autenticación global por token (HTTP Bearer).
- CORS habilitado para clientes externos (GUI, extensión, móvil).
- Uso de lifespan en lugar de @app.on_event para startup/shutdown.
"""

import threading
import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from Server.api_routes import router as api_router
from Server.database import Database
from Server.downloader import Downloader
from Server.security import verify_token
from Core.paths import ensure_dirs
from Core.logger import LoggerFactory
from Core.app_config import AppConfig


# ==========================================================
# ⚙️ Configuración base (AppConfig)
# ==========================================================
cfg = AppConfig()
cfg.initialize()
ensure_dirs()

logger = LoggerFactory.get_logger("SERVER")
security = HTTPBearer()  # Para Swagger / Authorize

SERVER_NAME = cfg.get("server", "name", fallback="MVideoDk Central Server")
SERVER_URL = cfg.get_server_url()
logger.info(f"✅ Servidor configurado: {SERVER_NAME} ({SERVER_URL})")


# ==========================================================
# 🧵 Worker central de descargas
# ==========================================================
class Worker:
    """
    Encapsula el hilo de trabajo que consume la cola de descargas.

    - Lee tareas PENDING desde la base de datos.
    - Ejecuta descargas mediante Downloader (yt-dlp / Douyin, etc.).
    - Soporta pausa, reanudación y cancelación de la tarea actual.
    """

    def __init__(self):
        self.db = Database()
        self.downloader = Downloader()

        self.thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.cancel_current_event = threading.Event()

        self.current_task_id: int | None = None
        self.active = False
        self.restart_in_progress = False

    # ------------------------------------------------------
    # 🚀 Control de ciclo de vida del hilo
    # ------------------------------------------------------
    def start(self) -> None:
        """Inicia el hilo principal si no está ya corriendo."""
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.pause_event.clear()
        self.cancel_current_event.clear()

        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()
        self.active = True
        logger.info("🟢 DownloaderWorker iniciado correctamente.")

    def loop(self) -> None:
        """Bucle principal que consume la cola de tareas."""
        self.db.clean_stuck_tasks()

        while not self.stop_event.is_set():
            try:
                # Pausa: no tomar nuevas tareas
                if self.pause_event.is_set():
                    time.sleep(1)
                    continue

                task = self.db.get_next_pending()
                if not task:
                    time.sleep(2)
                    continue

                self.current_task_id = task[0]
                self.cancel_current_event.clear()

                logger.info(f"⬇️ Iniciando descarga #{self.current_task_id}")
                self.downloader.run(task, cancel_event=self.cancel_current_event)
                logger.info(f"✅ Descarga #{self.current_task_id} finalizada")

            except Exception as e:
                logger.error(f"Error en loop del worker: {e}")
                time.sleep(3)
            finally:
                self.current_task_id = None

        logger.info("🔴 Worker detenido (loop finalizado).")

    def pause(self) -> None:
        """Detiene la toma de nuevas tareas (las actuales terminan)."""
        self.pause_event.set()
        logger.info("🟠 Worker en pausa (no tomará nuevas tareas).")

    def resume(self) -> None:
        """Permite nuevamente tomar tareas PENDING de la cola."""
        self.pause_event.clear()
        logger.info("🔵 Worker reanudado.")

    def cancel_current(self) -> bool:
        """
        Solicita cancelación de la descarga en curso.
        Devuelve True si había tarea activa, False en caso contrario.
        """
        if self.current_task_id is not None:
            self.cancel_current_event.set()
            logger.info(f"🛑 Cancelación solicitada para #{self.current_task_id}")
            return True
        return False

    def restart(self) -> None:
        """
        Reinicia tareas DOWNLOADING → PENDING.
        Útil al arrancar o tras un fallo.
        """
        self.db.clean_stuck_tasks()
        logger.info("♻️ Cola reiniciada: tareas DOWNLOADING marcadas como PENDING.")

    def stop(self) -> None:
        """Detiene el bucle del worker (usado en shutdown del servidor)."""
        self.stop_event.set()
        self.active = False
        logger.info("🔴 Señal de parada enviada al Worker.")


# Instancia global del Worker
worker = Worker()


# ==========================================================
# 🔒 Autenticación global (Bearer)
# ==========================================================
def auth_required(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> bool:
    """
    Dependencia global para proteger rutas con Bearer Token.
    Lanza HTTP 401 si el token no es válido.
    """
    token = credentials.credentials
    if not verify_token(token):
        logger.warning("❌ Intento de acceso no autorizado")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autorizado",
        )
    return True


# ==========================================================
# 🌐 Lifespan (startup / shutdown)
# ==========================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión de ciclo de vida de la aplicación FastAPI."""
    # === Startup ===
    logger.info("🧩 Inicializando servidor y worker principal (lifespan)...")
    worker.start()

    yield  # El servidor se ejecuta mientras estamos aquí

    # === Shutdown ===
    worker.stop()
    logger.info("🛑 Servidor detenido correctamente (lifespan).")


# ==========================================================
# 🚀 Creación de la app FastAPI
# ==========================================================
def create_app() -> FastAPI:
    app = FastAPI(
        title=SERVER_NAME,
        description=(
            "Servidor centralizado de descargas – control de tareas, "
            "autenticación y puente para GUI/extensión."
        ),
        version="20.0",
        lifespan=lifespan,
    )

    # CORS global (permitir GUI, extensión, móvil, etc.)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------
    # 🧱 Manejador global de excepciones
    # ------------------------------------------------------
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """
        Manejador global de errores no capturados.

        - Respeta HTTPException (reenvía status y detail).
        - Cualquier otro error → 500 con mensaje genérico.
        """
        if isinstance(exc, HTTPException):
            # Dejar que la semántica HTTP se mantenga
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail},
            )

        logger.error(f"Unhandled error: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Error"},
        )

    # Rutas principales de API
    app.include_router(api_router)

    # ------------------------------------------------------
    # 🎛️ Endpoints de control del Worker / Cola
    # ------------------------------------------------------
    @app.post("/api/control")
    async def control_proxy(request: Request, auth: bool = Depends(auth_required)):
        """
        Control directo del worker y de la cola.

        Acciones soportadas:
            - pause_worker
            - resume_worker
            - restart_worker  (DOWNLOADING → PENDING)
            - cancel_current
            - restart_all     (borra cola y contadores)
        """
        body = await request.json()
        action = body.get("action")

        if action == "pause_worker":
            worker.pause()
            return {"detail": "🟠 Worker pausado.", "worker_paused": True}

        if action == "resume_worker":
            worker.resume()
            return {"detail": "🔵 Worker reanudado.", "worker_paused": False}

        if action == "restart_worker":
            worker.restart()
            return {
                "detail": "♻️ Cola reiniciada.",
                "worker_paused": worker.pause_event.is_set(),
            }

        if action == "cancel_current":
            if worker.cancel_current():
                return {"detail": "🛑 Descarga actual cancelada."}
            raise HTTPException(status_code=409, detail="No hay tarea en ejecución")

        if action == "restart_all":
            # Reinicio fuerte: limpia tareas + contadores
            try:
                logger.info(
                    "🧨 Reinicio TOTAL de cola solicitado "
                    "(borrado completo y reinicio de contadores)."
                )

                worker.restart_in_progress = True
                worker.pause()

                db = Database()
                db.reset_tasks_and_ids()
                db.reset_counters()

                # Intentar cancelar si justo estaba ejecutando algo
                worker.cancel_current()
                worker.current_task_id = None
                worker.restart_in_progress = False
                worker.resume()

                msg = "🧨 Cola limpiada completamente y contadores reiniciados."
                logger.info(msg)
                return {"detail": msg}

            except Exception as e:
                worker.restart_in_progress = False
                logger.error(f"❌ Error durante restart_all: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Error en restart_all: {e}",
                )

        raise HTTPException(status_code=400, detail="Acción inválida o no soportada.")

    @app.get("/api/worker_state")
    async def worker_state(auth: bool = Depends(auth_required)):
        """
        Devuelve el estado básico del worker para la GUI:

        - worker_paused       → si está en pausa o no.
        - current_task_id     → id de tarea en curso (o None).
        - restart_in_progress → flag auxiliar para flujos avanzados.
        """
        return {
            "worker_paused": worker.pause_event.is_set(),
            "current_task_id": worker.current_task_id,
            "restart_in_progress": getattr(worker, "restart_in_progress", False),
        }

    return app


# ==========================================================
# 🏁 Ejecución local
# ==========================================================
app = create_app()


def run_server() -> None:
    """Arranca el servidor FastAPI usando configuración de AppConfig."""
    host = cfg.get_server_host()
    port = cfg.get_server_port()
    reload = cfg.getboolean("server", "reload", fallback=False)

    logger.info(f"🚀 Iniciando servidor FastAPI en {host}:{port} ...")
    uvicorn.run(app, host=host, port=port, reload=reload)


if __name__ == "__main__":
    run_server()
