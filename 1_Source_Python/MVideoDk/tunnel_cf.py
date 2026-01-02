# ==========================================================
# tunnel_cf.py   ✅ v20 —  Gestor del túnel Cloudflare para MVideoDk 
# ==========================================================
"""
Maneja la apertura y cierre del túnel Cloudflare (cloudflared)
para exponer públicamente el servidor FastAPI de MVideoDk.

- start_cloudflare_tunnel() → inicia el túnel y obtiene la URL pública.
- stop_cloudflare_tunnel()  → detiene el proceso activo.

No requiere modificaciones en otros módulos.
"""

import subprocess
import time
import re
from pathlib import Path

from Core.app_config import AppConfig
from Core.paths import data_dir, logs_dir, bin_dir
from Core.logger import LoggerFactory


logger = LoggerFactory.get_logger("TUNNEL")


# ==========================================================
# 🔚 DETENER TÚNEL — Seguro
# ==========================================================
def stop_cloudflare_tunnel(proc) -> None:
    """
    Detiene el proceso cloudflared de forma segura.

    Args:
        proc (subprocess.Popen | None): Proceso en ejecución.
    """
    if proc is None:
        return

    try:
        if proc.poll() is None:
            logger.info("🔻 Deteniendo túnel Cloudflare...")
            proc.terminate()
            time.sleep(0.3)

            if proc.poll() is None:
                logger.warning("⚠️ Terminación suave falló, forzando kill()")
                proc.kill()
    except Exception as e:
        logger.error(f"❌ Error deteniendo túnel: {e}")


# ==========================================================
# 🚀 INICIAR TÚNEL CLOUDFLARE
# ==========================================================
def start_cloudflare_tunnel():
    """
    Inicia un túnel Cloudflare hacia el servidor local de MVideoDk.

    Returns:
        tuple:
            (public_url:str | None, process:subprocess.Popen | None)
    """
    cfg = AppConfig()

    server_host = cfg.get_server_host()
    server_port = cfg.get_server_port()
    local_server_url = f"http://{server_host}:{server_port}"

    logger.info(f"🟦 Preparando túnel hacia: {local_server_url}")

    # ----------------------------------------------------------
    # Archivo de log del túnel
    # ----------------------------------------------------------
    tunnel_log_path = logs_dir() / "tunnel.log"

    try:
        tunnel_log_path.write_text("", encoding="utf-8")
    except Exception as e:
        logger.warning(f"⚠️ No se pudo inicializar el archivo de log: {e}")

    # ----------------------------------------------------------
    # Binario cloudflared
    # ----------------------------------------------------------
    cloudflared_path = bin_dir() / "cloudflared" / "cloudflared.exe"

    if not cloudflared_path.exists():
        logger.error(f"❌ cloudflared.exe NO encontrado en: {cloudflared_path}")
        return None, None

    cloudflared_cmd = [
        str(cloudflared_path),
        "tunnel",
        "--url", local_server_url,
        "--logfile", str(tunnel_log_path),
    ]

    # ----------------------------------------------------------
    # Lanzar proceso
    # ----------------------------------------------------------
    try:
        tunnel_process = subprocess.Popen(
            cloudflared_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        logger.info("⏳ Iniciando túnel Cloudflare...")
    except Exception as e:
        logger.error(f"❌ No se pudo iniciar cloudflared: {e}")
        return None, None

    # ----------------------------------------------------------
    # Leer URL pública desde el log (máx ~10 seg)
    # ----------------------------------------------------------
    tunnel_public_url = None

    for _ in range(40):
        try:
            if tunnel_log_path.exists():
                log_content = tunnel_log_path.read_text(errors="ignore")
                match = re.search(
                    r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com",
                    log_content,
                )
                if match:
                    tunnel_public_url = match.group(0)
                    break
        except Exception as e:
            logger.warning(f"⚠️ Error leyendo log del túnel: {e}")

        time.sleep(0.25)

    if not tunnel_public_url:
        logger.error("❌ No se pudo obtener la URL pública del túnel.")
        return None, tunnel_process

    logger.info(f"🌐 Túnel Cloudflare activo: {tunnel_public_url}")

    # ----------------------------------------------------------
    # Guardar URL en Data/cloudflare_url.txt
    # ----------------------------------------------------------
    try:
        output_path = data_dir() / "cloudflare_url.txt"
        output_path.write_text(tunnel_public_url, encoding="utf-8")
        logger.info(f"💾 URL guardada en: {output_path}")
    except Exception as e:
        logger.warning(f"⚠️ No se pudo guardar la URL pública: {e}")

    return tunnel_public_url, tunnel_process
