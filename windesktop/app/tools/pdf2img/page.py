"""PDF 转图片页面。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core import settings
from app.core.registry import ToolSpec
from app.core.tasks import CancellableThread
from app.tools.pdf2img import converter
from app.tools.pdf2img.converter import ConvertOptions
from app.ui.tool_page import ToolPage
from app.ui.widgets import DropZone, human_size

SETTINGS_KEY = "pdf2img/options"


class ConvertWorker(CancellableThread):
    def __init__(self, files: list[Path], options: ConvertOptions, parent=None) -> None:
        super().__init__(parent)
        self._files = files
        self._options = options

    def run_job(self) -> object:
        def on_progress(done: int, total: int) -> None:
            self.progress.emit(done, total)

        return converter.convert_batch(
            self._files,
            self._options,
            cancel=self.cancel_event,
            on_progress=on_progress,
            on_log=self.message.emit,
        )


class PdfToImagePage(ToolPage):
    def __init__(self, spec: ToolSpec, parent: QWidget | None = None) -> None:
        super().__init__(spec, parent)
        self._files: list[Path] = []
        self._worker: ConvertWorker | None = None
        self._custom_dir: str | None = None
        self._last_dir: str = ""
        self._last_output: Path | None = None
        self._build_ui()
        self._load_settings()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        self.drop = DropZone(
            "拖拽 PDF 文件或文件夹到这里",
            "也可以点击此处选择文件，支持多选与整目录批量转换",
            self,
        )
        self.drop.paths_dropped.connect(self.add_paths)
        self.drop.clicked.connect(self.pick_files)
        self.body.addWidget(self.drop)

        middle = QHBoxLayout()
        middle.setSpacing(14)

        left = QVBoxLayout()
        left.setSpacing(8)
        list_head = QHBoxLayout()
        list_title = QLabel("待转换文件", self)
        list_title.setObjectName("sectionTitle")
        self.count_label = QLabel("0 个文件 / 0 页", self)
        self.count_label.setObjectName("hintText")
        list_head.addWidget(list_title)
        list_head.addStretch(1)
        list_head.addWidget(self.count_label)
        left.addLayout(list_head)

        self.file_list = QListWidget(self)
        self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.file_list.setMinimumWidth(380)
        self.file_list.setAlternatingRowColors(False)
        left.addWidget(self.file_list, 1)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.btn_files = QPushButton("选择文件", self)
        self.btn_folder = QPushButton("选择文件夹", self)
        self.btn_remove = QPushButton("移除选中", self)
        self.btn_clear = QPushButton("清空", self)
        for button in (self.btn_files, self.btn_folder, self.btn_remove, self.btn_clear):
            button.setObjectName("ghost")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_files.clicked.connect(self.pick_files)
        self.btn_folder.clicked.connect(self.pick_folder)
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_clear.clicked.connect(self.clear_files)
        for button in (self.btn_files, self.btn_folder, self.btn_remove, self.btn_clear):
            buttons.addWidget(button)
        buttons.addStretch(1)
        left.addLayout(buttons)

        middle.addLayout(left, 1)
        middle.addWidget(self._build_options(), 0)
        self.body.addLayout(middle, 1)

        progress_row = QHBoxLayout()
        progress_row.setSpacing(10)
        self.progress = QProgressBar(self)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.status = QLabel("就绪", self)
        self.status.setObjectName("hintText")
        self.status.setMinimumWidth(150)
        progress_row.addWidget(self.progress, 1)
        progress_row.addWidget(self.status)
        self.body.addLayout(progress_row)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.btn_open = QPushButton("打开输出位置", self)
        self.btn_open.setObjectName("ghost")
        self.btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open.clicked.connect(self.open_output)
        self.btn_open.hide()

        self.btn_cancel = QPushButton("取消", self)
        self.btn_cancel.setObjectName("ghost")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.cancel_conversion)
        self.btn_cancel.hide()

        self.btn_start = QPushButton("开始转换", self)
        self.btn_start.setObjectName("primary")
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.setMinimumWidth(110)
        self.btn_start.clicked.connect(self.start_conversion)

        actions.addStretch(1)
        actions.addWidget(self.btn_open)
        actions.addWidget(self.btn_cancel)
        actions.addWidget(self.btn_start)
        self.body.addLayout(actions)

        self.log = QPlainTextEdit(self)
        self.log.setObjectName("log")
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(800)
        self.log.setFixedHeight(92)
        self.log.setPlaceholderText("转换日志会显示在这里")
        self.body.addWidget(self.log)

    def _build_options(self) -> QGroupBox:
        box = QGroupBox("转换设置", self)
        box.setFixedWidth(340)
        form = QFormLayout(box)
        form.setContentsMargins(14, 20, 14, 12)
        form.setSpacing(9)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self.fmt_combo = QComboBox(box)
        self.fmt_combo.addItem("PNG（无损）", "png")
        self.fmt_combo.addItem("JPG（体积小）", "jpg")
        self.fmt_combo.currentIndexChanged.connect(self._on_format_changed)
        form.addRow("图片格式", self.fmt_combo)

        self.dpi_spin = QSpinBox(box)
        self.dpi_spin.setRange(48, 1200)
        self.dpi_spin.setSingleStep(50)
        self.dpi_spin.setValue(200)
        self.dpi_spin.setSuffix(" DPI")
        form.addRow("分辨率", self.dpi_spin)

        self.quality_spin = QSpinBox(box)
        self.quality_spin.setRange(1, 100)
        self.quality_spin.setValue(90)
        self.quality_spin.setSuffix(" %")
        form.addRow("JPG 质量", self.quality_spin)

        self.range_edit = QLineEdit(box)
        self.range_edit.setPlaceholderText("留空 = 全部，例：1-5,8,10-")
        form.addRow("页码范围", self.range_edit)

        self.pad_spin = QSpinBox(box)
        self.pad_spin.setRange(0, 6)
        self.pad_spin.setValue(3)
        self.pad_spin.setSuffix(" 位")
        self.pad_spin.setSpecialValueText("不补零")
        form.addRow("页码位数", self.pad_spin)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(6)
        self.mode_combo = QComboBox(box)
        self.mode_combo.addItem("PDF 原目录", "same")
        self.mode_combo.addItem("同名子文件夹", "subfolder")
        self.mode_combo.addItem("自定义目录", "custom")
        self.mode_combo.setCurrentIndex(1)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_row.addWidget(self.mode_combo, 1)
        self.btn_dir = QPushButton("…", box)
        self.btn_dir.setObjectName("ghost")
        self.btn_dir.setFixedWidth(34)
        self.btn_dir.clicked.connect(self.pick_custom_dir)
        mode_row.addWidget(self.btn_dir)
        form.addRow("输出位置", mode_row)

        self.dir_label = QLabel("", box)
        self.dir_label.setObjectName("hintText")
        form.addRow("", self.dir_label)

        self.conflict_combo = QComboBox(box)
        self.conflict_combo.addItem("覆盖", "overwrite")
        self.conflict_combo.addItem("跳过", "skip")
        self.conflict_combo.addItem("自动重命名", "rename")
        form.addRow("已存在文件", self.conflict_combo)

        self.password_edit = QLineEdit(box)
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("加密 PDF 才需要填")
        form.addRow("PDF 密码", self.password_edit)

        self.recursive_check = QCheckBox("包含子文件夹", box)
        self.recursive_check.setChecked(True)
        form.addRow("", self.recursive_check)

        self._on_format_changed()
        self._on_mode_changed()
        return box

    # ------------------------------------------------------------- 选项联动
    def _on_format_changed(self) -> None:
        is_jpg = self.fmt_combo.currentData() == "jpg"
        self.quality_spin.setEnabled(is_jpg)

    def _on_mode_changed(self) -> None:
        mode = self.mode_combo.currentData()
        self.btn_dir.setEnabled(mode == "custom")
        self._update_dir_hint()

    def _update_dir_hint(self) -> None:
        mode = self.mode_combo.currentData()
        if mode == "custom":
            text = self._custom_dir or "尚未选择目录"
        elif mode == "subfolder":
            text = "输出到 <原目录>/<PDF 名>_images/"
        else:
            text = "输出到 PDF 所在目录"
        self.dir_label.setText(text)
        self.dir_label.setToolTip(text)

    # ------------------------------------------------------------- 文件管理
    def add_paths(self, paths: list[str]) -> None:
        pdfs = converter.collect_pdfs(
            [Path(p) for p in paths], recursive=self.recursive_check.isChecked()
        )
        if not pdfs:
            QMessageBox.information(self, "没有可转换的文件", "所选位置没有找到 PDF 文件。")
            return

        existing = {path.resolve() for path in self._files}
        added = 0
        for path in pdfs:
            key = path.resolve()
            if key in existing:
                continue
            existing.add(key)
            try:
                pages = converter.probe(path, self.password_edit.text())
                detail = f"{pages} 页"
            except Exception:  # noqa: BLE001 - 页数读不到不影响后续转换尝试
                detail = "无法读取"
            item = QListWidgetItem(f"{path.name}   ·   {detail}   ·   {human_size(path.stat().st_size)}")
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            item.setToolTip(str(path))
            self.file_list.addItem(item)
            self._files.append(path)
            added += 1

        self._last_dir = str(Path(paths[0]).parent)
        self._refresh_summary()
        if added:
            self._append_log(f"已添加 {added} 个 PDF 文件")

    def pick_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择 PDF 文件", self._last_dir, "PDF 文件 (*.pdf)"
        )
        if files:
            self.add_paths(files)

    def pick_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择包含 PDF 的文件夹", self._last_dir)
        if folder:
            self.add_paths([folder])

    def pick_custom_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择输出目录", self._custom_dir or self._last_dir)
        if folder:
            self._custom_dir = folder
            self._update_dir_hint()

    def remove_selected(self) -> None:
        rows = sorted({self.file_list.row(item) for item in self.file_list.selectedItems()}, reverse=True)
        for row in rows:
            item = self.file_list.takeItem(row)
            if item is not None:
                path = Path(item.data(Qt.ItemDataRole.UserRole))
                self._files = [p for p in self._files if p != path]
        self._refresh_summary()

    def clear_files(self) -> None:
        self.file_list.clear()
        self._files.clear()
        self._refresh_summary()

    def _refresh_summary(self) -> None:
        total_pages = 0
        for row in range(self.file_list.count()):
            text = self.file_list.item(row).text()
            total_pages += _extract_pages(text)
        self.count_label.setText(f"{len(self._files)} 个文件 / {total_pages} 页")
        self.btn_start.setEnabled(bool(self._files) and not self._is_running())

    # ------------------------------------------------------------- 转换流程
    def _read_options(self) -> ConvertOptions:
        return ConvertOptions(
            fmt=str(self.fmt_combo.currentData()),
            dpi=self.dpi_spin.value(),
            jpeg_quality=self.quality_spin.value(),
            page_range=self.range_edit.text(),
            zero_pad=self.pad_spin.value(),
            output_mode=str(self.mode_combo.currentData()),
            custom_dir=self._custom_dir,
            on_conflict=str(self.conflict_combo.currentData()),
            password=self.password_edit.text(),
        )

    def start_conversion(self) -> None:
        if self._is_running():
            return
        if not self._files:
            QMessageBox.information(self, "还没有文件", "请先选择 PDF 文件或文件夹。")
            return

        options = self._read_options()
        try:
            converter.check_page_range(options.page_range)
        except ValueError as exc:
            QMessageBox.warning(self, "页码范围", str(exc))
            return
        if options.output_mode == "custom":
            if not self._custom_dir or not Path(self._custom_dir).is_dir():
                QMessageBox.warning(self, "输出目录", "请先选择一个存在的自定义输出目录。")
                return

        self._save_settings()
        self.log.clear()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.status.setText("准备中…")
        self._set_running(True)

        worker = ConvertWorker(list(self._files), options, self)
        worker.progress.connect(self._on_progress)
        worker.message.connect(self._append_log)
        worker.result.connect(self._on_finished)
        worker.failed.connect(self._on_failed)
        worker.finished.connect(self._on_worker_finished)
        self._worker = worker
        worker.start()

    def cancel_conversion(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            self.status.setText("正在取消…")
            self.btn_cancel.setEnabled(False)

    def _on_progress(self, done: int, total: int) -> None:
        percent = int(done * 100 / total) if total else 0
        self.progress.setValue(min(100, percent))
        self.status.setText(f"转换中… {done}/{total} 页")

    def _on_finished(self, batch: object) -> None:
        result: converter.BatchResult = batch  # type: ignore[assignment]
        if result.files:
            outputs = [out for f in result.files for out in f.outputs]
            if outputs:
                self._last_output = outputs[0].parent
                self.btn_open.show()
        if result.cancelled:
            self.status.setText(f"已取消，已完成 {result.page_count} 页")
            self._append_log(f"已取消：成功 {result.ok_count} 个文件，失败 {result.fail_count} 个")
        else:
            self.progress.setValue(100)
            self.status.setText(f"完成：{result.ok_count} 个文件 / {result.page_count} 页")
            self._append_log(
                f"全部结束：成功 {result.ok_count} 个文件，失败 {result.fail_count} 个，共 {result.page_count} 页"
            )
        failures = [f for f in result.files if not f.ok]
        if failures:
            detail = "\n".join(f"· {f.source.name}：{f.error}" for f in failures[:10])
            if len(failures) > 10:
                detail += f"\n… 另有 {len(failures) - 10} 个失败"
            QMessageBox.warning(self, "部分文件转换失败", detail)

    def _on_failed(self, message: str) -> None:
        self.status.setText("出错")
        self._append_log(f"错误：{message}")
        QMessageBox.critical(self, "转换失败", message)

    def _on_worker_finished(self) -> None:
        self._worker = None
        self._set_running(False)

    def _is_running(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    def _set_running(self, running: bool) -> None:
        self.btn_start.setVisible(not running)
        self.btn_cancel.setVisible(running)
        self.btn_cancel.setEnabled(running)
        for widget in (
            self.drop,
            self.btn_files,
            self.btn_folder,
            self.btn_remove,
            self.btn_clear,
            self.fmt_combo,
            self.dpi_spin,
            self.quality_spin,
            self.range_edit,
            self.pad_spin,
            self.mode_combo,
            self.btn_dir,
            self.conflict_combo,
            self.password_edit,
            self.recursive_check,
            self.file_list,
        ):
            widget.setEnabled(not running)
        if not running:
            self._on_format_changed()
            self.btn_start.setEnabled(bool(self._files))

    def _append_log(self, text: str) -> None:
        self.log.appendPlainText(text)

    def open_output(self) -> None:
        target = self._last_output or (Path(self._custom_dir) if self._custom_dir else None)
        if target and Path(target).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))

    # ------------------------------------------------------------- 设置持久化
    def _save_settings(self) -> None:
        settings.put(
            SETTINGS_KEY,
            {
                "fmt": self.fmt_combo.currentData(),
                "dpi": self.dpi_spin.value(),
                "quality": self.quality_spin.value(),
                "zero_pad": self.pad_spin.value(),
                "output_mode": self.mode_combo.currentData(),
                "on_conflict": self.conflict_combo.currentData(),
                "custom_dir": self._custom_dir,
                "recursive": self.recursive_check.isChecked(),
            },
        )

    def _load_settings(self) -> None:
        data = settings.get(SETTINGS_KEY, {}) or {}
        if not isinstance(data, dict):
            return
        try:
            fmt = data.get("fmt")
            if fmt:
                index = self.fmt_combo.findData(fmt)
                if index >= 0:
                    self.fmt_combo.setCurrentIndex(index)
            if isinstance(data.get("dpi"), int):
                self.dpi_spin.setValue(data["dpi"])
            if isinstance(data.get("quality"), int):
                self.quality_spin.setValue(data["quality"])
            if isinstance(data.get("zero_pad"), int):
                self.pad_spin.setValue(data["zero_pad"])
            if data.get("output_mode"):
                index = self.mode_combo.findData(data["output_mode"])
                if index >= 0:
                    self.mode_combo.setCurrentIndex(index)
            if data.get("on_conflict"):
                index = self.conflict_combo.findData(data["on_conflict"])
                if index >= 0:
                    self.conflict_combo.setCurrentIndex(index)
            if data.get("custom_dir"):
                self._custom_dir = str(data["custom_dir"])
            if isinstance(data.get("recursive"), bool):
                self.recursive_check.setChecked(data["recursive"])
        except Exception:  # noqa: BLE001 - 配置损坏时用默认值即可
            pass
        self._update_dir_hint()

    def shutdown(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(3000)


def _extract_pages(item_text: str) -> int:
    parts = [piece.strip() for piece in item_text.split("·")]
    for piece in parts:
        if piece.endswith("页"):
            try:
                return int(piece[:-1])
            except ValueError:
                return 0
    return 0
