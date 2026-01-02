# ================================================================
# Server/downloaders/post_processor.py  ✅ v20 — Post-procesador AUDIO/BOTH
# ================================================================
"""
Módulo de post-procesado para descargas:

Configuración válida desde [postprocess] en config.ini:
    enabled = true/false
    action  = audio | both
    audio_format = mp3/m4a/flac/wav
    audio_bitrate = 320k (u otros)

Reglas v20:
- NO existe action="none" ni "video".
- enabled = false  → se devuelve el video tal como está.
- action = audio   → se extrae audio y se elimina el video original.
- action = both    → se extrae audio y se mantiene el video.

El módulo:
- Valida presencia de ffmpeg y ffprobe.
- Ejecuta ffmpeg con parámetros adecuados al formato.
- Maneja errores y logs de manera clara.
"""

import subprocess
from pathlib import Path

from Core.logger import LoggerFactory
from Core.app_config import AppConfig
from Core.paths import ffmpeg_dir

# ---------------------------------------------------------------
# 🔧 Configuración e inicialización
# ---------------------------------------------------------------
log = LoggerFactory.get_logger("POSTPROCESS")

FFMPEG_BIN = ffmpeg_dir() / "ffmpeg.exe"
FFPROBE_BIN = ffmpeg_dir() / "ffprobe.exe"


# ================================================================
# 🔍 Verificación de FFmpeg
# ================================================================
def _check_ffmpeg():
    """
    Verifica que ffmpeg.exe y ffprobe.exe existan en la instalación.
    Lanza RuntimeError si alguno falta.
    """
    if not FFMPEG_BIN.exists():
        raise RuntimeError(f"FFmpeg no encontrado: {FFMPEG_BIN}")

    if not FFPROBE_BIN.exists():
        raise RuntimeError(f"ffprobe no encontrado: {FFPROBE_BIN}")


# ================================================================
# 🎧 PROCESAMIENTO PRINCIPAL
# ================================================================
def process_file(input_path: str) -> Path:
    """
    Procesa un archivo descargado según configuración del usuario.

    Estados permitidos:
      enabled = false → no se toca el archivo (solo video).
      action  = audio → genera audio y elimina el video.
      action  = both  → genera audio y conserva el video.

    Args:
        input_path (str): Ruta absoluta al archivo original.

    Returns:
        Path: Ruta del archivo final (audio o video según modo).
    """
    cfg = AppConfig()

    enabled = cfg.getboolean("postprocess", "enabled", fallback=False)
    action = cfg.get("postprocess", "action", fallback="audio").lower()
    audio_format = cfg.get("postprocess", "audio_format", fallback="mp3").lower()
    bitrate = cfg.get("postprocess", "audio_bitrate", fallback="320k")

    input_path = Path(input_path)

    # ---------------------------------------------------------
    # 🔕 POSTPROCESADO DESACTIVADO
    # ---------------------------------------------------------
    if not enabled:
        log.info("🎧 Post-procesado desactivado. Se deja el video sin cambios.")
        return input_path

    # ---------------------------------------------------------
    # 🔎 Validar acción
    # ---------------------------------------------------------
    if action not in ("audio", "both"):
        log.warning(f"⚠️ Acción '{action}' inválida. Se deja el archivo original.")
        return input_path

    if not input_path.exists():
        log.error(f"❌ Archivo no encontrado: {input_path}")
        return input_path

    # ---------------------------------------------------------
    # 🧪 Verificar FFmpeg
    # ---------------------------------------------------------
    try:
        _check_ffmpeg()
    except Exception as e:
        log.error(f"❌ FFmpeg no disponible: {e}")
        return input_path

    # ---------------------------------------------------------
    # 📄 Construir ruta de salida
    # ---------------------------------------------------------
    output_path = input_path.with_suffix(f".{audio_format}")

    log.info(f"🎧 Extrayendo audio → {input_path.name}")
    log.info(f"   Acción = {action} | Formato = {audio_format} | Bitrate = {bitrate}")

    # ---------------------------------------------------------
    # 🛠 Generar comando FFmpeg según formato
    # ---------------------------------------------------------
    cmd = [
        str(FFMPEG_BIN),
        "-y",
        "-i", str(input_path),
        "-vn",  # eliminar video, sólo audio
    ]

    if audio_format == "mp3":
        cmd += ["-acodec", "libmp3lame", "-b:a", bitrate]
    elif audio_format == "m4a":
        cmd += ["-c:a", "aac", "-b:a", bitrate]
    elif audio_format == "flac":
        cmd += ["-c:a", "flac"]
    elif audio_format == "wav":
        cmd += ["-acodec", "pcm_s16le"]
    else:
        log.error(f"❌ Formato no soportado: {audio_format}")
        return input_path

    cmd.append(str(output_path))

    # ---------------------------------------------------------
    # ▶️ Ejecutar FFmpeg
    # ---------------------------------------------------------
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )

        if proc.returncode != 0:
            log.error(f"❌ FFmpeg falló:\n{proc.stderr[-300:]}")
            return input_path

    except Exception as e:
        log.error(f"❌ Error ejecutando FFmpeg: {e}")
        return input_path

    log.info(f"🎵 Audio generado: {output_path.name}")

    # ---------------------------------------------------------
    # 🧹 Finalizar según modo
    # ---------------------------------------------------------
    if action == "audio":
        # borrar video original
        try:
            input_path.unlink()
            log.info("🗑 Video eliminado — modo AUDIO.")
        except Exception as e:
            log.error(f"⚠️ No se pudo eliminar video: {e}")
        return output_path

    if action == "both":
        # se deja el video, pero se retorna la ruta del video como archivo final
        return input_path
