"""WinTools 入口。"""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app import APP_NAME, __version__
from app.core.paths import asset
from app.ui.icons import app_icon
from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme


def create_app(argv: list[str] | None = None) -> QApplication:
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, False)

    icon_file = asset("app.ico")
    app.setWindowIcon(QIcon(str(icon_file)) if icon_file.exists() else app_icon())
    apply_theme(app)
    return app


def main() -> int:
    if "--selftest" in sys.argv:
        from app.selftest import run_safe

        return run_safe()

    app = create_app()
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
