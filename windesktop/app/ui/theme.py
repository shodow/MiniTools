"""全局样式（浅色，卡片式）。"""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

FONT_FAMILY = "Microsoft YaHei UI"
FALLBACK_FAMILY = "Segoe UI"

QSS = """
QWidget {
    color: #1F2937;
    font-size: 13px;
}
QMainWindow, QWidget#pageRoot { background: #F4F6F9; }

#appTitle { font-size: 13px; font-weight: 600; color: #2563EB; }
#homeTitle { font-size: 23px; font-weight: 700; color: #111827; }
#homeSubtitle { font-size: 13px; color: #6B7280; }
#pageHeaderTitle { font-size: 20px; font-weight: 700; color: #111827; }
#hintText { font-size: 12px; color: #6B7280; }
#inlineHint { font-size: 12px; color: #6B7280; }
#sectionTitle { font-size: 13px; font-weight: 600; color: #374151; }
#monoPath { font-size: 11px; color: #6B7280; }

/* ---------- 卡片 ---------- */
#toolCard {
    background: #FFFFFF;
    border: 1px solid #E5E8EE;
    border-radius: 14px;
}
#toolCard:hover {
    background: #F8FAFF;
    border: 1px solid #A9C3F5;
}
#toolCard:focus {
    border: 1px solid #2563EB;
}
#cardTitle { font-size: 15px; font-weight: 700; color: #111827; }
#cardSummary { font-size: 12px; color: #6B7280; }
#cardArrow { font-size: 14px; color: #C3CAD6; }
#toolCard:hover #cardArrow { color: #2563EB; }

/* ---------- 按钮 ---------- */
QPushButton#primary {
    background: #2563EB; color: #FFFFFF; border: none; border-radius: 8px;
    padding: 8px 20px; font-weight: 600;
}
QPushButton#primary:hover { background: #1D4ED8; }
QPushButton#primary:pressed { background: #1E40AF; }
QPushButton#primary:disabled { background: #B7CBF3; color: #F1F5FD; }

QPushButton#ghost {
    background: #FFFFFF; color: #374151; border: 1px solid #D8DDE5;
    border-radius: 8px; padding: 7px 14px;
}
QPushButton#ghost:hover { background: #F3F5F9; border-color: #B9C1CE; }
QPushButton#ghost:disabled { color: #A9B1BF; border-color: #E5E8EE; }
QPushButton#link {
    background: transparent; border: none; color: #2563EB; padding: 2px 4px;
}
QPushButton#link:hover { color: #1D4ED8; text-decoration: underline; }

/* ---------- 输入控件 ---------- */
QLineEdit, QComboBox, QSpinBox {
    background: #FFFFFF; border: 1px solid #D8DDE5; border-radius: 8px;
    padding: 6px 9px; min-height: 20px;
    selection-background-color: #DCE8FD; selection-color: #111827;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 1px solid #2563EB; }
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {
    background: #F3F5F9; color: #98A1B0;
}
QComboBox::drop-down { border: none; width: 22px; }
QComboBox::down-arrow {
    image: url("@ASSETS@/chevron_down.png");
    width: 10px; height: 6px; margin-right: 8px;
}
QComboBox QAbstractItemView {
    background: #FFFFFF; border: 1px solid #E5E8EE; outline: none;
    selection-background-color: #E8F0FE; selection-color: #111827; padding: 4px;
}
QSpinBox::up-button {
    subcontrol-origin: border; subcontrol-position: top right;
    width: 18px; border: none; background: transparent;
}
QSpinBox::down-button {
    subcontrol-origin: border; subcontrol-position: bottom right;
    width: 18px; border: none; background: transparent;
}
QSpinBox::up-arrow { image: url("@ASSETS@/chevron_up.png"); width: 9px; height: 5px; }
QSpinBox::down-arrow { image: url("@ASSETS@/chevron_down.png"); width: 9px; height: 5px; }

QCheckBox { spacing: 7px; }
QCheckBox::indicator {
    width: 16px; height: 16px; border: 1px solid #C7CED9; border-radius: 4px;
    background: #FFFFFF;
}
QCheckBox::indicator:checked {
    background: #2563EB; border-color: #2563EB;
    image: url(:/qt-project.org/styles/commonstyle/images/standardbutton-apply-16.png);
}
QCheckBox:disabled { color: #A9B1BF; }

QGroupBox {
    background: #FFFFFF; border: 1px solid #E5E8EE; border-radius: 12px;
    margin-top: 16px; padding: 12px 12px 10px 12px;
}
QGroupBox::title {
    subcontrol-origin: margin; left: 12px; padding: 0 5px;
    color: #374151; font-weight: 600;
}

/* ---------- 列表 / 滚动 ---------- */
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #D3D9E2; border-radius: 5px; min-height: 32px; }
QScrollBar::handle:vertical:hover { background: #B9C1CE; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }

QListWidget {
    background: #FFFFFF; border: 1px solid #E5E8EE; border-radius: 12px; padding: 5px;
    outline: none;
}
QListWidget::item { padding: 7px 9px; border-radius: 7px; color: #374151; }
QListWidget::item:hover { background: #F5F7FA; }
QListWidget::item:selected { background: #E8F0FE; color: #111827; }

#dropZone {
    background: #FAFBFD; border: 2px dashed #CBD3DF; border-radius: 12px;
}
#dropZone[dragActive="true"] {
    background: #EFF5FF; border: 2px dashed #2563EB;
}
#dropTitle { font-size: 14px; font-weight: 600; color: #374151; }

/* ---------- 预览 ---------- */
#previewBox {
    background: #FFFFFF;
    border: 1px solid #E5E8EE;
    border-radius: 12px;
    padding: 2px;
}
QPlainTextEdit#watermarkText {
    background: #FFFFFF; border: 1px solid #D8DDE5; border-radius: 8px;
    padding: 5px 7px; font-size: 13px;
    selection-background-color: #DCE8FD; selection-color: #111827;
}
QPlainTextEdit#watermarkText:focus { border: 1px solid #2563EB; }

/* ---------- 进度 / 日志 ---------- */
QProgressBar {
    background: #E9EDF3; border: none; border-radius: 5px; height: 10px;
    text-align: center; color: transparent;
}
QProgressBar::chunk { background: #2563EB; border-radius: 5px; }

QPlainTextEdit#log {
    background: #FFFFFF; border: 1px solid #E5E8EE; border-radius: 10px;
    padding: 6px; color: #4B5563;
    font-family: "Cascadia Mono", "Consolas", monospace; font-size: 12px;
}

QToolTip {
    background: #111827; color: #F9FAFB; border: none; border-radius: 6px; padding: 5px 8px;
}
"""


def apply_theme(app: QApplication) -> None:
    from app.core.paths import asset

    font = QFont(FONT_FAMILY, 10)
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)
    assets_dir = asset().as_posix()
    app.setStyleSheet(QSS.replace("@ASSETS@", assets_dir))
