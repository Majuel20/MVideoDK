# ==========================================================
# Server/security.py  ✅ v20 — Gestión centralizada del token
# ==========================================================
"""
Módulo de seguridad para MVideoDK.

Responsabilidades:
- Gestionar el token del servidor (archivo configurable).
- Crear un token si no existe o está vacío.
- Verificar tokens entrantes (Bearer) mediante comparación segura.
- Generar hashing SHA256 para exponer un identificador seguro.

Este módulo es utilizado por:
- API (autenticación de endpoints)
- Extensión del navegador
- GUI
"""

import os
import hmac
import hashlib
from pathlib import Path

from Core.paths import token_path as default_token_path
from Core.logger import LoggerFactory
from Core.app_config import AppConfig

logger = LoggerFactory.get_logger("SECURITY")


# ----------------------------------------------------------
# 📌 Ruta del archivo de token
# ----------------------------------------------------------
def _get_token_file() -> Path:
    """
    Obtiene la ruta final del archivo de token.

    Prioridad:
        1) security.token_path en config.ini (AppConfig)
        2) token_path() definido en Core.paths
    """
    cfg = AppConfig()
    cfg_path = cfg.get("security", "token_path", fallback="").strip()

    if cfg_path:
        return Path(cfg_path).expanduser().resolve()

    # Usar ruta por defecto del sistema
    return default_token_path().resolve()


# ----------------------------------------------------------
# 🔐 Crear token
# ----------------------------------------------------------
def create_token() -> str:
    """
    Crea un token aleatorio, lo escribe en disco y lo devuelve.

    Returns:
        str: Token generado (hex).
    """
    token_file = _get_token_file()

    try:
        token_file.parent.mkdir(parents=True, exist_ok=True)

        token = os.urandom(16).hex()
        token_file.write_text(token, encoding="utf-8")

        logger.info(f"🔑 Token generado en: {token_file}")
        return token

    except Exception as e:
        logger.error(f"❌ Error al crear token: {e}")
        raise


# ----------------------------------------------------------
# 📖 Leer token
# ----------------------------------------------------------
def get_token() -> str:
    """
    Obtiene el token actual. Si no existe o está vacío, lo recrea.

    Returns:
        str: Token del servidor.
    """
    token_file = _get_token_file()

    if not token_file.exists():
        return create_token()

    try:
        token = token_file.read_text(encoding="utf-8").strip()

        if not token:
            logger.warning("Archivo de token vacío — regenerando token...")
            return create_token()

        return token

    except Exception as e:
        logger.error(f"Error al leer token: {e}")
        return create_token()


# ----------------------------------------------------------
# 🧠 Digest SHA256
# ----------------------------------------------------------
def get_token_digest() -> str:
    """
    Devuelve SHA256(token actual) para debug seguro.

    Returns:
        str: Digest en hexadecimal.
    """
    token = get_token().encode("utf-8")
    return hashlib.sha256(token).hexdigest()


# ----------------------------------------------------------
# ✅ Verificar token
# ----------------------------------------------------------
def verify_token(token: str) -> bool:
    """
    Compara el token recibido con el token del servidor.

    Utiliza hmac.compare_digest → seguro ante ataques de tiempo.

    Args:
        token (str): Token recibido (Authorization: Bearer ...)

    Returns:
        bool: True si coincide, False si no.
    """
    try:
        expected = get_token()
        is_valid = hmac.compare_digest(token.strip(), expected)

        if not is_valid:
            logger.warning("Intento de autenticación fallido.")
        return is_valid

    except Exception as e:
        logger.error(f"Error verificando token: {e}")
        return False
