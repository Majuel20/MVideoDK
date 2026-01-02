# ==========================================================
# main.py   ✅ v20 —  Unified Launcher (GUI + Servidor)
# ==========================================================
"""
Lanzador principal de MVideoDk:
- Inicia el servidor FastAPI en un hilo daemon.
- Espera que el servidor esté activo.
- Lanza la GUI en el hilo principal.
- No gestiona túneles: eso es responsabilidad de la GUI.

Compatible con ejecución normal y con PyInstaller (frozen).
"""

import threading
import time
import sys
import requests
from pathlib import Path
import uvicorn
from uvicorn import Config, Server

# ----------------------------------------------------------
# Ajuste dinámico de rutas según entorno (frozen / normal)
# ----------------------------------------------------------
if getattr(sys, "frozen", False):
    ROOT = Path(sys.executable).parent
else:
    ROOT = Path(__file__).resolve().parent

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "Core"))
sys.path.insert(0, str(ROOT / "Server"))
sys.path.insert(0, str(ROOT / "Client_GUI"))

from Core.app_config import AppConfig
from Core.logger import LoggerFactory
from Server.server import app as fastapi_app

logger = LoggerFactory.get_logger("MAIN")


# ==========================================================
# 🔥 Iniciar servidor en un hilo (daemon)
# ==========================================================
def server_thread_start() -> threading.Thread:
    """
    Lanza el servidor FastAPI dentro de un hilo daemon.
    Devuelve el objeto Thread.
    """
    cfg = AppConfig()
    host = cfg.get_server_host()
    port = cfg.get_server_port()

    def _run():
        uvconfig = Config(
            app=fastapi_app,
            host=host,
            port=port,
            reload=False,
            workers=1,
            log_level="info",
        )
        server = Server(uvconfig)
        server.run()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    logger.info(f"🚀 Servidor FastAPI lanzado en hilo daemon ({host}:{port})")
    return t


# ==========================================================
# 🕒 Esperar que el servidor arranque
# ==========================================================
def wait_for_server(url: str, timeout: int = 10) -> bool:
    """
    Intenta conectarse al servidor FastAPI hasta que responda.
    """
    logger.info(f"⏳ Esperando servidor en {url} (timeout={timeout}s)...")
    start = time.time()

    while time.time() - start < timeout:
        try:
            requests.get(url)
            logger.info("✔ Servidor respondió correctamente.")
            return True
        except Exception:
            time.sleep(0.4)

    logger.error("❌ El servidor no respondió dentro del tiempo.")
    return False


# ==========================================================
# 🧠 APP PRINCIPAL (GUI en hilo principal)
# ==========================================================
def main() -> None:
    logger.info("🚀 Iniciando MVideoDk Launcher...")

    cfg = AppConfig()
    cfg.ensure_dirs()

    server_url = cfg.get_server_url()

    # 1) Lanzar servidor FastAPI
    server_thread_start()

    # 2) Esperar al servidor
    if not wait_for_server(server_url, timeout=12):
        logger.error("❌ Abortando porque el servidor no está disponible.")
        return

    logger.info(f"✔ Servidor activo en {server_url}")

    # 3) Lanzar GUI (que también gestiona el túnel)
    try:
        from Client_GUI.mvideodk_main import run_gui
        run_gui()
    except Exception as e:
        logger.error(f"❌ Error al iniciar la GUI: {e}")
        return

    logger.info("🎨 GUI cerrada. Limpiando recursos...")

    # Nota: el túnel Cloudflare se gestiona en la GUI, no aquí.

    logger.info("🏁 MVideoDk finalizado.")
    sys.exit(0)


if __name__ == "__main__":
    main()
