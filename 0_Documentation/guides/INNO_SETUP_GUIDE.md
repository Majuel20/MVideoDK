# Guía — 4_InnoSetup (instalador)

Esta guía resume el proceso y checklist del instalador (Inno Setup).

> El instalador NO construye el programa.  
> Solo empaqueta carpetas ya preparadas.

---

## Entradas (fuentes)

1) Programa (Program Files)
- Fuente: `3_Package_Final\Programa\`
- Destino: `C:\Program Files\MVideoDK\`

2) Recursos persistentes (ProgramData)
- Fuente: `2_Installer_Resources\ProgramData\MVideoDK\`
- Destino: `C:\ProgramData\MVideoDK\`

3) Copia para el usuario (Descargas)
- Destino: `%USERPROFILE%\Downloads\MVideoDK_resources\`
  - `Extension\`
  - `Apk\`

---

## Flujo UI recomendado

1. Bienvenida
2. Licencia (EULA)
3. Instalación (copias)
4. Pantalla personalizada: “Extensión del navegador (opcional)”
5. Pantalla final (opción: iniciar MVideoDK)

---

## Cómo compilar

1. Abre Inno Setup
2. Abre: `4_InnoSetup\MVideoDK_installer\MVideoDK.iss`
3. Build/Compile

Salida esperada:
- `4_InnoSetup\MVideoDK_installer\Output\MVideoDK-Setup.exe`

---

## Checklist antes de compilar

- Existe `3_Package_Final\Programa\` (y funciona)
- Existe `2_Installer_Resources\ProgramData\MVideoDK\`
- Existe `docs\EULA_MVideoDK.txt` (del instalador)
- Icono del instalador válido


> Importante:
> El instalador muestra una EULA antes de copiar archivos.
> El texto se toma desde `4_InnoSetup/MVideoDK_installer/docs/EULA_MVideoDK.txt`.
