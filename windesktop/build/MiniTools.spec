# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置（onedir）。"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

PROJECT = Path(SPECPATH).resolve().parent
ICON = PROJECT / "app" / "assets" / "app.ico"

# 明显用不到的重型 Qt 模块，跳过以压缩体积
EXCLUDES = [
    "tkinter",
    "unittest",
    "pydoc_data",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtQuick",
    "PySide6.QtQuick3D",
    "PySide6.QtQml",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DRender",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DExtras",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtDesigner",
    "PySide6.QtHelp",
    "PySide6.QtSql",
    "PySide6.QtTest",
    "PySide6.QtBluetooth",
    "PySide6.QtNfc",
    "PySide6.QtPositioning",
    "PySide6.QtSensors",
    "PySide6.QtSerialPort",
    "PySide6.QtTextToSpeech",
    "PySide6.QtWebSockets",
    "PySide6.QtWebChannel",
    "PySide6.QtRemoteObjects",
    "PySide6.QtScxml",
    "PySide6.QtStateMachine",
    "PySide6.QtSpatialAudio",
    "PySide6.QtHttpServer",
    "PySide6.QtNetworkAuth",
    "PySide6.QtOpenGLFunctions",
]

# 运行时不需要的二进制 / 插件（按子串匹配）
DROP_BINARIES = (
    "qt6webengine",
    "qt6quick",
    "qt6qml",
    "qt6pdf",
    "qt63d",
    "qt6charts",
    "qt6datavisualization",
    "qt6designer",
    "qt6help",
    "qt6multimedia",
    "qt6bluetooth",
    "qt6nfc",
    "qt6positioning",
    "qt6sensors",
    "qt6serialport",
    "qt6texttospeech",
    "qt6websockets",
    "qt6webchannel",
    "qt6remoteobjects",
    "qt6scxml",
    "qt6statemachine",
    "qt6spatialaudio",
    "qt6httpserver",
    "qt6networkauth",
    "qt6opengl",
    "qt6sql",
    "qt6test",
    "qt6concurrent",
    "qt6network",
    "qtnetwork",
    "opengl32sw",
    "_avif",
    "qt6opengl32",
)

KEEP_TRANSLATIONS = ("_zh_cn", "_zh_cn.qm", "qtbase_zh")


def _keep_binary(entry) -> bool:
    name = entry[0].lower().replace("\\", "/")
    base = name.rsplit("/", 1)[-1]
    if any(tag in base for tag in DROP_BINARIES):
        return False
    return True


def _keep_data(entry) -> bool:
    dest = entry[0].lower().replace("\\", "/")
    if "/translations/" in dest or dest.startswith("pyside6/translations"):
        return any(tag in dest for tag in KEEP_TRANSLATIONS)
    return True


a = Analysis(
    [str(PROJECT / "app" / "main.py")],
    pathex=[str(PROJECT)],
    binaries=[],
    datas=[(str(PROJECT / "app" / "assets"), "app/assets")],
    hiddenimports=["pypdfium2", "pypdfium2_raw"] + collect_submodules("app.tools"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
    optimize=1,
)

a.binaries = [entry for entry in a.binaries if _keep_binary(entry)]
a.datas = [entry for entry in a.datas if _keep_data(entry)]


# conda 环境把 libffi / openssl / expat 等放在 Library\bin，PyInstaller 找不到，
# 手动补进去（缺 ffi.dll 会导致 ctypes 导入失败，进而 pypdfium2 无法加载）。
def _add_conda_runtime_dlls() -> None:
    import sys

    lib_bin = Path(sys.prefix) / "Library" / "bin"
    if not lib_bin.is_dir():
        return
    wanted = (
        "ffi.dll",
        "libffi-8.dll",
        "libssl-3-x64.dll",
        "libcrypto-3-x64.dll",
        "libexpat.dll",
        "liblzma.dll",
        "LIBBZ2.dll",
        "libbz2.dll",
        "zlib.dll",
    )
    existing = {Path(dest).name.lower() for dest, _src, _kind in a.binaries}
    for name in wanted:
        source = lib_bin / name
        if source.is_file() and name.lower() not in existing:
            a.binaries.append((name, str(source), "BINARY"))


_add_conda_runtime_dlls()

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MiniTools",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON) if ICON.exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="MiniTools",
)
