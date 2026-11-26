"""后台任务基础设施：QThread + 信号，供各工具页面复用。"""

from __future__ import annotations

import threading
from typing import Callable

from PySide6.QtCore import QThread, Signal


class CancellableThread(QThread):
    """带取消令牌的后台线程。

    子类实现 run_job()；进度通过 progress / message 信号回传，
    结果通过 result / failed 信号回传。
    """

    progress = Signal(int, int)          # (已完成, 总数)
    message = Signal(str)                # 单行日志
    result = Signal(object)              # 成功结果
    failed = Signal(str)                 # 失败原因

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._cancel = threading.Event()

    # ---- 提供给子类使用 ----
    @property
    def cancel_event(self) -> threading.Event:
        return self._cancel

    def is_cancelled(self) -> bool:
        return self._cancel.is_set()

    def cancel(self) -> None:
        self._cancel.set()

    def run_job(self) -> object:  # pragma: no cover - 由子类覆盖
        raise NotImplementedError

    # ---- Qt 入口 ----
    def run(self) -> None:  # noqa: D102
        try:
            value = self.run_job()
        except Exception as exc:  # noqa: BLE001 - 统一转成 UI 提示
            if self.is_cancelled():
                self.failed.emit("已取消")
            else:
                self.failed.emit(f"{type(exc).__name__}: {exc}")
            return
        self.result.emit(value)


class ThreadReporter:
    """把线程安全的进度回调包装成批量发送，避免信号风暴。"""

    def __init__(
        self,
        emit_progress: Callable[[int, int], None],
        emit_message: Callable[[str], None],
        throttle: int = 1,
    ) -> None:
        self._emit_progress = emit_progress
        self._emit_message = emit_message
        self._throttle = max(1, throttle)
        self._pending = 0
        self._last = (0, 0)
        self._lock = threading.Lock()

    def progress(self, done: int, total: int, force: bool = False) -> None:
        with self._lock:
            self._last = (done, total)
            self._pending += 1
            if not force and self._pending < self._throttle:
                return
            self._pending = 0
        self._emit_progress(done, total)

    def flush(self) -> None:
        with self._lock:
            done, total = self._last
        self._emit_progress(done, total)

    def log(self, text: str) -> None:
        self._emit_message(text)
