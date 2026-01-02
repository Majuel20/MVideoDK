# Guía — 3_Package_Final (producto listo)

Esta carpeta representa el “producto final” ya ensamblado, listo para:
- pruebas sin instalador, o
- empaquetado por Inno Setup.

---

## Qué contiene

- `MVideoDK.exe` (Launcher ONEFILE)
- `MVideoDK_core.exe` (Core ONEDIR)
- `_internal\` (obligatorio)
- otros archivos del Core ONEDIR (icons, DLLs, etc.)

---

## Cómo se arma

1) Compila el Core (ONEDIR) → `dist\MVideoDK_core\...`
2) Compila el Launcher (ONEFILE) → `dist\MVideoDK.exe`
3) Copia/ensambla en una sola carpeta:

```text
3_Package_Final/
└─ programa/
   └─ MVideoDK/
      ├─ MVideoDK.exe
      ├─ MVideoDK_core.exe
      ├─ _internal/
      ├─ icons/ (si aplica)
      └─ ...
```

---

## Prueba obligatoria (sin instalador)

Desde esa carpeta:
- ejecuta `MVideoDK.exe`
- debe abrir splash → iniciar Core → aparecer tray

Si aquí no funciona, el instalador tampoco.

> Nota:
> Esta carpeta **no debe versionarse en Git**.
> Se genera localmente como paso previo al instalador o a pruebas manuales.

