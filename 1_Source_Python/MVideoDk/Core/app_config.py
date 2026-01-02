# ==========================================================
# Core/app_config.py  ✅ v20 — Sistema profesional de configuración
# ==========================================================
"""
Gestor centralizado de configuración para MVideoDk.

Mejoras v20:
- Documentación profesional.
- Limpieza interna sin tocar la lógica del proyecto.
- Estructura de secciones más clara y coherente.
- Valores por defecto reorganizados y explicados.

Características:
- Singleton thread-safe.
- Crea config.ini si no existe.
- Rellena claves faltantes sin sobrescribir valores existentes.
- Notifica listeners ante cambios.
- Proporciona getters tipados y robustos.
"""

import configparser
import threading
from pathlib import Path

from Core.paths import (
    config_ini_path,
    downloads_dir,
    logs_dir,
    temp_dir,
    database_path,
    token_path,
    extension_dir,
)


# ==========================================================
# 🧩 Clase principal AppConfig (Singleton)
# ==========================================================
class AppConfig:
    """Gestor global de configuración (Singleton + thread-safe)."""

    _instance = None
    _lock = threading.Lock()

    # ------------------------------------------------------
    # Valores por defecto de toda la aplicación
    # ------------------------------------------------------
    DEFAULTS = {
        "server": {
            "scheme": "http",
            "host": "127.0.0.1",
            "port": "8334",
            "reload": "false",
        },
        "paths": {
            "download_dir": str(downloads_dir()),
            "log_dir": str(logs_dir()),
            "temp_dir": str(temp_dir()),
            "db_path": str(database_path()),
        },
        "security": {
            "token_path": str(token_path()),
        },
        "extension": {
            "dir": str(extension_dir()),
        },
        "logging": {
            "level": "INFO",
        },
        "clipboard": {
            "enabled": "true",
            "interval_ms": "3000",
            "auto_start": "false",
        },
        "downloads": {
            "quality": "best",
            "retry_cancelled": "true",
            "overwrite_existing": "false",
            "extra_args": "",
        },
        "gui": {
            "theme": "dark",
            "auto_refresh": "true",
            "rows_per_page": "25",
        },
        "postprocess": {
            "enabled": "false",
            "action": "none",         # Antes era "video"
            "audio_format": "mp3",
            "audio_bitrate": "320k",
        },
    }

    # ------------------------------------------------------
    # Singleton
    # ------------------------------------------------------
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init_once()
        return cls._instance

    # ------------------------------------------------------
    # Inicialización real del objeto
    # ------------------------------------------------------
    def _init_once(self):
        self.config_file = config_ini_path()
        self.parser = configparser.ConfigParser()
        self.listeners = []
        self.load()

    # ======================================================
    # 📁 Manejo del archivo de configuración
    # ======================================================
    def initialize(self):
        """
        Garantiza que config.ini exista y contenga todas las claves.
        - Si no existe → se crea con DEFAULTS.
        - Si existe → se rellenan claves faltantes.
        """
        if not self.config_file.exists():
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            self._write_defaults()
        else:
            self.load()
            self._fill_missing_defaults()
            self.save()

    def load(self):
        """Carga los valores DEFAULTS y luego los del archivo si existe."""
        self.parser.read_dict(self.DEFAULTS)
        if self.config_file.exists():
            self.parser.read(self.config_file, encoding="utf-8")

    def save(self):
        """Guarda la configuración actual en config.ini."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w", encoding="utf-8") as f:
            self.parser.write(f)

    def _write_defaults(self):
        """Crea un config.ini limpio con valores por defecto."""
        self.parser.read_dict(self.DEFAULTS)
        self.save()

    def _fill_missing_defaults(self):
        """Inserta claves faltantes sin reemplazar valores existentes."""
        updated = False

        for section, values in self.DEFAULTS.items():
            if not self.parser.has_section(section):
                self.parser[section] = values
                updated = True
            else:
                for key, value in values.items():
                    if not self.parser.has_option(section, key):
                        self.parser.set(section, key, value)
                        updated = True

        if updated:
            self.save()

    # ======================================================
    # 🔍 Métodos GET genéricos
    # ======================================================
    def get(self, section: str, key: str, fallback=None):
        return self.parser.get(section, key, fallback=fallback)

    def getint(self, section: str, key: str, fallback=None):
        try:
            return self.parser.getint(section, key, fallback=fallback)
        except Exception:
            return fallback

    def getfloat(self, section: str, key: str, fallback=None):
        """Conversión robusta float → admite valores no estrictos."""
        try:
            return self.parser.getfloat(section, key, fallback=fallback)
        except Exception:
            raw = self.get(section, key, fallback)
            try:
                return float(raw)
            except Exception:
                return fallback

    def getboolean(self, section: str, key: str, fallback=None):
        try:
            return self.parser.getboolean(section, key, fallback=fallback)
        except Exception:
            return fallback

    def get_clipboard_config(self) -> dict:
        """Devuelve las opciones completas de la sección [clipboard]."""
        return {
            "enabled": self.getboolean("clipboard", "enabled", fallback=True),
            "auto_start": self.getboolean("clipboard", "auto_start", fallback=False),
            "interval_ms": self.getint("clipboard", "interval_ms", fallback=3000),
        }

    # ======================================================
    # 📂 Rutas absolutas
    # ======================================================
    def get_path(self, name: str) -> Path:
        """Obtiene una ruta desde la sección [paths]."""
        value = self.parser.get("paths", name, fallback=None)
        return Path(value).resolve()

    def get_token_path(self) -> Path:
        """
        Devuelve la ruta absoluta del token.
        Crea automáticamente la carpeta correspondiente si no existe.
        """
        raw = self.get("security", "token_path", fallback=str(token_path()))
        path = Path(raw).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    # ======================================================
    # 📦 Crear directorios necesarios
    # ======================================================
    def ensure_dirs(self):
        """Crea todas las carpetas críticas si aún no existen."""
        downloads_dir().mkdir(parents=True, exist_ok=True)
        logs_dir().mkdir(parents=True, exist_ok=True)
        temp_dir().mkdir(parents=True, exist_ok=True)
        token_path().parent.mkdir(parents=True, exist_ok=True)

    # ======================================================
    # 🌐 Getters del servidor
    # ======================================================
    def get_server_scheme(self) -> str:
        return self.parser.get("server", "scheme", fallback="http").strip()

    def get_server_host(self) -> str:
        return self.parser.get("server", "host", fallback="127.0.0.1").strip()

    def get_server_port(self) -> int:
        try:
            return self.parser.getint("server", "port", fallback=8334)
        except Exception:
            return 8334

    def get_server_url(self) -> str:
        """Compone la URL base del servidor, ej: http://127.0.0.1:8334."""
        scheme = self.get_server_scheme()
        host = self.get_server_host()
        port = self.get_server_port()
        return f"{scheme}://{host}:{port}"

    # ======================================================
    # 🔔 Listeners de configuración
    # ======================================================
    def add_listener(self, callback):
        """Registra funciones que reaccionan a cambios en config."""
        if callable(callback):
            self.listeners.append(callback)

    def set(self, section: str, key: str, value):
        """
        Modifica la configuración y notifica listeners.
        - Crea la sección si no existe.
        - Guarda inmediatamente en disco.
        """
        if not self.parser.has_section(section):
            self.parser.add_section(section)

        self.parser.set(section, key, str(value))
        self.save()

        for cb in self.listeners:
            try:
                cb(section, key, value)
            except Exception:
                pass
