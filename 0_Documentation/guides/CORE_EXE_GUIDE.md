# Guía — Build de ejecutables (Core + Launcher)

Esta guía explica cómo generar los ejecutables de MVideoDK en Windows usando PyInstaller.

Se generan dos ejecutables distintos:

- Core: MVideoDK_core.exe (ONEDIR)
- Launcher: MVideoDK.exe (ONEFILE, windowed)

Notas clave:
- El Core es la aplicación real.
- El Launcher solo muestra splash y ejecuta el Core.
- Los binarios externos (ffmpeg, yt-dlp, cloudflared, adb, playwright, etc.) NO se empaquetan dentro de los exe.

---

## Estructura esperada del proyecto

```text
PROJECT_MVideoDK/
├─ 1_Source_Python/
│  ├─ MVideoDk/        (Core)
│  │  ├─ main.py
│  │  ├─ MVideoDK_core.spec
│  │  └─ icons/
│  └─ Launcher/        (Launcher)
│     ├─ MVideoDK.py
│     ├─ MVideoDK.spec
│     └─ Iconos/
│
├─ 3_Package_Final/
│  └─ Programa/
│     └─ MVideoDK/
└─ 4_InnoSetup/
