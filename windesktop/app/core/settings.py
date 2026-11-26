"""基于 QSettings 的轻量偏好存储（注册表 HKCU\\Software\\WinTools）。"""

from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import QSettings

from app import APP_NAME


def _store() -> QSettings:
    return QSettings(APP_NAME, APP_NAME)


def get(key: str, default: Any = None) -> Any:
    raw = _store().value(key, None)
    if raw is None:
        return default
    if isinstance(default, (dict, list, bool, int)) or isinstance(raw, str):
        try:
            return json.loads(raw) if isinstance(raw, str) else raw
        except (ValueError, TypeError):
            return raw
    return raw


def put(key: str, value: Any) -> None:
    _store().setValue(key, json.dumps(value, ensure_ascii=False))


def sync() -> None:
    _store().sync()
