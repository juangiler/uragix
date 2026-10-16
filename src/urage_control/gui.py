"""PySide6 desktop interface for the uRage mouse lighting controller."""

from __future__ import annotations

import sys
from collections.abc import Sequence

from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QCloseEvent, QColor
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .device import (
    DeviceError,
    DeviceNotFoundError,
    UrageDevice,
    USBPermissionError,
)
from .presets import PRESETS, validate_rgb

APP_STYLESHEET = """
QWidget {
    color: #e8e9ed;
    font-family: "Noto Sans", "DejaVu Sans", sans-serif;
    font-size: 10pt;
}
QMainWindow { background: #202329; }
QLabel { background: transparent; }
QFrame#panel {
    background: #191919;
    border: 1px solid #30343c;
    border-radius: 10px;
}
QLabel#muted { color: #a1a6b0; }
QLabel#heading { font-size: 17pt; font-weight: 600; }
QLabel#sectionTitle { font-size: 11pt; font-weight: 600; }
QLabel#statusText { color: #c6cad2; }
QLabel#notice { color: #aeb4bf; }
QPushButton {
    background: #202329;
    border: 1px solid #3a3f49;
    border-radius: 7px;
    padding: 8px 12px;
}
QPushButton:hover { background: #343943; border-color: #555c68; }
QPushButton:pressed { background: #252930; }
QPushButton:disabled { color: #757b85; background: #24272d; }
QPushButton#applyButton {
    background: #d9e2f2;
    color: #17191d;
    border: 1px solid #d9e2f2;
    font-weight: 600;
    padding: 10px 16px;
}
QPushButton#applyButton:hover { background: #edf2fa; }
QPushButton#applyButton:disabled { color: #777e89; background: #343943; border-color: #343943; }
QPushButton[preset="true"] { border: 1px solid #91a9d1; }
QSlider::groove:horizontal {
    height: 5px;
    background: #3b4049;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    width: 14px;
    margin: -5px 0;
    border-radius: 7px;
    background: #d9e2f2;
}
QSlider::handle:horizontal:hover { background: #ffffff; }
QSpinBox {
    background: #202329;
    border: 1px solid #3a3f49;
    border-radius: 6px;
    padding: 5px 7px;
    min-width: 54px;
}
QSpinBox QLineEdit { background: #202329; }
QSpinBox:focus { border-color: #91a9d1; }
QPushButton:focus { outline: none; }
QSlider:focus { outline: 1px solid #91a9d1; }
"""


class _DeviceWorker(QObject):
    """Run one potentially blocking device operation outside the UI thread."""

    succeeded = Signal(str, object)
    failed = Signal(str, object)
    finished = Signal()

    def __init__(
        self, action: str, device: UrageDevice, rgb: tuple[int, int, int] | None
    ):
        super().__init__()
        self.action = action
        self.device = device
        self.rgb = rgb

    @Slot()
    def run(self) -> None:
        try:
            if self.action == "discover":
                result = self.device.is_available()
            else:
                if self.rgb is None:
                    raise ValueError("an RGB color is required to apply a color")
                self.device.apply_color(self.rgb)
                result = None
            self.succeeded.emit(self.action, result)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(self.action, exc)
        finally:
            self.finished.emit()


