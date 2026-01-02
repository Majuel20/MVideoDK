# ==========================================================
# Core/utils.py  ✅ v20 — Utilidades generales (Backend + GUI)
# ==========================================================
"""
Colección de utilidades compartidas entre Backend y GUI en MVideoDk.

Incluye:
- Validación robusta de URLs (con fallback si no existe validators)
- Sanitización de nombres de archivo
- Formateo de IDs, progreso y estados
- Obtención de dominios
- Construcción de títulos amigables para la GUI

Mejoras v20:
- Documentación más clara y concisa.
- Estructura limpia sin modificar la lógica existente.
- Consolidación y consistencia con el estilo del proyecto.
"""

import re
from datetime import datetime

# ==========================================================
# 🔗 Validación de URLs
# ==========================================================
try:
    import validators as _validators
except Exception:
    _validators = None

# Regex de fallback (simple y robusta)
_URL_FALLBACK_RE = re.compile(r"^https?://[^\s]+$", re.IGNORECASE)


def is_valid_url(url: str) -> bool:
    """
    Valida una URL:
    - Si la librería `validators` está instalada, se usa primero.
    - Si falla, se usa una validación básica via regex.

    Args:
        url (str): Cadena a validar.

    Returns:
        bool: True si parece una URL válida.
    """
    if not isinstance(url, str):
        return False

    url = url.strip()
    if not url:
        return False

    if _validators is not None:
        try:
            return bool(_validators.url(url))
        except Exception:
            pass

    return bool(_URL_FALLBACK_RE.match(url))


# ==========================================================
# 📁 Sanitización y formateo genérico
# ==========================================================
def sanitize_filename(name: str) -> str:
    """
    Limpia una cadena para usarla como nombre de archivo:
    - Elimina caracteres inválidos en Windows/Linux.
    - Recorta longitud excesiva.
    """
    safe = re.sub(r'[<>:"/\\|?*]', "", str(name))
    safe = safe.strip().rstrip(".")
    return safe[:200]


def timestamp() -> str:
    """Devuelve un timestamp simple: YYYY-MM-DD_HH-MM-SS."""
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


# ==========================================================
# 🔧 Utilidades para GUI / Logging
# ==========================================================
def format_task_id(prefix: str | None, local_id: int | str | None) -> str:
    """
    Devuelve un ID legible, ej.: prefix='G', local_id=3 → 'G3'.
    """
    if not prefix and not local_id:
        return ""
    if not prefix:
        return str(local_id)
    if local_id is None:
        return str(prefix)
    return f"{prefix}{local_id}"


def format_progress(value: float | int | None) -> str:
    """
    Formatea un valor de porcentaje:
    - None o negativo → "--"
    - Entero → "42%"
    - Float → "42.3%"
    """
    try:
        v = float(value)
        if v < 0:
            return "--"
        if v.is_integer():
            return f"{int(v)}%"
        return f"{v:.1f}%"
    except Exception:
        return "--"


def format_status(status: str) -> str:
    """
    Devuelve una versión amigable del estado para la GUI/logs.
    """
    if not status:
        return "Desconocido"

    s = status.strip().upper()
    mapping = {
        "PENDING":    "🕓 Pendiente",
        "DOWNLOADING": "⬇️ Descargando",
        "COMPLETED":  "✅ Completado",
        "ERROR":      "❌ Error",
        "PAUSED":     "⏸️ Pausado",
        "CANCELLED":  "🛑 Cancelado",
    }
    return mapping.get(s, s.title())


def extract_domain(url: str) -> str:
    """
    Extrae el dominio base de una URL:
        https://www.youtube.com/watch → youtube.com
    """
    if not isinstance(url, str) or not url:
        return ""
    m = re.search(r"https?://(?:www\.)?([^/]+)", url)
    return m.group(1) if m else ""


# ==========================================================
# 🏷️ Construcción de títulos amigables para GUI
# ==========================================================
def build_friendly_title(
    url: str,
    filename: str | None = None,
    mode: str | None = None,
) -> str:
    """
    Genera un título amigable basado en:
    - filename (prioridad)
    - dominio extraído de la URL
    - tipo (VIDEO / PLAYLIST / AUDIO)

    Reglas:
    1) Si filename existe → usarlo directamente.
    2) Identificar plataforma mediante dominio.
    3) Devolver:
       "Video de YouTube", "Playlist de TikTok", "Audio de Instagram", etc.
    """
    # 1) Filename tiene prioridad
    if filename:
        fname = str(filename).strip()
        if fname:
            return fname

    # 2) Dominio
    dom = extract_domain(url)
    if not dom:
        clean = (url or "").strip()
        return clean if clean else "Descarga"

    dom_l = dom.lower()

    if "youtube.com" in dom_l or "youtu.be" in dom_l:
        platform = "YouTube"
    elif "tiktok.com" in dom_l:
        platform = "TikTok"
    elif "instagram.com" in dom_l or "instagr.am" in dom_l:
        platform = "Instagram"
    elif "facebook.com" in dom_l or "fb.watch" in dom_l:
        platform = "Facebook"
    elif "twitter.com" in dom_l or "x.com" in dom_l:
        platform = "Twitter/X"
    else:
        platform = dom

    # 3) Tipo de media
    media_type = "Video"
    if mode:
        m = str(mode).strip().upper()
        if m == "PLAYLIST":
            media_type = "Playlist"
        elif m in ("AUDIO", "MP3", "M4A"):
            media_type = "Audio"

    return f"{media_type} de {platform}"
