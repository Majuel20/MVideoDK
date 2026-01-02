# Instalación (Windows 10/11 x64)

Esta guía explica cómo instalar y ejecutar MVideoDK en Windows.

> Si solo quieres entender “qué instala dónde”, este documento es suficiente.  
> Si necesitas construir el instalador o compilar ejecutables, revisa `docs/guides/`.

---

## Requisitos

- Windows 10 u 11 (64-bit)
- Permisos para instalar en **Program Files** y escribir en **ProgramData**

---

## Instalación con instalador (recomendado)

1. Ejecuta el instalador `MVideoDK-Setup.exe`.
2. El instalador **muestra el EULA antes de instalar**; léelo y acéptalo para continuar.
3. Elige carpeta de instalación (por defecto: `C:\Program Files\MVideoDK\`).
4. Finaliza.

El instalador:
- Copia el programa a **Program Files**
- Copia recursos técnicos a **ProgramData**
- Deja recursos opcionales para el usuario en **Descargas**
- Muestra una pantalla final con instrucciones sobre la extensión (**la extensión es opcional**)

---

## ¿Dónde se instala cada cosa?

### Programa (Program Files)
`C:\Program Files\MVideoDK\`

Incluye:
- `MVideoDK.exe` (Launcher)
- `MVideoDK_core.exe` (Core)
- `_internal\` (obligatorio para el Core)
- `docs\` (documentación instalada)

### Recursos persistentes (ProgramData)
`C:\ProgramData\MVideoDK\`

Incluye (ejemplo):
- `bin\` (ffmpeg, yt-dlp, cloudflared, adb, playwright, etc.)
- `Config\`
- `Data\`
- `Logs\`
- `Temp\`
- `Extension\`
- `Apk\`

### Copia para el usuario (Descargas)
`%USERPROFILE%\Downloads\MVideoDK_resources\`
- `Extension\` (opcional)
- `Apk\` (opcional)

---

## Primer inicio

1. Abre el acceso directo o ejecuta:
   - `C:\Program Files\MVideoDK\MVideoDK.exe`
2. Verás un splash corto (Launcher).
3. Se iniciará el Core (aplicación real).

> Si el Core no arranca, revisa “Solución de problemas”.

---

## Extensión de navegador (opcional)

MVideoDK funciona sin extensión.

La instalación de la extensión es **opcional** y se realiza manualmente.

Si deseas instalarla:
- Lee: [`docs/EXTENSION.md`](EXTENSION.md)

---

## Desinstalación

- Usa “Agregar o quitar programas” (Windows).
- El desinstalador elimina los archivos en **Program Files** y las entradas del instalador.

> Nota: según la **configuración o decisión del instalador**, algunas carpetas en **ProgramData** (por ejemplo logs o datos) pueden permanecer tras la desinstalación.  
> Si deseas un borrado completo, elimina manualmente `C:\ProgramData\MVideoDK\` (solo si ya no necesitas esa información).

---

## Solución de problemas

### El programa no inicia (o se cierra instantáneamente)

- Verifica que existan:
  - `MVideoDK_core.exe`
  - la carpeta `_internal\` junto al Core

### “No se encuentran binarios externos”

- Verifica que existan en:
  - `C:\ProgramData\MVideoDK\bin\`

### La extensión no aparece o no funciona

- Es normal si no la instalaste manualmente.
- Revisa:
  - [`docs/EXTENSION.md`](EXTENSION.md)
