# Guía — 2_Installer_Resources (ProgramData)

Esta carpeta contiene recursos que el instalador copiará a:

`C:\ProgramData\MVideoDK\`

Aquí viven:
- binarios externos,
- carpetas persistentes,
- recursos que no deben ir dentro del Core/Launcher.

---

## Qué SÍ va aquí

- `bin\` (ffmpeg, yt-dlp, cloudflared, adb, playwright, etc.)
- `Config\`, `Data\`, `Logs\`, `Temp\`
- `Extension\` (copia técnica)
- `Apk\` (copia técnica)

---

## Qué NO va aquí

- `MVideoDK.exe` (launcher)
- `MVideoDK_core.exe` (core)
- `_internal\`
- `dist/` o `build/` de PyInstaller
- código fuente Python
- scripts `.iss`

---

## Estructura recomendada

```text
2_Installer_Resources/
└─ ProgramData/
   └─ MVideoDK/
      ├─ bin/
      ├─ Config/
      ├─ Data/
      ├─ Logs/
      ├─ Temp/
      ├─ Extension/
      └─ Apk/
```

---

