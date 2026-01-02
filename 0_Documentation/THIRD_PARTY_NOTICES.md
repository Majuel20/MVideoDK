# Avisos de Terceros (Third-Party Notices)

MVideoDK utiliza bibliotecas, frameworks y herramientas de terceros.  
Cada componente mantiene su propia licencia, marcas registradas y términos de uso.

> Este archivo **no reemplaza** las licencias originales.  
> Su objetivo es documentar dependencias relevantes y facilitar el cumplimiento de licencias.

---

## Componentes Python / Frameworks

- **Python** (runtime)
  - Licencia: PSF License (Python Software Foundation)

- **PyInstaller** (empaquetado)
  - Licencia: GPLv2 con excepción (ver documentación oficial de PyInstaller)

- **PyQt6** (UI del Core)
  - Licencia: GPLv3 o licencia comercial (Riverbank) *(según la modalidad utilizada)*

- **Tkinter** (UI del Launcher)
  - Parte del ecosistema Python/Tcl-Tk (ver documentación de Python)

- **Pillow** (imágenes/splash en el Launcher)
  - Licencia: MIT-CMU (según proyecto Pillow)

- **FastAPI** (si el Core incluye servidor API interno)
  - Licencia: MIT

---

## Herramientas externas (no empaquetadas)

Estas herramientas suelen instalarse en:

`C:\ProgramData\MVideoDK\bin\`

Ejemplos (según la distribución/configuración):
- **FFmpeg**
  - Licencia: LGPL v2.1+ (con partes opcionales GPL dependiendo del build)

- **yt-dlp**
  - Licencia: Unlicense (nota: algunos binarios distribuidos por terceros pueden incluir código con otras licencias)

- **cloudflared**
  - Licencia: Apache 2.0

- **Android Debug Bridge (adb)**
  - Licencia: Apache 2.0 (AOSP)

- **Playwright**
  - Licencia: Apache 2.0

---

## Recomendaciones prácticas (no exhaustivas)

- No eliminar avisos de copyright de terceros.
- Respetar las licencias de cada componente y herramienta utilizada.
- Si distribuyes builds/instaladores, incluye los avisos de terceros junto al instalador (por ejemplo, `THIRD_PARTY_NOTICES.txt` o `THIRD_PARTY_NOTICES.md`).
- Si incluyes binarios de terceros (por ejemplo FFmpeg), verifica la licencia exacta del build y adjunta los textos/avisos requeridos por su licencia cuando aplique.

---

## Enlaces útiles (referencia)

- PyInstaller: https://pyinstaller.org/en/stable/license.html
- PyQt (Riverbank): https://www.riverbankcomputing.com/software/pyqt/
- FFmpeg legal: https://www.ffmpeg.org/legal.html
- Playwright LICENSE: https://github.com/microsoft/playwright/blob/main/LICENSE
- yt-dlp LICENSE: https://github.com/yt-dlp/yt-dlp/blob/master/LICENSE
- cloudflared repo: https://github.com/cloudflare/cloudflared
