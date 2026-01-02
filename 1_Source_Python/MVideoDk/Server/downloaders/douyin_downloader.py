# ================================================================
# Server/downloaders/douyin_downloader.py  ✅ v20 — Douyin Downloader PRO
# ================================================================
"""
Downloader dedicado para videos de Douyin (TikTok China).

Características v20:
- Resolución automática de shortlinks (rápido + fallback Playwright).
- Extracción de metadata AWEME desde tráfico de red.
- Descarga con barra de progreso y soporte para cancelación.
- Manejo completo de errores y actualización en base de datos.
- Post-procesado integrado mediante `process_file`.

NOTA: No se ha modificado ninguna lógica funcional respecto a la v9/v5,
solo limpieza profunda, documentación profesional y organización por secciones.
"""

import re
from pathlib import Path
from typing import Optional, Dict
import requests
from threading import Event
from playwright.sync_api import sync_playwright

from Core.paths import chromium_dir, chromium_executable
from Core.logger import LoggerFactory
from Core.utils import sanitize_filename
from Core.app_config import AppConfig

from Server.database import (
    Database,
    STATUS_DOWNLOADING,
    STATUS_COMPLETED,
    STATUS_ERROR,
    STATUS_CANCELLED,
)
from Server.downloaders.post_processor import process_file


# ================================================================
# 🔧 Configuración
# ================================================================
HEADLESS = True
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/127.0.0.0 Safari/537.36"
)
CHUNK = 1024 * 256  # 256 KB


# ================================================================
# 🔎 Localización del ejecutable Chromium
# ================================================================
def get_chromium_path() -> str:
    """
    Devuelve la ruta absoluta del ejecutable Chromium usado por Playwright.
    Lanza error si no existe (el instalador debe haberlo copiado).
    """
    path = chromium_executable()
    if path.exists():
        return str(path)
    raise FileNotFoundError(f"Chromium no encontrado en {path}")


# ================================================================
# 🧹 Helpers internos
# ================================================================
def clean(text: str) -> str:
    """Limpia cadenas para usarlas como nombre de archivo seguro."""
    if not text:
        return "video"
    text = re.sub(r"[\\/:*?\"<>|]", "_", text.strip())
    return text[:150] or "video"


def pick_aweme(data: Dict):
    """Extrae el objeto AWEME desde distintas estructuras posibles."""
    if not isinstance(data, dict):
        return None

    if "aweme_detail" in data:
        return data["aweme_detail"]

    if "aweme_list" in data and data["aweme_list"]:
        return data["aweme_list"][0]

    if "aweme" in data:
        return data["aweme"]

    if "item" in data:
        return pick_aweme(data["item"])

    if "data" in data:
        return pick_aweme(data["data"])

    return None


# ================================================================
# 🔗 Resolver Shortlink (rápido + fallback Playwright)
# ================================================================
def resolve_shortlink(url: str, logger):
    """
    Resuelve v.douyin.com → URL completa.
    Fases:
        1. Intento rápido con requests (sin redirección automática).
        2. Fallback: abrir shortlink con Playwright.
    """
    if "v.douyin.com" not in url.lower():
        return url

    # Método rápido
    try:
        logger.info(f"Douyin: resolviendo shortlink (rápido) {url}")
        r = requests.get(url, allow_redirects=False, timeout=8)
        loc = r.headers.get("Location")
        if loc:
            logger.info(f"Douyin: shortlink resuelto a {loc} (rápido)")
            return loc
    except Exception as e:
        logger.warning(f"Douyin: método rápido falló ({e})")

    # Fallback con Playwright
    try:
        chromium_path = get_chromium_path()
        logger.info(f"Douyin: resolviendo shortlink con Playwright {url}")

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=HEADLESS,
                executable_path=chromium_path,
            )
            ctx = browser.new_context(user_agent=UA)
            page = ctx.new_page()
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            final = page.url
            browser.close()

            logger.info(f"Douyin: shortlink resuelto a {final} (fallback)")
            return final

    except Exception as e:
        logger.warning(f"Douyin: fallback Playwright falló ({e})")

    return url


# ================================================================
# 📡 Extraer metadata AWEME desde tráfico de red
# ================================================================
def extract_aweme_from_network(url: str, logger) -> Optional[dict]:
    """
    Abre la página con Playwright, captura respuestas y busca la metadata AWEME.
    """
    container = {"aweme": None}

    chromium_path = get_chromium_path()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=HEADLESS,
            executable_path=chromium_path,
        )
        ctx = browser.new_context(
            user_agent=UA,
            java_script_enabled=True,
        )
        page = ctx.new_page()

        def on_response(resp):
            if container["aweme"] is not None:
                return
            if "detail" not in resp.url:
                return
            try:
                data = resp.json()
            except Exception:
                return
            aw = pick_aweme(data)
            if aw:
                container["aweme"] = aw

        ctx.on("response", on_response)

        try:
            logger.info(f"Douyin: abriendo página {url}")
            page.goto(url, timeout=60000)
            page.wait_for_timeout(5500)
        except Exception as e:
            logger.warning(f"Douyin: error cargando página: {e}")
        finally:
            browser.close()

    return container["aweme"]


