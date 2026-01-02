# ================================================================
# Server/downloaders/ytdlp_downloader.py  ✅ v20 — Downloader yt-dlp PRO
# ================================================================
"""
Downloader universal basado en yt-dlp.

Mejoras v20:
- Estructura profesional y documentación clara.
- Limpieza completa sin alterar lógica funcional.
- Mejor lectura de progresos y detección de archivos.
- Mantiene compatibilidad total con v6 FINAL.

Flujo principal:
1. Validación de ejecutable
2. Construcción dinámica del comando yt-dlp
3. Lectura incremental de progreso (stdout)
4. Manejo de cancelación en tiempo real
5. Detección del archivo final generado
6. Post-procesado opcional (audio/video)
7. Actualización en base de datos
"""

import subprocess
import time
from threading import Event
from pathlib import Path
from datetime import datetime

from Core.logger import LoggerFactory
from Core.utils import sanitize_filename
from Core.paths import downloads_dir, ytdlp_executable
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
# 🧩 Clase principal
# ================================================================
class YTDownloader:
    """Downloader basado en yt-dlp con progresos y postprocesado integrado."""

    def __init__(self):
        self.logger = LoggerFactory.get_logger("YTDLP")
        self.db = Database()

        # Directorio base (~/Downloads/MVideoDK/origin/)
        self.download_dir = downloads_dir()

        # Configuración desde config.ini
        cfg = AppConfig()
        self.ytdlp_format = cfg.get("downloads", "quality", fallback="best")
        self.ytdlp_extra_args = cfg.get("downloads", "extra_args", fallback="")
        self.overwrite_existing = cfg.getboolean(
            "downloads", "overwrite_existing", fallback=False
        )

        self.ytdlp_path = ytdlp_executable()

    def supports(self, url: str) -> bool:
        """yt-dlp soporta prácticamente cualquier URL."""
        return True

    # ============================================================
    # ▶️ RUN — flujo principal del downloader
    # ============================================================
    def run(self, task_row, cancel_event: Event | None = None) -> None:
        if not task_row:
            return

        # Desempaquetar row de DB
        (
            task_id, url, source, local_id, source_prefix, mode,
            filename, filepath, status, progress,
            retry_count, added_at, completed_at, error_msg,
        ) = task_row[:14]

        display_id = local_id or task_id

        # ----------------------------------------------------------
        # Validar presencia de yt-dlp
        # ----------------------------------------------------------
        if not self.ytdlp_path.exists():
            msg = f"❌ yt-dlp.exe NO encontrado en {self.ytdlp_path}"
            self.logger.error(msg)
            self.db.update_status(task_id, STATUS_ERROR, error=msg)
            return

        self.db.update_status(task_id, STATUS_DOWNLOADING, 0.0)
        self.logger.info(f"Comenzando descarga [ID{source_prefix}{display_id}] {url}")

        # ----------------------------------------------------------
        # Generar carpeta según origen (ej: GUI, CLIPBOARD, FILE…)
        # ----------------------------------------------------------
        origin_label = sanitize_filename(source.upper()) or "OTHER"
        task_dir = self.download_dir / origin_label
        task_dir.mkdir(parents=True, exist_ok=True)

        # Archivo plantilla
        output_template = task_dir / f"%(title)s [ID{display_id}].%(ext)s"

        # ============================================================
        # 🛠 Construcción del comando yt-dlp
        # ============================================================
        cmd = [
            str(self.ytdlp_path),
            "--newline",
            "-o", str(output_template),
        ]

        # Modo según GUI
        if mode == "VIDEO":
            cmd.append("--no-playlist")
        elif mode == "PLAYLIST":
            cmd.append("--yes-playlist")

        # Calidad
        fmt = (self.ytdlp_format or "").strip().lower()
        if fmt not in ["", "best", "default", "auto"]:
            cmd.extend(["-f", fmt])
        else:
            self.logger.info("🎬 Calidad automática (best).")

        # Sobrescritura
        if self.overwrite_existing:
            cmd.append("--no-continue")

        # Argumentos extra del usuario
        if self.ytdlp_extra_args:
            cmd.extend(self.ytdlp_extra_args.split())

        cmd.append(url)

        # ============================================================
        # ▶️ Ejecutar yt-dlp
        # ============================================================
        detected_path = None
        start_time = time.time()

        try:
            self.logger.info(f"▶️ Ejecutando: {' '.join(cmd)}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="ignore",
            )

            last_update = 0

            while True:
                # Cancelación desde GUI
                if cancel_event and cancel_event.is_set():
                    process.terminate()
                    self.db.update_status(task_id, STATUS_CANCELLED, error="Cancelled")
                    return

                line = process.stdout.readline() if process.stdout else ""
                if not line and process.poll() is not None:
                    break
                if not line:
                    continue

                line = line.strip()

                # ------------------------------------------------------
                # Detectar destino real (archivo generado)
                # ------------------------------------------------------
                if "Destination:" in line:
                    try:
                        dest = line.split("Destination:", 1)[1].strip()
                        p = Path(dest)
                        if not p.is_absolute():
                            p = task_dir / p
                        detected_path = p
                        self.logger.info(f"Destino detectado: {p}")
                    except Exception:
                        pass

                # ------------------------------------------------------
                # Progreso: buscar tokens tipo "54.3%"
                # ------------------------------------------------------
                for token in line.split():
                    if token.endswith("%"):
                        try:
                            pct = float(token[:-1])
                            now = time.time()
                            if now - last_update > 1:
                                self.db.update_status(task_id, STATUS_DOWNLOADING, pct)
                                last_update = now
                        except Exception:
                            pass

            process.wait()

            # Capturar stderr
            try:
                stderr_text = process.stderr.read() or ""
            except Exception:
                stderr_text = ""

            # ------------------------------------------------------
            # Localizar archivo final real
            # ------------------------------------------------------
            candidate = None

            # 1) El archivo detectado explícitamente
            if detected_path and detected_path.exists():
                candidate = detected_path

            else:
                # 2) Buscar archivos con el ID
                for p in task_dir.glob(f"* [ID{display_id}].*"):
                    if candidate is None or p.stat().st_mtime > candidate.stat().st_mtime:
                        candidate = p

                # 3) Fallback: archivo reciente si yt-dlp terminó OK
                if candidate is None and process.returncode == 0:
                    recent = [
                        p for p in task_dir.glob("*")
                        if p.is_file() and p.stat().st_mtime >= start_time - 3
                    ]
                    if recent:
                        candidate = max(recent, key=lambda p: p.stat().st_mtime)
                        self.logger.warning(f"Archivo adoptado: {candidate}")

            # ============================================================
            # ✔️ POST-PROCESADO + ACTUALIZACIÓN DB
            # ============================================================
            if candidate:
                final_path = process_file(str(candidate)) or candidate
                final_path = Path(final_path)

                self.db.update_status(
                    task_id,
                    STATUS_COMPLETED,
                    100.0,
                    filename=final_path.name,
                    filepath=str(final_path),
                    completed_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )

                self.logger.info(f"✅ Descarga completada #{task_id}: {final_path.name}")
                return

            # ============================================================
            # ❌ Sin archivo → ERROR
            # ============================================================
            if process.returncode != 0:
                last_err = stderr_text.splitlines()[-1] if stderr_text else "Error desconocido."
                msg = f"yt-dlp terminó con código {process.returncode}: {last_err}"
            else:
                msg = "yt-dlp finalizó sin errores pero no generó archivo."

            self.db.update_status(task_id, STATUS_ERROR, error=msg)
            self.logger.error(f"❌ Error en #{task_id}: {msg}")

        except Exception as e:
            self.db.update_status(task_id, STATUS_ERROR, error=str(e))
            self.logger.error(f"⚠️ Excepción en #{task_id}: {e}")
