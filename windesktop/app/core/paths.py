"""运行时路径解析：区分源码运行与 PyInstaller 打包运行。"""

from __future__ import annotations

import sys
from pathlib import Path


def bundle_root() -> Path:
    """资源根目录：打包后是 _MEIPASS，源码运行是项目根目录。"""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return Path(__file__).resolve().parents[2]


def resource(*parts: str) -> Path:
    """拼出资源文件路径（app/assets 下的东西）。"""
    return bundle_root().joinpath(*parts)


def asset(*parts: str) -> Path:
    return resource("app", "assets", *parts)


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))
