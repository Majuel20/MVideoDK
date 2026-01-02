# ==========================================================
# Server/log.py  ✅ v20 — Helper unificado de logging del servidor
# ==========================================================
"""
Módulo auxiliar para obtener loggers ya configurados mediante
LoggerFactory. Garantiza consistencia en todo el backend:

- Formato unificado
- Rotación diaria
- Salida a archivo + consola
- Respeta AppConfig → [logging] level

Se usa en todos los componentes del servidor (worker, API, downloaders).
"""

from Core.logger import LoggerFactory


def get_server_logger(name: str = "SERVER"):
    """
    Devuelve un logger configurado con el sistema centralizado.

    Args:
        name (str): Nombre lógico del logger.  
                    Por defecto: "SERVER".

    Returns:
        logging.Logger: Instancia configurada por LoggerFactory.
    """
    return LoggerFactory.get_logger(name)