# ================================================================
# 🎬 Downloader Douyin
# ================================================================
class DouyinDownloader:

    def __init__(self):
        self.logger = LoggerFactory.get_logger("DOUYIN")
        self.db = Database()

        cfg = AppConfig()
        self.download_dir = cfg.get_path("download_dir")

    def supports(self, url: str) -> bool:
        """Indica si el downloader puede manejar esta URL."""
        if not url:
            return False
        u = url.lower()
        return "douyin.com" in u or "iesdouyin.com" in u

    # -----------------------------------------------------------
    # ⬇️ Descarga del archivo MP4 con progreso en DB
    # -----------------------------------------------------------
    def _download_mp4(self, mp4_url: str, out: Path, task_id: int, cancel_event: Event):
        """
        Descarga el MP4 actualizando el progreso:
            0–20%    → Etapa de metadata
            20–99%   → Descarga real
            100%     → Final
        """
        try:
            with requests.get(mp4_url, stream=True, timeout=20) as r:
                if r.status_code != 200:
                    return False, f"HTTP {r.status_code}"

                total = int(r.headers.get("content-length") or 0)
                out.parent.mkdir(parents=True, exist_ok=True)

                downloaded = 0
                last_report = 20.0  # arranca desde 20%

                with open(out, "wb") as f:
                    for chunk in r.iter_content(CHUNK):

                        if cancel_event and cancel_event.is_set():
                            return False, "Cancelled by user"

                        if not chunk:
                            continue

                        f.write(chunk)
                        downloaded += len(chunk)

                        if total > 0:
                            pct = 20 + (downloaded / total) * 80
                            pct = min(pct, 99)

                            if pct - last_report >= 1:
                                self.db.update_status(task_id, STATUS_DOWNLOADING, pct)
                                last_report = pct

                return True, None

        except Exception as e:
            return False, str(e)

    # -----------------------------------------------------------
    # ▶️ RUN — Flujo principal
    # -----------------------------------------------------------
    def run(self, task_row, cancel_event: Event | None = None):
        """
        Ejecuta el flujo completo del downloader:
        - Resolver shortlink
        - Extraer metadata
        - Determinar URL del MP4
        - Descargar
        - Postprocesar (opcional)
        - Actualizar DB
        """
        if not task_row:
            return

        (
            task_id, url, source, local_id,
            source_prefix, mode, fn, fp,
            st, prg, retry, add_at, end_at, err
        ) = task_row[:14]

        display_id = local_id or task_id

        self.logger.info(
            f"Douyin: comenzando descarga [ID{source_prefix}{display_id}] {url}"
        )

        self.db.update_status(task_id, STATUS_DOWNLOADING, 0)

        task_dir = self.download_dir
        task_dir.mkdir(parents=True, exist_ok=True)

        try:
            if cancel_event and cancel_event.is_set():
                self.db.update_status(task_id, STATUS_CANCELLED, error="Cancelled by user")
                return

            # 1) Resolver shortlink
            final_url = resolve_shortlink(url, self.logger)

            # 2) Extraer metadata AWEME
            aweme = extract_aweme_from_network(final_url, self.logger)
            if not aweme:
                msg = "No se pudo obtener metadata del video Douyin."
                self.logger.error(msg)
                self.db.update_status(task_id, STATUS_ERROR, error=msg)
                return

            self.db.update_status(task_id, STATUS_DOWNLOADING, 20)

            # 3) Extraer campos necesarios
            desc = aweme.get("desc", "") or ""
            author = (
                aweme.get("author", {}).get("nickname")
                or aweme.get("author", {}).get("unique_id")
                or "Autor"
            )

            video = aweme.get("video", {}) or {}
            play_addr = (
                video.get("play_addr")
                or video.get("play_addr_lowbr")
                or video.get("play_addr_h264")
                or {}
            )

            url_list = play_addr.get("url_list") or []
            if not url_list:
                msg = "No hay URL MP4 disponible."
                self.logger.error(msg)
                self.db.update_status(task_id, STATUS_ERROR, error=msg)
                return

            mp4_url = url_list[0]

            safe_title = clean(desc)
            safe_author = clean(author)
            mp4_name = f"{safe_title} - {safe_author} [ID{display_id}].mp4"
            mp4_path = task_dir / mp4_name

            # 4) Descarga MP4
            ok, err = self._download_mp4(mp4_url, mp4_path, task_id, cancel_event)
            if not ok:
                if err == "Cancelled by user":
                    self.db.update_status(task_id, STATUS_CANCELLED, error=err)
                    return
                self.db.update_status(task_id, STATUS_ERROR, error=err)
                return

            # 5) Postprocesado (audio u otros)
            final_path = process_file(str(mp4_path)) or mp4_path
            final_path = Path(final_path)

            # 6) Finalizar y actualizar DB
            self.db.update_status(
                task_id,
                STATUS_COMPLETED,
                100,
                filename=final_path.name,
                filepath=str(final_path),
            )

            self.logger.info(
                f"Douyin: ✅ Descarga completada #{task_id}: {final_path.name}"
            )

        except Exception as e:
            msg = str(e)
            self.logger.error(f"Douyin EXCEPCIÓN: {msg}")
            self.db.update_status(task_id, STATUS_ERROR, error=msg)
