# -*- mode: python ; coding: utf-8 -*-
# -*- ONEDIR (estable, recomendado) -*-

from PyInstaller.utils.hooks import collect_submodules

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('icons', 'icons'),
    ],
    hiddenimports=collect_submodules('PyQt6'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MVideoDK_core',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon='icons/main/icon_256.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name='MVideoDK_core',
)
