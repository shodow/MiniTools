"""主窗口：卡片首页 + 工具子页面栈。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QStackedWidget

from app import APP_DISPLAY_NAME, APP_NAME, __version__
from app.core import registry
from app.ui.home_page import HomePage
from app.ui.icons import app_icon
from app.ui.tool_page import ToolPage


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_DISPLAY_NAME} v{__version__}")
        self.setWindowIcon(app_icon())
        self.setMinimumSize(940, 640)
        self.resize(1140, 780)

        self.stack = QStackedWidget(self)
        self.setCentralWidget(self.stack)
        self._pages: dict[str, ToolPage] = {}

        self.home = HomePage(self)
        self.home.open_tool.connect(self.open_tool)
        self.stack.addWidget(self.home)

    def open_tool(self, tool_id: str) -> None:
        spec = registry.get_tool(tool_id)
        if spec is None:
            return
        page = self._pages.get(tool_id)
        if page is None:
            page = spec.page_factory()
            page.setParent(self)
            page.back_requested.connect(self.show_home)
            self._pages[tool_id] = page
            self.stack.addWidget(page)
        self.stack.setCurrentWidget(page)
        page.on_shown()

    def show_home(self) -> None:
        self.stack.setCurrentWidget(self.home)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape and self.stack.currentWidget() is not self.home:
            self.show_home()
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event) -> None:  # noqa: N802
        for page in self._pages.values():
            shutdown = getattr(page, "shutdown", None)
            if callable(shutdown):
                shutdown()
        super().closeEvent(event)
