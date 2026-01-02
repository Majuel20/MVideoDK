# Extensión de navegador (opcional)

La extensión es un complemento opcional: **MVideoDK funciona sin ella**.

Este documento explica cómo instalarla manualmente en navegadores basados en Chromium
(Chrome, Edge, Brave, etc.) usando “Load unpacked / Cargar descomprimida”.

> La extensión funciona **mientras el modo desarrollador esté habilitado** en el navegador.

---

## Requisitos

- Navegador basado en Chromium
- **Modo desarrollador** habilitado en la página de extensiones
- Carpeta de la extensión disponible en tu PC

La carpeta se entrega normalmente en:

`%USERPROFILE%\Downloads\MVideoDK_resources\Extension\`

---

## Instalación (Chrome / Edge / Brave)

1. Abre la página de extensiones:
   - Chrome: `chrome://extensions`
   - Edge: `edge://extensions`
2. Activa **Modo desarrollador** (Developer mode).
3. Haz clic en **Cargar descomprimida / Load unpacked**.
4. Selecciona la carpeta de la extensión (la carpeta raíz que contiene el `manifest.json`).
5. Verifica que la extensión quede activada.

---

## Notas importantes

- Si desactivas el modo desarrollador, las extensiones cargadas como “unpacked” pueden deshabilitarse y **dejar de funcionar**.
- Si actualizas los archivos de la extensión, normalmente puedes usar el botón “Recargar” en la página de extensiones.
- Si el instalador te ofrece un botón para abrir la carpeta de la extensión, úsalo para llegar a la ruta correcta.

---

## Desinstalación

- Abre la página de extensiones.
- Elimina la extensión.

---

## Seguridad

Las extensiones en modo desarrollador:
- pueden tener permisos sobre páginas según su `manifest.json`,
- deben instalarse solo si confías en el origen del código,
- pueden ser auditadas revisando su carpeta de instalación.
