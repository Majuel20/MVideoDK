# Arquitectura de MVideoDK

Este documento describe la arquitectura de MVideoDK a un nivel **práctico y verificable**:
qué componentes existen, cómo se empaquetan, cómo se ejecutan y qué rutas usa el sistema en Windows.

> Público objetivo: usuarios avanzados, testers y desarrolladores que necesitan entender el “mapa” del proyecto sin entrar todavía en el detalle del código.

---

## Principios

1. **Separación clara de responsabilidades**
   - El **Core** es la aplicación real.
   - El **Launcher** solo presenta (splash) y ejecuta el Core.
   - El **instalador** solo empaqueta/copía archivos ya preparados.

2. **Estabilidad primero**
   - El Core se distribuye como **ONEDIR** (más estable en Windows con PyQt).
   - El Launcher se distribuye como **ONEFILE** (ligero, windowed).

3. **Binarios externos fuera del ejecutable**
   - Herramientas como `ffmpeg`, `yt-dlp`, `cloudflared`, `adb` y `playwright` se instalan en
     `C:\ProgramData\MVideoDK\bin\` y **no** se empaquetan dentro del `.exe`.

---

## Componentes

### 1) Core (aplicación principal)

- Ejecutable: `MVideoDK_core.exe`
- Empaquetado: PyInstaller **ONEDIR**
- Contiene: lógica principal, GUI, system tray, y servicios internos.
- Requisito en runtime: la carpeta `_internal` debe existir junto al ejecutable.

> Detalle importante: el Core se compila con consola habilitada por compatibilidad con el tray.

---

### 2) Launcher

- Ejecutable: `MVideoDK.exe`
- Empaquetado: PyInstaller **ONEFILE** (windowed)
- Función:
  - ocultar consola,
  - mostrar splash,
  - ejecutar `MVideoDK_core.exe` (en la misma carpeta),
  - cerrarse.

---

### 3) Recursos persistentes (ProgramData)

Ubicación: `C:\ProgramData\MVideoDK\`

Contiene:
- `bin\` (binarios externos)
- `Config\`
- `Data\`
- `Logs\`
- `Temp\`
- `Extension\`
- `Apk\`

Estos recursos:
- no dependen del build del Core/Launcher,
- se copian por el instalador,
- permanecen entre ejecuciones.

---

### 4) Recursos para el usuario (Descargas)

El instalador deja una copia informativa (y opcional) en:

`%USERPROFILE%\Downloads\MVideoDK_resources\`
- `Extension\`
- `Apk\`

---

### 5) Extensión de navegador (opcional)

- Complementaria: MVideoDK funciona sin ella.
- Instalación manual:
  - “Load unpacked / Cargar descomprimida”
  - requiere modo desarrollador habilitado.
- Ubicación entregada al usuario:
  - `Descargas\MVideoDK_resources\Extension`

---

### 6) APK (opcional)

- Ubicación entregada al usuario:
  - `Descargas\MVideoDK_resources\Apk`

---

## Rutas finales en Windows

### Program Files (aplicación)
`C:\Program Files\MVideoDK\`

- `MVideoDK.exe` (Launcher)
- `MVideoDK_core.exe` (Core)
- `_internal\` (dependencias del Core)
- `docs\` (documentación instalada)

### ProgramData (recursos persistentes)
`C:\ProgramData\MVideoDK\`

- `bin\` (herramientas externas)
- `Config\`, `Logs\`, `Data\`, etc.

### Descargas (recursos opcionales del usuario)
`%USERPROFILE%\Downloads\MVideoDK_resources\`

---

## Flujo de ejecución (runtime)

```text
Usuario
  └─ Ejecuta MVideoDK.exe (Launcher)
        ├─ Muestra splash
        ├─ Busca MVideoDK_core.exe en la misma carpeta
        ├─ Lanza MVideoDK_core.exe
        └─ Se cierra

MVideoDK_core.exe (Core)
  ├─ Inicia GUI (PyQt)
  ├─ Inicia tray
  ├─ Usa recursos de ProgramData (bin, config, logs)
  └─ Ejecuta funcionalidades según el uso del usuario
```

---

## Flujo de construcción y empaquetado (build → instalador)

```text
1) Build del Core (ONEDIR)     -> dist/MVideoDK_core/...
2) Build del Launcher (ONEFILE)-> dist/MVideoDK.exe

3) Ensamblaje (3_Package_Final)
   - se juntan Launcher + Core ONEDIR (incluye _internal)

4) Instalador (4_InnoSetup)
   - copia 3_Package_Final a Program Files
   - copia 2_Installer_Resources a ProgramData
   - deja copia opcional en Descargas
```

> Para detalles prácticos, ver las guías por carpeta en `docs/guides/`.

---

## Qué NO forma parte de esta arquitectura

- No se asume servicio comercial ni infraestructura propia de servidores.
- No se empaquetan binarios externos dentro de los ejecutables.
- La extensión y el APK son **opcionales**.
