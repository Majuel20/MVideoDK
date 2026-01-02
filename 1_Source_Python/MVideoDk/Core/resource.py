# ==========================================================
# Core/resource.py  ✅ v20 — Resolver de rutas para PyInstaller
# ==========================================================
"""
Utilidad para obtener rutas absolutas de recursos en MVideoDK.

Compatible con:
- Ejecución normal en entorno de desarrollo.
- Ejecutables empaquetados con PyInstaller (.exe):
      PyInstaller crea una carpeta temporal _MEIPASS donde
      se extraen los recursos incluidos en el bundle.

Uso típico:
    resource_path("assets/icon.png")
"""

from pathlib import Path
import sys


# ==========================================================
# 🔍 Resolución de recursos
# ==========================================================
def resource_path(relative_path: str) -> str:
    """
    Resuelve la ruta absoluta de un recurso.

    Comportamiento:
    - Si el programa está empaquetado con PyInstaller, usa sys._MEIPASS.
    - En desarrollo, usa la raíz del proyecto (dos niveles arriba de este archivo).

    Args:
        relative_path (str): Ruta relativa dentro del proyecto o bundle.

    Returns:
        str: Ruta absoluta al recurso solicitado.
    """
    if hasattr(sys, "_MEIPASS"):
        # PyInstaller → carpeta temporal que contiene los recursos
        base = Path(sys._MEIPASS)
    else:
        # /Core/resource.py → parent = /Core → parents[1] = raíz del proyecto
        base = Path(__file__).resolve().parents[1]

    return str((base / relative_path).resolve())
