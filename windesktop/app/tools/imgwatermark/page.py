"""图片加水印页面。"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image
from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core import settings
from app.core.registry import ToolSpec
from app.core.tasks import CancellableThread
from app.tools.imgwatermark import converter
from app.tools.imgwatermark.converter import WatermarkOptions
from app.ui.tool_page import ToolPage
from app.ui.widgets import DropZone, filesize_of

SETTINGS_KEY = "imgwatermark/options"

COLORS = (
    ("白色", "#FFFFFF"),
    ("黑色", "#111111"),
    ("浅灰", "#D0D0D0"),
    ("深灰", "#555555"),
)


def _inline_label(text: str, parent: QWidget | None = None) -> QLabel:
    label = QLabel(text, parent)
    label.setObjectName("inlineHint")
    return label


def _placeholder_image(width: int = 960, height: int = 540) -> Image.Image:
    """没有选图时用的示例底图（浅色渐变，方便看清水印效果）。"""
    gradient = Image.linear_gradient("L").resize((width, height))
    soft = gradient.point(lambda v: 240 - v // 5)
    base = Image.merge(
        "RGB",
        (
            soft.point(lambda v: max(0, v - 8)),
            soft,
            soft.point(lambda v: min(255, v + 10)),
        ),
    )
    from PIL import ImageDraw

    draw = ImageDraw.Draw(base)
    draw.rounded_rectangle(
        (width * 0.12, height * 0.22, width * 0.55, height * 0.62),
        radius=24,
        fill=(255, 255, 255, 255),
        outline=(226, 232, 240),
        width=3,
    )
    draw.ellipse(
        (width * 0.62, height * 0.30, width * 0.86, height * 0.54),
        fill=(219, 234, 254),
    )
    draw.rectangle(
        (width * 0.12, height * 0.72, width * 0.88, height * 0.75),
        fill=(203, 213, 225),
    )
    return base


class WatermarkWorker(CancellableThread):
    def __init__(self, files: list[Path], options: WatermarkOptions, parent=None) -> None:
        super().__init__(parent)
        self._files = files
        self._options = options

    def run_job(self) -> object:
        return converter.convert_batch(
            self._files,
            self._options,
            cancel=self.cancel_event,
            on_progress=lambda done, total: self.progress.emit(done, total),
            on_log=self.message.emit,
        )


class ImageWatermarkPage(ToolPage):
    def __init__(self, spec: ToolSpec, parent: QWidget | None = None) -> None:
        super().__init__(spec, parent)
        self._files: list[Path] = []
        self._worker: WatermarkWorker | None = None
        self._custom_dir: str | None = None
        self._last_dir: str = ""
        self._last_output: Path | None = None

        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(180)
        self._preview_timer.timeout.connect(self.refresh_preview)

        self._build_ui()
        self._connect_preview_triggers()
        self._load_settings()
        self.refresh_preview()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        columns = QHBoxLayout()
        columns.setSpacing(14)

        # ---- 左列：拖拽区 + 文件列表 ----
        left = QVBoxLayout()
        left.setSpacing(8)
        self.drop = DropZone(
            "拖拽 PNG / JPG 图片或文件夹到这里",
            "也可以点击此处选择图片，支持多选与整目录批量处理",
            self,
        )
        self.drop.paths_dropped.connect(self.add_paths)
        self.drop.clicked.connect(self.pick_files)
        left.addWidget(self.drop)

        list_head = QHBoxLayout()
        list_title = QLabel("待处理图片", self)
        list_title.setObjectName("sectionTitle")
        self.count_label = QLabel("0 张图片", self)
        self.count_label.setObjectName("hintText")
        list_head.addWidget(list_title)
        list_head.addStretch(1)
        list_head.addWidget(self.count_label)
        left.addLayout(list_head)

        self.file_list = QListWidget(self)
        self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.file_list.setMinimumWidth(340)
        left.addWidget(self.file_list, 1)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.btn_files = QPushButton("选择图片", self)
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

        self.preview = QLabel(self)
        self.preview.setObjectName("previewBox")
        self.preview.setMinimumHeight(140)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left.addWidget(self.preview, 0)

        self.preview_hint = QLabel("预览", self)
        self.preview_hint.setObjectName("hintText")
        self.preview_hint.setAlignment(Qt.AlignmentFlag.AlignRight)
        left.addWidget(self.preview_hint, 0)
        columns.addLayout(left, 1)

        # ---- 右列：设置（内容多时可滚动）----
        right = QVBoxLayout()
        right.setSpacing(0)
        self.options_scroll = QScrollArea(self)
        self.options_scroll.setWidgetResizable(True)
        self.options_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.options_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.options_scroll.setFixedWidth(360)
        self.options_scroll.setWidget(self._build_options())
        right.addWidget(self.options_scroll, 1)
        columns.addLayout(right, 0)
        self.body.addLayout(columns, 1)

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

        self.btn_start = QPushButton("开始添加水印", self)
        self.btn_start.setObjectName("primary")
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.setMinimumWidth(120)
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
        self.log.setFixedHeight(76)
        self.log.setPlaceholderText("处理日志会显示在这里")
        self.body.addWidget(self.log)

    def _build_options(self) -> QGroupBox:
        box = QGroupBox("水印设置", self)
        form = QFormLayout(box)
        form.setContentsMargins(14, 20, 14, 12)
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self.text_edit = QPlainTextEdit(box)
        self.text_edit.setPlaceholderText("例如：© 我的照片 2026\n支持中文，换行会变成多行水印")
        self.text_edit.setFixedHeight(58)
        self.text_edit.setObjectName("watermarkText")
        form.addRow("水印文字", self.text_edit)

        self.opacity_spin = QSpinBox(box)
        self.opacity_spin.setRange(0, 100)
        self.opacity_spin.setValue(75)
        self.opacity_spin.setSuffix(" %")
        self.opacity_spin.setMinimumWidth(84)

        self.size_spin = QSpinBox(box)
        self.size_spin.setRange(6, 400)
        self.size_spin.setValue(20)
        self.size_spin.setSuffix(" px")
        self.size_spin.setMinimumWidth(84)

        opacity_row = QHBoxLayout()
        opacity_row.setSpacing(6)
        opacity_row.addWidget(self.opacity_spin, 1)
        opacity_row.addWidget(_inline_label("字号", box))
        opacity_row.addWidget(self.size_spin, 1)
        form.addRow("透明度", opacity_row)

        self.spacing_spin = QSpinBox(box)
        self.spacing_spin.setRange(0, 1000)
        self.spacing_spin.setValue(60)
        self.spacing_spin.setSuffix(" px")
        self.spacing_spin.setMinimumWidth(84)

        self.angle_spin = QSpinBox(box)
        self.angle_spin.setRange(0, 90)
        self.angle_spin.setValue(45)
        self.angle_spin.setSuffix(" °")
        self.angle_spin.setMinimumWidth(84)

        layout_row = QHBoxLayout()
        layout_row.setSpacing(6)
        layout_row.addWidget(self.spacing_spin, 1)
        layout_row.addWidget(_inline_label("角度", box))
        layout_row.addWidget(self.angle_spin, 1)
        form.addRow("水印间距", layout_row)

        self.color_combo = QComboBox(box)
        for name, value in COLORS:
            self.color_combo.addItem(name, value)
        self.color_combo.addItem("自定义…", "__custom__")
        self.color_combo.currentIndexChanged.connect(self._on_color_changed)
        form.addRow("文字颜色", self.color_combo)

        self.outline_check = QCheckBox("描边（浅色背景也看得清）", box)
        self.outline_check.setChecked(True)
        form.addRow("", self.outline_check)

        self.fmt_combo = QComboBox(box)
        self.fmt_combo.addItem("保持原格式", "keep")
        self.fmt_combo.addItem("PNG（无损）", "png")
        self.fmt_combo.addItem("JPG（体积小）", "jpg")
        self.fmt_combo.currentIndexChanged.connect(self._on_format_changed)
        form.addRow("输出格式", self.fmt_combo)

        self.quality_spin = QSpinBox(box)
        self.quality_spin.setRange(1, 100)
        self.quality_spin.setValue(92)
        self.quality_spin.setSuffix(" %")
        form.addRow("JPG 质量", self.quality_spin)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(6)
        self.mode_combo = QComboBox(box)
        self.mode_combo.addItem("原目录", "same")
        self.mode_combo.addItem("同名子文件夹", "subfolder")
        self.mode_combo.addItem("自定义目录", "custom")
        self.mode_combo.setCurrentIndex(1)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_row.addWidget(self.mode_combo, 1)
        self.btn_dir = QPushButton("浏览", box)
        self.btn_dir.setObjectName("ghost")
        self.btn_dir.setFixedWidth(52)
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

        self.recursive_check = QCheckBox("包含子文件夹", box)
        self.recursive_check.setChecked(True)
        form.addRow("", self.recursive_check)

        self._custom_color: str | None = None
        self._on_format_changed()
        self._on_mode_changed()
        return box

    def _connect_preview_triggers(self) -> None:
        self.text_edit.textChanged.connect(self._schedule_preview)
        for spin in (self.opacity_spin, self.size_spin, self.spacing_spin, self.angle_spin):
            spin.valueChanged.connect(self._schedule_preview)
        self.color_combo.currentIndexChanged.connect(self._schedule_preview)
        self.outline_check.toggled.connect(self._schedule_preview)
        self.fmt_combo.currentIndexChanged.connect(self._schedule_preview)

    def _schedule_preview(self) -> None:
        if self._is_running():
            return
        self._preview_timer.start()

    # ------------------------------------------------------------- 选项联动
    def _on_format_changed(self) -> None:
        self.quality_spin.setEnabled(self.fmt_combo.currentData() == "jpg")

    def _on_mode_changed(self) -> None:
        mode = self.mode_combo.currentData()
        self.btn_dir.setEnabled(mode == "custom")
        self._update_dir_hint()

    def _update_dir_hint(self) -> None:
        mode = self.mode_combo.currentData()
        if mode == "custom":
            text = self._custom_dir or "尚未选择目录"
        elif mode == "subfolder":
            text = "输出到 <原目录>/<图片名>_watermark/"
        else:
            text = "输出到图片所在目录"
        self.dir_label.setText(text)
        self.dir_label.setToolTip(text)

    def _current_color(self) -> str:
        data = self.color_combo.currentData()
        if data == "__custom__":
            return self._custom_color or "#FFFFFF"
        return str(data or "#FFFFFF")

    def _on_color_changed(self) -> None:
        if self.color_combo.currentData() == "__custom__":
            color = QColorDialog.getColor(
                QColor(self._custom_color or "#3B82F6"), self, "选择水印颜色"
            )
            if color.isValid():
                self._custom_color = color.name().upper()
                index = self.color_combo.findData("__custom__")
                self.color_combo.setItemText(index, f"自定义 {self._custom_color}")
                self.color_combo.setCurrentIndex(index)
            else:
                if self._custom_color:
                    index = self.color_combo.findData("__custom__")
                    self.color_combo.setItemText(index, f"自定义 {self._custom_color}")
                    self.color_combo.setCurrentIndex(index)
                else:
                    self.color_combo.setCurrentIndex(0)
        self._schedule_preview()

    # ------------------------------------------------------------- 文件管理
    def add_paths(self, paths: list[str]) -> None:
        images = converter.collect_images(
            [Path(p) for p in paths], recursive=self.recursive_check.isChecked()
        )
        if not images:
            QMessageBox.information(self, "没有可处理的图片", "所选位置没有找到 PNG / JPG 图片。")
            return

        existing = {path.resolve() for path in self._files}
        added = 0
        for path in images:
            key = path.resolve()
            if key in existing:
                continue
            existing.add(key)
            try:
                with Image.open(path) as probe:
                    detail = f"{probe.width}×{probe.height}"
            except Exception:  # noqa: BLE001
                detail = "无法读取"
            item = QListWidgetItem(f"{path.name}   ·   {detail}   ·   {filesize_of(path)}")
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            item.setToolTip(str(path))
            self.file_list.addItem(item)
            self._files.append(path)
            added += 1

        self._last_dir = str(Path(paths[0]).parent)
        self._refresh_summary()
        if added:
            self._append_log(f"已添加 {added} 张图片")
            self._schedule_preview()

    def pick_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择图片",
            self._last_dir,
            "图片 (*.png *.jpg *.jpeg *.bmp *.webp);;所有文件 (*.*)",
        )
        if files:
            self.add_paths(files)

    def pick_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择包含图片的文件夹", self._last_dir)
        if folder:
            self.add_paths([folder])

    def pick_custom_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "选择输出目录", self._custom_dir or self._last_dir
        )
        if folder:
            self._custom_dir = folder
            self._update_dir_hint()

    def remove_selected(self) -> None:
        rows = sorted(
            {self.file_list.row(item) for item in self.file_list.selectedItems()}, reverse=True
        )
        for row in rows:
            item = self.file_list.takeItem(row)
            if item is not None:
                path = Path(item.data(Qt.ItemDataRole.UserRole))
                self._files = [p for p in self._files if p != path]
        self._refresh_summary()
        self._schedule_preview()

    def clear_files(self) -> None:
        self.file_list.clear()
        self._files.clear()
        self._refresh_summary()
        self._schedule_preview()

    def _refresh_summary(self) -> None:
        self.count_label.setText(f"{len(self._files)} 张图片")
        self.btn_start.setEnabled(bool(self._files) and not self._is_running())

    # ------------------------------------------------------------- 预览
    def refresh_preview(self) -> None:
        if self._is_running():
            return
        options = self._read_options()
        source = self._files[0] if self._files else None
        base: Image.Image | None = None
        if source is not None:
            try:
                with Image.open(source) as raw:
                    raw.load()
                    base = raw.copy()
            except Exception:  # noqa: BLE001 - 读不出来就用示例图
                base = None
        if base is None:
            base = _placeholder_image()

        max_w = max(240, self.preview.width() - 8)
        max_h = max(80, self.preview.height() - 8)
        thumb = base.copy()
        thumb.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        factor = thumb.width / max(1, base.width)
        scaled = WatermarkOptions(
            text=options.text,
            opacity=options.opacity,
            font_size=max(6, int(round(options.font_size * factor))),
            spacing=max(2, int(round(options.spacing * factor))),
            angle=options.angle,
            color=options.color,
            outline=options.outline,
            font_path=options.font_path,
        )
        if not options.text.strip():
            self.preview.setPixmap(self._to_pixmap(thumb))
            self.preview_hint.setText("预览")
        else:
            try:
                marked = converter.apply_watermark(thumb, scaled)
            except Exception:  # noqa: BLE001
                marked = thumb
            self.preview.setPixmap(self._to_pixmap(marked))
            self.preview_hint.setText(f"预览 {factor * 100:.0f}%")

    @staticmethod
    def _to_pixmap(image: Image.Image) -> QPixmap:
        buffer = io.BytesIO()
        image.convert("RGBA").save(buffer, format="PNG")
        pixmap = QPixmap()
        pixmap.loadFromData(buffer.getvalue(), "PNG")
        return pixmap

    # ------------------------------------------------------------- 转换流程
    def _read_options(self) -> WatermarkOptions:
        return WatermarkOptions(
            text=self.text_edit.toPlainText(),
            opacity=self.opacity_spin.value(),
            font_size=self.size_spin.value(),
            spacing=self.spacing_spin.value(),
            angle=self.angle_spin.value(),
            color=self._current_color(),
            outline=self.outline_check.isChecked(),
            fmt=str(self.fmt_combo.currentData()),
            jpeg_quality=self.quality_spin.value(),
            output_mode=str(self.mode_combo.currentData()),
            custom_dir=self._custom_dir,
            on_conflict=str(self.conflict_combo.currentData()),
        )

    def start_conversion(self) -> None:
        if self._is_running():
            return
        if not self._files:
            QMessageBox.information(self, "还没有图片", "请先选择图片或文件夹。")
            return
        options = self._read_options()
        if not options.text.strip():
            QMessageBox.warning(self, "水印文字", "请先输入要添加的水印文字。")
            self.text_edit.setFocus()
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

        worker = WatermarkWorker(list(self._files), options, self)
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
        self.status.setText(f"处理中… {done}/{total} 张")

    def _on_finished(self, batch: object) -> None:
        result: converter.BatchResult = batch  # type: ignore[assignment]
        outputs = [out for f in result.files for out in f.outputs]
        if outputs:
            self._last_output = outputs[0].parent
            self.btn_open.show()
        if result.cancelled:
            self.status.setText(f"已取消，已完成 {result.image_count} 张")
            self._append_log(f"已取消：成功 {result.ok_count} 个，失败 {result.fail_count} 个")
        else:
            self.progress.setValue(100)
            self.status.setText(f"完成：{result.image_count} 张图片")
            self._append_log(
                f"全部结束：成功 {result.ok_count} 个，失败 {result.fail_count} 个"
            )
        failures = [f for f in result.files if not f.ok]
        if failures:
            detail = "\n".join(f"· {f.source.name}：{f.error}" for f in failures[:10])
            if len(failures) > 10:
                detail += f"\n… 另有 {len(failures) - 10} 个失败"
            QMessageBox.warning(self, "部分图片处理失败", detail)

    def _on_failed(self, message: str) -> None:
        self.status.setText("出错")
        self._append_log(f"错误：{message}")
        QMessageBox.critical(self, "处理失败", message)

    def _on_worker_finished(self) -> None:
        self._worker = None
        self._set_running(False)
        self._schedule_preview()

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
            self.text_edit,
            self.opacity_spin,
            self.size_spin,
            self.spacing_spin,
            self.angle_spin,
            self.color_combo,
            self.outline_check,
            self.fmt_combo,
            self.mode_combo,
            self.btn_dir,
            self.conflict_combo,
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
                "text": self.text_edit.toPlainText(),
                "opacity": self.opacity_spin.value(),
                "font_size": self.size_spin.value(),
                "spacing": self.spacing_spin.value(),
                "angle": self.angle_spin.value(),
                "color": self.color_combo.currentData(),
                "outline": self.outline_check.isChecked(),
                "custom_color": self._custom_color,
                "fmt": self.fmt_combo.currentData(),
                "quality": self.quality_spin.value(),
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
            if isinstance(data.get("text"), str):
                self.text_edit.setPlainText(data["text"])
            if isinstance(data.get("opacity"), int):
                self.opacity_spin.setValue(data["opacity"])
            if isinstance(data.get("font_size"), int):
                self.size_spin.setValue(data["font_size"])
            if isinstance(data.get("spacing"), int):
                self.spacing_spin.setValue(data["spacing"])
            if isinstance(data.get("angle"), int):
                self.angle_spin.setValue(data["angle"])
            if isinstance(data.get("custom_color"), str):
                self._custom_color = data["custom_color"]
                index = self.color_combo.findData("__custom__")
                self.color_combo.setItemText(index, f"自定义 {self._custom_color}")
            if isinstance(data.get("outline"), bool):
                self.outline_check.setChecked(data["outline"])
            if data.get("color"):
                index = self.color_combo.findData(data["color"])
                if index >= 0:
                    self.color_combo.setCurrentIndex(index)
                elif self._custom_color:
                    self.color_combo.setCurrentIndex(self.color_combo.findData("__custom__"))
            if data.get("fmt"):
                index = self.fmt_combo.findData(data["fmt"])
                if index >= 0:
                    self.fmt_combo.setCurrentIndex(index)
            if isinstance(data.get("quality"), int):
                self.quality_spin.setValue(data["quality"])
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
        except Exception:  # noqa: BLE001 - 配置损坏就用默认值
            pass
        self._update_dir_hint()
        self._on_format_changed()

    def shutdown(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(3000)
