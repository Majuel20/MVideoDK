# ==========================================================
# Core/logger.py  ✅ v20 — Sistema consolidado de logging
# ==========================================================
"""
Sistema de logging centralizado para MVideoDk.

Mejoras v20:
- Documentación clara y profesional.
- Organización interna más legible.
- Mantiene exactamente la misma lógica y compatibilidad total.

Características:
- Logs rotativos diarios con TimedRotatingFileHandler.
- Consola unificada con formato consistente.
- Nivel configurable desde config.ini ([logging].level).
- Guarda logs bajo ProgramData / directorio asignado en Core.paths.
"""

import sys
import logging
from logging.handlers import TimedRotatingFileHandler

from Core.paths import logs_dir
from Core.app_config import AppConfig


# ==========================================================
# 🔍 Nivel de logging según configuración
# ==========================================================
def _get_level() -> int:
    """
    Obtiene el nivel de logging desde config.ini.
    Si no es válido, retorna INFO como fallback.
    """
    cfg = AppConfig()
    level = cfg.get("logging", "level", fallback="INFO").upper()
    return getattr(logging, level, logging.INFO)


# ==========================================================
# 🏭 Fábrica de loggers
# ==========================================================
class LoggerFactory:
    """
    Generador centralizado de loggers:
    - Un logger por nombre.
    - Evita crear handlers duplicados.
    """

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """
        Devuelve un logger configurado para el módulo solicitado.

        Comportamiento:
        - Crea automáticamente el directorio de logs.
        - Añade handler rotativo por día (backup 7 días).
        - Añade también salida a consola.
        - Aplica formato uniforme.
        - Respeta el nivel definido en config.ini.
        """
        logs_dir().mkdir(parents=True, exist_ok=True)
        log_path = logs_dir() / f"{name.lower()}.log"

        logger = logging.getLogger(name)

        # Evitar duplicar handlers si ya fue creado.
        if logger.handlers:
            return logger

        # ---------- File handler (rotación diaria) ----------
        file_handler = TimedRotatingFileHandler(
            filename=log_path,
            when="midnight",
            backupCount=7,
            encoding="utf-8",
        )

        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(formatter)

        # ---------- Consola ----------
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)

        # ---------- Registrar handlers ----------
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        # ---------- Nivel global ----------
        level = _get_level()
        logger.setLevel(level)
        file_handler.setLevel(level)
        console_handler.setLevel(level)

        return logger
