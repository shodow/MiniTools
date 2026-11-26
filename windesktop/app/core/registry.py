"""工具注册表 —— 新增功能只需在 app/tools/<id>/tool.py 里声明一个 ToolSpec。"""

from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass, field
from typing import Callable, Iterable

from PySide6.QtWidgets import QWidget


@dataclass(frozen=True)
class ToolSpec:
    """一个工具卡片的全部元信息。"""

    id: str
    title: str
    summary: str
    badge: str                       # 卡片图标上的短文字，例如 "PDF"
    accent: str                      # 卡片主色 #RRGGBB
    page_factory: Callable[[], QWidget]
    order: int = 100
    keywords: tuple[str, ...] = field(default_factory=tuple)


_SPECS: dict[str, ToolSpec] = {}
_loaded = False


def register(spec: ToolSpec) -> ToolSpec:
    _SPECS[spec.id] = spec
    return spec


def discover() -> None:
    """加载工具声明。

    优先读 app/tools/__init__.py 里的 TOOL_MODULES（打包后唯一可靠的来源），
    再补一遍 pkgutil 扫描（源码运行时新加的工具不用改登记表也能出现）。
    """
    global _loaded
    if _loaded:
        return
    import app.tools as tools_pkg

    module_names: list[str] = list(getattr(tools_pkg, "TOOL_MODULES", ()))
    try:
        for info in pkgutil.iter_modules(tools_pkg.__path__):
            if info.ispkg:
                module_names.append(f"app.tools.{info.name}.tool")
    except Exception:  # noqa: BLE001 - 冻结环境下扫描不可用，忽略即可
        pass

    seen: set[str] = set()
    for name in module_names:
        if name in seen:
            continue
        seen.add(name)
        try:
            module = importlib.import_module(name)
        except Exception as exc:  # noqa: BLE001 - 单个工具坏了不影响其它工具
            print(f"[registry] 跳过工具 {name}: {exc}")
            continue
        spec = getattr(module, "TOOL", None)
        if isinstance(spec, ToolSpec):
            register(spec)
    _loaded = True


def all_tools() -> list[ToolSpec]:
    discover()
    return sorted(_SPECS.values(), key=lambda s: (s.order, s.id))


def get_tool(tool_id: str) -> ToolSpec | None:
    discover()
    return _SPECS.get(tool_id)


def search(text: str) -> list[ToolSpec]:
    text = text.strip().lower()
    if not text:
        return all_tools()
    hits = []
    for spec in all_tools():
        haystack = " ".join((spec.title, spec.summary, spec.id, *spec.keywords)).lower()
        if text in haystack:
            hits.append(spec)
    return hits


def iter_specs() -> Iterable[ToolSpec]:  # pragma: no cover - 便捷别名
    return all_tools()