class ColorControlWindow(QMainWindow):
    """Compact color selector whose only USB path is ``UrageDevice``."""

    def __init__(self, device: UrageDevice | None = None) -> None:
        super().__init__()
        self.device = device or UrageDevice()
        self.rgb = validate_rgb(*PRESETS["red"])
        self._threads: set[QThread] = set()
        self._workers: set[_DeviceWorker] = set()
        self._pending_action: str | None = None
        self._active_rgb: tuple[int, int, int] | None = None
        self._close_when_finished = False
        self._preset_buttons: dict[str, QPushButton] = {}
        self._sliders: list[QSlider] = []
        self._spinboxes: list[QSpinBox] = []

        self.setWindowTitle("uRage Control")
        self.setMinimumSize(500, 590)
        self.resize(560, 660)
        self.setStyleSheet(APP_STYLESHEET)
        self._build_ui()
        self._update_color(self.rgb)
        self._set_status("Checking device…", "busy")
        self._set_message("Checking for the supported uRage mouse…", error=False)
        self._start_operation("discover")

    def _build_ui(self) -> None:
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(22, 18, 22, 20)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title_column = QVBoxLayout()
        title = QLabel("uRage Control")
        title.setObjectName("heading")
        subtitle = QLabel("Mouse lighting control")
        subtitle.setObjectName("muted")
        title_column.addWidget(title)
        title_column.addWidget(subtitle)
        header.addLayout(title_column)
        header.addStretch(1)

        device_card = QFrame()
        device_card.setObjectName("panel")
        device_layout = QHBoxLayout(device_card)
        device_layout.setContentsMargins(11, 8, 12, 8)
        device_layout.setSpacing(8)
        self.status_dot = QLabel("●")
        self.status_dot.setAccessibleName("Device status indicator")
        self.device_label = QLabel("Supported uRage mouse")
        self.device_label.setObjectName("statusText")
        device_layout.addWidget(self.status_dot)
        device_layout.addWidget(self.device_label)
        header.addWidget(device_card)
        layout.addLayout(header)

        preview = QFrame()
        preview.setObjectName("panel")
        preview_layout = QHBoxLayout(preview)
        preview_layout.setContentsMargins(16, 14, 16, 14)
        preview_layout.setSpacing(16)
        self.color_swatch = QFrame()
        self.color_swatch.setMinimumSize(100, 78)
        self.color_swatch.setMaximumWidth(130)
        self.color_swatch.setAccessibleName("Selected color preview")
        self.color_swatch.setStyleSheet(
            "border-radius: 8px; border: 1px solid #ffffff33;"
        )
        preview_layout.addWidget(self.color_swatch)
        preview_text = QVBoxLayout()
        preview_heading = QLabel("Selected color")
        preview_heading.setObjectName("sectionTitle")
        preview_note = QLabel("Preview only · not applied to the mouse")
        preview_note.setObjectName("muted")
        self.rgb_label = QLabel()
        self.hex_label = QLabel()
        self.hex_label.setObjectName("muted")
        preview_text.addWidget(preview_heading)
        preview_text.addWidget(preview_note)
        preview_text.addSpacing(6)
        preview_text.addWidget(self.rgb_label)
        preview_text.addWidget(self.hex_label)
        preview_layout.addLayout(preview_text, 1)
        layout.addWidget(preview)

        preset_panel = self._panel()
        preset_layout = QVBoxLayout(preset_panel)
        preset_layout.setContentsMargins(14, 12, 14, 14)
        preset_layout.setSpacing(10)
        preset_title = QLabel("Preset colors")
        preset_title.setObjectName("sectionTitle")
        preset_layout.addWidget(preset_title)
        swatches = QGridLayout()
        swatches.setHorizontalSpacing(8)
        swatches.setVerticalSpacing(8)
        for index, (name, color) in enumerate(PRESETS.items()):
            button = QPushButton(name.title())
            button.setToolTip(
                f"Select {name} preset, RGB {color[0]}, {color[1]}, {color[2]}"
            )
            button.setAccessibleName(f"{name.title()} preset color")
            button.setMinimumHeight(36)
            button.clicked.connect(
                lambda checked=False, value=color: self._update_color(value)
            )
            self._preset_buttons[name] = button
            swatches.addWidget(button, index // 4, index % 4)
        preset_layout.addLayout(swatches)
        layout.addWidget(preset_panel)

        rgb_panel = self._panel()
        rgb_layout = QVBoxLayout(rgb_panel)
        rgb_layout.setContentsMargins(14, 12, 14, 12)
        rgb_layout.setSpacing(8)
        rgb_title = QLabel("Custom RGB")
        rgb_title.setObjectName("sectionTitle")
        rgb_layout.addWidget(rgb_title)
        for index, (name, initial) in enumerate(
            zip(("Red", "Green", "Blue"), self.rgb)
        ):
            channel_row = QGridLayout()
            channel_row.setHorizontalSpacing(12)
            label = QLabel(name)
            label.setMinimumWidth(48)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 255)
            slider.setValue(initial)
            slider.setAccessibleName(f"{name} channel slider")
            spin = QSpinBox()
            spin.setRange(0, 255)
            spin.setValue(initial)
            spin.setKeyboardTracking(False)
            spin.setAccessibleName(f"{name} channel value")
            slider.valueChanged.connect(
                lambda value, i=index: self._channel_changed(i, value)
            )
            spin.valueChanged.connect(
                lambda value, i=index: self._channel_changed(i, value)
            )
            self._sliders.append(slider)
            self._spinboxes.append(spin)
            channel_row.addWidget(label, 0, 0)
            channel_row.addWidget(slider, 0, 1)
            channel_row.addWidget(spin, 0, 2)
            rgb_layout.addLayout(channel_row)
        layout.addWidget(rgb_panel)

        footer = QHBoxLayout()
        self.message_label = QLabel()
        self.message_label.setObjectName("notice")
        self.message_label.setWordWrap(True)
        self.message_label.setMinimumHeight(34)
        footer.addWidget(self.message_label, 1)
        self.apply_button = QPushButton("Apply Color")
        self.apply_button.setObjectName("applyButton")
        self.apply_button.setDefault(True)
        self.apply_button.setMinimumHeight(42)
        self.apply_button.setAccessibleName("Apply selected color to the mouse")
        self.apply_button.clicked.connect(self._apply_color)
        footer.addWidget(self.apply_button)
        layout.addLayout(footer)
        self.setCentralWidget(central)

    @staticmethod
    def _panel() -> QFrame:
        panel = QFrame()
        panel.setObjectName("panel")
        return panel

    @Slot(int, int)
    def _channel_changed(self, index: int, value: int) -> None:
        if self._sliders[index].value() != value:
            self._sliders[index].setValue(value)
        if self._spinboxes[index].value() != value:
            self._spinboxes[index].setValue(value)
        color = list(self.rgb)
        color[index] = value
        self._update_color(tuple(color))

    def _update_color(self, values: Sequence[int]) -> None:
        self.rgb = validate_rgb(*values)
        color = QColor(*self.rgb)
        hex_color = color.name().upper()
        self.color_swatch.setStyleSheet(
            f"background-color: {hex_color}; border-radius: 8px; border: 1px solid #ffffff33;"
        )
        self.rgb_label.setText(f"RGB  {self.rgb[0]}, {self.rgb[1]}, {self.rgb[2]}")
        self.hex_label.setText(hex_color)
        for index, value in enumerate(self.rgb):
            if self._sliders[index].value() != value:
                self._sliders[index].setValue(value)
            if self._spinboxes[index].value() != value:
                self._spinboxes[index].setValue(value)
        for name, button in self._preset_buttons.items():
            selected = PRESETS[name] == self.rgb
            button.setProperty("preset", selected)
            button.style().unpolish(button)
            button.style().polish(button)

    @Slot()
    def _apply_color(self) -> None:
        if self._pending_action is None:
            self._start_operation("apply", self.rgb)

    def _start_operation(
        self, action: str, rgb: tuple[int, int, int] | None = None
    ) -> None:
        if self._pending_action is not None:
            return
        self._pending_action = action
        self._active_rgb = rgb
        self.apply_button.setEnabled(False)
        self._set_status("Device busy", "busy")
        if action == "apply":
            self._set_message("Applying selected color…", error=False)
        worker_thread = QThread(self)
        worker = _DeviceWorker(action, self.device, rgb)
        worker.moveToThread(worker_thread)
        worker_thread.started.connect(worker.run)
        worker.succeeded.connect(self._operation_succeeded)
        worker.failed.connect(self._operation_failed)
        worker.finished.connect(worker_thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker_thread.finished.connect(
            lambda thread=worker_thread, active_worker=worker: self._thread_finished(
                thread, active_worker
            )
        )
        self._threads.add(worker_thread)
        self._workers.add(worker)
        worker_thread.start()

    @Slot(str, object)
    def _operation_succeeded(self, action: str, result: object) -> None:
        if action == "discover":
            if result:
                self._set_status("Connected", "connected")
                self._set_message("Mouse detected and ready.", error=False)
            else:
                self._set_status("Not detected", "missing")
                self._set_message("No supported uRage mouse was found.", error=True)
        else:
            self._set_status("Connected", "connected")
            applied = self._active_rgb or self.rgb
            self._set_message(
                f"Color applied: RGB({applied[0]}, {applied[1]}, {applied[2]}).",
                error=False,
            )
        self._pending_action = None
        self._active_rgb = None
        self.apply_button.setEnabled(True)

    @Slot(str, object)
    def _operation_failed(self, action: str, error: object) -> None:
        if isinstance(error, USBPermissionError):
            self._set_status("USB permission error", "permission")
            message = (
                "USB access denied. Check device permissions; no color was applied."
            )
        elif isinstance(error, DeviceNotFoundError):
            self._set_status("Not detected", "missing")
            message = "No supported uRage mouse was found."
        elif isinstance(error, DeviceError):
            self._set_status("Device error", "missing")
            operation = (
                "check the device" if action == "discover" else "apply the color"
            )
            message = f"Could not {operation}: {error}"
        else:
            self._set_status("Device error", "missing")
            message = f"Unexpected device error: {error}"
        self._set_message(message, error=True)
        self._pending_action = None
        self._active_rgb = None
        self.apply_button.setEnabled(True)

    def _thread_finished(self, thread: QThread, worker: _DeviceWorker) -> None:
        self._threads.discard(thread)
        self._workers.discard(worker)
        thread.deleteLater()
        if self._close_when_finished and not self._threads:
            QTimer.singleShot(0, self.close)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._threads:
            self._close_when_finished = True
            event.ignore()
            self._set_message(
                "Waiting for the USB operation to finish before closing…", error=False
            )
            return
        event.accept()

    def _set_status(self, text: str, state: str) -> None:
        colors = {
            "connected": "#78c99b",
            "missing": "#d47b7b",
            "busy": "#e2bd74",
            "permission": "#e29a69",
        }
        self.status_dot.setStyleSheet(f"color: {colors[state]};")
        self.device_label.setText(text)

    def _set_message(self, message: str, *, error: bool) -> None:
        self.message_label.setText(message)
        self.message_label.setStyleSheet("color: #e29a69;" if error else "")


def main(argv: Sequence[str] | None = None) -> int:
    """Launch the desktop utility."""
    app = QApplication(list(argv) if argv is not None else sys.argv)
    app.setApplicationName("uRage Control")
    app.setStyleSheet(APP_STYLESHEET)
    window = ColorControlWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
