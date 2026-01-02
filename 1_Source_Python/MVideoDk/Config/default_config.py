# ==========================================================
# Config/default_config.py  ✅ v20 — Inicialización de configuración
# ==========================================================
"""
Inicializador de configuración para MVideoDk.

Mejoras v20:
- Documentación más clara y uniforme.
- Sección de prefijos reorganizada.
- Limpieza general sin alterar la lógica.

Funciones:
- ensure_config_exists():
      Garantiza que config.ini exista y esté correctamente inicializado.
- get_source_prefix():
      Devuelve un prefijo legible según la fuente (CLIPBOARD → C, GUI → G, etc.).
"""

from Core.app_config import AppConfig
from Core.logger import LoggerFactory

logger = LoggerFactory.get_logger("CONFIG")


# ==========================================================
# 🔧 Inicialización de configuración
# ==========================================================
def ensure_config_exists() -> None:
    """
    Asegura que el archivo de configuración exista y esté completo.
    Si el archivo no existe, AppConfig lo crea con valores por defecto.
    Si existe, valida y completa claves faltantes.

    Se utiliza desde:
        - El servidor principal
        - La GUI
    """
    try:
        cfg = AppConfig()
        cfg.initialize()
        logger.info("✅ Configuración verificada/cargada correctamente.")
    except Exception as e:
        logger.error(f"❌ Error al inicializar configuración: {e}")
        raise


# ==========================================================
# 🔠 Prefijos de origen (IDs legibles)
# ==========================================================
def get_source_prefix(source: str) -> str:
    """
    Devuelve el prefijo asociado a un tipo de origen.
    Esto permite generar IDs internos legibles en la cola.

    Ejemplos:
        MOBILE    → "M"
        EXT       → "E"
        CLIPBOARD → "C"
        FILE      → "F"
        GUI       → "G"
        API       → "A"
        SYSTEM    → "S"

    Si el origen no está mapeado → retorna "?".
    """
    prefix_map = {
        "MOBILE": "M",
        "EXT": "E",
        "CLIPBOARD": "C",
        "FILE": "F",
        "GUI": "G",
        "API": "A",
        "SYSTEM": "S",
    }
    return prefix_map.get(source.upper(), "?")
