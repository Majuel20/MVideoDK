# ==========================================================
# Core/paths.py  ✅ v20 — Sistema central de rutas para instalador
# ==========================================================
"""
Sistema definitivo de rutas para MVideoDK.

Objetivos v20:
- Mantener compatibilidad total con instalador y ejecución empaquetada (.exe).
- Centralizar todas las rutas críticas.
- Uniformar documentación y estilo.
- NO modificar lógica original.

Todos los datos se almacenan bajo:
    C:\ProgramData\MVideoDK\
excepto las descargas, que van a:
    ~/Downloads/MVideoDK
"""

from pathlib import Path

# Nombre raíz de la aplicación (para instalador)
APP_NAME = "MVideoDK"

# Carpeta base establecida por el instalador
BASE_DATA_DIR = Path(r"C:\ProgramData") / APP_NAME


# ==========================================================
# 📁 Carpetas principales
# ==========================================================
def data_dir() -> Path:
    """Carpeta principal de datos: C:/ProgramData/MVideoDK/Data"""
    return (BASE_DATA_DIR / "Data").resolve()


def logs_dir() -> Path:
    """Carpeta de logs rotativos."""
    return (BASE_DATA_DIR / "Logs").resolve()


def config_dir() -> Path:
    """Carpeta del archivo config.ini."""
    return (BASE_DATA_DIR / "Config").resolve()


def temp_dir() -> Path:
    """Carpeta temporal para operaciones del sistema."""
    return (BASE_DATA_DIR / "Temp").resolve()


def downloads_dir() -> Path:
    """
    Carpeta donde se guardan descargas del usuario.
    Home/Downloads/MVideoDK   (independiente del instalador)
    """
    return (Path.home() / "Downloads" / APP_NAME).resolve()


def extension_dir() -> Path:
    """Carpeta para extensiones externas."""
    return (BASE_DATA_DIR / "Extension").resolve()


def apk_dir() -> Path:
    """Carpeta para APKs o herramientas móviles."""
    return (BASE_DATA_DIR / "Apk").resolve()


def bin_dir() -> Path:
    """Carpeta donde se guardan binarios ffmpeg, adb, yt-dlp, playwright, etc."""
    return (BASE_DATA_DIR / "bin").resolve()


# ==========================================================
# 🔧 BINARIOS
# ==========================================================
def ffmpeg_dir() -> Path:
    """Directorio contenedor de ejecutables FFmpeg."""
    return (bin_dir() / "ffmpeg").resolve()


def adb_dir() -> Path:
    """Directorio de ADB (Android Debug Bridge)."""
    return (bin_dir() / "adb").resolve()


def ytdlp_dir() -> Path:
    """Carpeta que contiene yt-dlp."""
    return (bin_dir() / "yt-dlp").resolve()


def ytdlp_executable() -> Path:
    """Ruta al ejecutable yt-dlp.exe."""
    return ytdlp_dir() / "yt-dlp.exe"


# ==========================================================
# 🌐 Playwright Chromium
# ==========================================================
def playwright_dir() -> Path:
    """
    Carpeta raíz donde se copia el paquete 'ms-playwright'.
    Ejemplo:
        C:\ProgramData\MVideoDK\bin\ms-playwright
    """
    return (bin_dir() / "ms-playwright").resolve()


def chromium_dir() -> Path:
    """
    Ruta a la carpeta de la versión específica de Chromium.
    Ejemplo real:
        C:\ProgramData\MVideoDK\bin\ms-playwright\chromium-1194\chrome-win
    """
    return (playwright_dir() / "chromium-1194" / "chrome-win").resolve()


def chromium_executable() -> Path:
    """Ruta exacta de chrome.exe utilizado por Playwright."""
    return chromium_dir() / "chrome.exe"


# ==========================================================
# 📄 Archivos específicos
# ==========================================================
def database_path() -> Path:
    """Ruta al archivo SQLite principal."""
    return data_dir() / "database.db"


def token_path() -> Path:
    """Ruta al archivo token.key."""
    return data_dir() / "token.key"


def config_ini_path() -> Path:
    """Ruta al archivo config.ini principal."""
    return config_dir() / "config.ini"


# ==========================================================
# 🏗️ Creación automática de estructura
# ==========================================================
def ensure_dirs() -> None:
    """
    Crea toda la estructura de carpetas necesarias para el programa.
    No crea archivos.
    No necesita crear chrome.exe (solo la carpeta contenedora).
    """
    for p in [
        data_dir(),
        logs_dir(),
        config_dir(),
        temp_dir(),
        downloads_dir(),
        extension_dir(),
        apk_dir(),
        bin_dir(),
        ffmpeg_dir(),
        adb_dir(),
        ytdlp_dir(),
        playwright_dir(),    # Contenedor ms-playwright
        chromium_dir(),      # Carpeta donde estará chrome.exe
    ]:
        p.mkdir(parents=True, exist_ok=True)
