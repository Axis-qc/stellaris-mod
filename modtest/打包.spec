# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置。

要点：lang/ 必须一起打进产物。onedir 模式下 --add-data 的内容落在
_internal 里，i18n.py 的 _lang_dirs() 已经会去找 sys._MEIPASS，所以
玩家机器上只带 bin/ 整个目录也能取到语言文件。
"""

import os

BASE = os.path.dirname(os.path.abspath(SPEC))
LANG = os.path.join(BASE, "lang")

a = Analysis(
    [os.path.join(BASE, "src", "mod_conflict_check.py")],
    pathex=[os.path.join(BASE, "src")],
    binaries=[],
    datas=[(LANG, "lang")],
    hiddenimports=[],
    hookspath=[],
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
    name="StellarisModConflictChecker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="StellarisModConflictChecker",
)
