# MVideoDK

MVideoDK es un proyecto **personal y educativo** para **Windows 10/11 (x64)**.  
Se comparte para **aprendizaje, referencia y mejoras comunitarias**.  
**No es un producto comercial.**

Este repositorio contiene:
- Código fuente (Core + Launcher)
- Documentación oficial del proyecto
- Recursos y guías para generar el instalador (Inno Setup)

> **Nota importante**  
> Los ejecutables (`.exe`) y binarios externos **no deben versionarse en Git**.  
> Para distribución se recomienda usar **GitHub Releases** y/o el **instalador oficial**.

---

## Documentación

La documentación oficial del proyecto se encuentra en la carpeta:

**`0_Documentation/`**

Documentos principales:
- **Arquitectura**: [`0_Documentation/ARCHITECTURE.md`](0_Documentation/ARCHITECTURE.md)
- **Instalación y rutas**: [`0_Documentation/INSTALLATION.md`](0_Documentation/INSTALLATION.md)
- **Extensión de navegador (opcional)**: [`0_Documentation/EXTENSION.md`](0_Documentation/EXTENSION.md)
- **Privacidad**: [`0_Documentation/PRIVACY.md`](0_Documentation/PRIVACY.md)
- **Términos de uso / EULA**: [`0_Documentation/TERMS.md`](0_Documentation/TERMS.md)
- **Avisos de terceros**: [`0_Documentation/THIRD_PARTY_NOTICES.md`](0_Documentation/THIRD_PARTY_NOTICES.md)

Guías técnicas por etapa del proyecto:
- [`0_Documentation/guides/CORE_EXE_GUIDE.md`](0_Documentation/guides/CORE_EXE_GUIDE.md)
- [`0_Documentation/guides/INSTALLER_RESOURCES_GUIDE.md`](0_Documentation/guides/INSTALLER_RESOURCES_GUIDE.md)
- [`0_Documentation/guides/PACKAGE_FINAL_GUIDE.md`](0_Documentation/guides/PACKAGE_FINAL_GUIDE.md)
- [`0_Documentation/guides/INNO_SETUP_GUIDE.md`](0_Documentation/guides/INNO_SETUP_GUIDE.md)

---

## Resumen rápido (qué es qué)

MVideoDK está dividido en varias piezas claramente separadas:

- **Core** (`MVideoDK_core.exe`, PyInstaller **ONEDIR**)  
  La aplicación real: GUI, system tray y lógica principal.

- **Launcher** (`MVideoDK.exe`, PyInstaller **ONEFILE** windowed)  
  Muestra un splash, ejecuta el Core y se cierra.

- **Binarios externos** (NO empaquetados en el exe)  
  Se instalan en:  
  `C:\ProgramData\MVideoDK\bin\`

- **Extensión de navegador (opcional)**  
  Instalación manual en modo desarrollador (Chromium-based).

- **APK (opcional)**  
  Se entrega como recurso adicional para el usuario.

---

## Estructura del proyecto (alto nivel)

```text
PROJECT_MVideoDK/
├─ README.md
├─ 0_Documentation/
│  ├─ ARCHITECTURE.md
│  ├─ INSTALLATION.md
│  ├─ EXTENSION.md
│  ├─ PRIVACY.md
│  ├─ TERMS.md
│  ├─ THIRD_PARTY_NOTICES.md
│  └─ guides/
│     ├─ CORE_EXE_GUIDE.md
│     ├─ INSTALLER_RESOURCES_GUIDE.md
│     ├─ PACKAGE_FINAL_GUIDE.md
│     └─ INNO_SETUP_GUIDE.md
│
├─ 1_Source_Python/
│  ├─ MVideoDK/        (Core)
│  └─ Launcher/        (Launcher)
│
├─ 2_Installer_Resources/
├─ 3_Package_Final/
└─ 4_InnoSetup/
