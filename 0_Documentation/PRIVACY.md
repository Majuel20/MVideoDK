# Privacidad

Este documento describe la postura de privacidad de MVideoDK.

> Importante: MVideoDK es un proyecto personal/educativo. Este documento busca ser claro y honesto, sin lenguaje comercial.

---

## Resumen

- MVideoDK no está pensado como un servicio comercial.
- No requiere registro de cuentas.
- No ofrece una infraestructura propia de servidores “en la nube”.
- Los datos principales del funcionamiento se almacenan **localmente** en el equipo del usuario.

---

## Datos que pueden almacenarse localmente

MVideoDK utiliza carpetas de trabajo en:

`C:\ProgramData\MVideoDK\`

Típicamente:
- `Config\` : configuración local
- `Logs\`   : registros de ejecución (para diagnóstico)
- `Data\`   : datos locales de la aplicación (si aplica)
- `Temp\`   : temporales

> Si el usuario desinstala, algunos datos en ProgramData podrían permanecer según la configuración del instalador. Se pueden borrar manualmente si ya no se necesitan.

---

## Red y servicios de terceros

Dependiendo de las funciones que el usuario use, MVideoDK puede interactuar con:
- sitios web o plataformas externas (por ejemplo, al descargar contenido),
- herramientas externas instaladas en `C:\ProgramData\MVideoDK\bin\` (p. ej. ffmpeg, yt-dlp, cloudflared, adb, playwright).

En esos casos:
- La comunicación ocurre entre el equipo del usuario y dichos servicios/herramientas.
- Es posible que esos terceros registren información técnica estándar (p. ej. IP, user-agent, logs propios).

MVideoDK no controla las políticas de privacidad de terceros.  
Para más contexto, ver: `docs/THIRD_PARTY_NOTICES.md`.

---

## Extensión de navegador (opcional)

La extensión se instala manualmente (modo desarrollador) y puede:
- interactuar con páginas del navegador según los permisos definidos por su `manifest.json`.

Si no deseas este componente, simplemente no lo instales.

---

## Control del usuario

El usuario puede:
- revisar y borrar `C:\ProgramData\MVideoDK\Logs\` y `Temp\`
- desinstalar el programa
- eliminar manualmente `C:\ProgramData\MVideoDK\` (si desea un borrado total)
- no instalar la extensión ni el APK (opcionales)

---

## Contacto

Si necesitas reportar un problema de privacidad o un hallazgo de seguridad:
- abre un Issue en GitHub (recomendado), o
- usa el canal de contacto definido por el repositorio.

---

## Documento instalado

Este documento se incluye con el programa como:

`C:\Program Files\MVideoDK\docs\PRIVACY.txt`

El archivo `.md` se mantiene en el repositorio únicamente con fines de documentación y desarrollo.
