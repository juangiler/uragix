import os
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

from urage_control.device import DeviceNotFoundError, USBPermissionError
from urage_control.gui import ColorControlWindow
from urage_control.presets import PRESETS


@pytest.fixture(scope="module")
def app():
    instance = QApplication.instance() or QApplication([])
    yield instance


def wait_until(app, predicate, timeout_ms=2500):
    from PySide6.QtCore import QEventLoop, QTimer

    loop = QEventLoop()
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    timer.start(timeout_ms)
    poll = QTimer()
    poll.timeout.connect(lambda: loop.quit() if predicate() else None)
    poll.start(10)
    if not predicate():
        loop.exec()
    poll.stop()
    timer.stop()
    app.processEvents()
    assert predicate(), "GUI operation did not finish before timeout"


def fake_device(*, available=True, apply_error=None):
    device = SimpleNamespace(
        is_available=Mock(return_value=available),
        apply_color=Mock(side_effect=apply_error),
    )
    return device


def make_window(app, device):
    window = ColorControlWindow(device=device)
    window.show()
    wait_until(app, lambda: window._pending_action is None and not window._threads)
    return window


def close_window(app, window):
    window.close()
    wait_until(app, lambda: not window._threads)
    app.processEvents()


def test_rgb_slider_and_spinbox_stay_synchronized_and_preserve_channels(app):
    window = make_window(app, fake_device())
    window._spinboxes[1].setValue(120)

    assert window._sliders[1].value() == 120
    assert window._spinboxes[1].value() == 120
    assert window.rgb == (255, 120, 0)
    assert window.rgb_label.text() == "RGB  255, 120, 0"
    assert window.hex_label.text() == "#FF7800"
    close_window(app, window)


def test_preset_buttons_use_project_presets_and_update_controls(app):
    window = make_window(app, fake_device())
    window._preset_buttons["cyan"].click()

    assert window.rgb == PRESETS["cyan"]
    assert tuple(box.value() for box in window._spinboxes) == PRESETS["cyan"]
    assert window._preset_buttons["cyan"].property("preset") is True
    close_window(app, window)


@pytest.mark.parametrize(
    "error, expected_status, expected_message",
    [
        (
            DeviceNotFoundError("device missing"),
            "Not detected",
            "No supported uRage mouse",
        ),
        (
            USBPermissionError("access denied"),
            "USB permission error",
            "USB access denied",
        ),
        (RuntimeError("transfer failed"), "Device error", "Unexpected device error"),
    ],
)
def test_failed_apply_reports_error_without_crashing(
    app, error, expected_status, expected_message
):
    device = fake_device(apply_error=error)
    window = make_window(app, device)
    window._apply_color()
    wait_until(
        app, lambda: window._pending_action is None and device.apply_color.called
    )

    assert window.device_label.text() == expected_status
    assert expected_message in window.message_label.text()
    assert window.apply_button.isEnabled()
    assert window.rgb == PRESETS["red"]
    close_window(app, window)


def test_window_starts_and_reports_missing_device_without_hardware(app):
    device = fake_device(available=False)
    window = make_window(app, device)

    assert device.is_available.call_count == 1
    assert window.device_label.text() == "Not detected"
    assert window.apply_button.isEnabled()
    close_window(app, window)


def test_window_uses_project_application_icon(app):
    window = make_window(app, fake_device())

    assert not window.windowIcon().isNull()
    close_window(app, window)


def test_apply_runs_once_in_background_and_reports_the_applied_selection(app):
    started = Event()
    finish = Event()

    def delayed_apply(rgb):
        started.set()
        assert finish.wait(2)

    device = fake_device()
    device.apply_color.side_effect = delayed_apply
    window = make_window(app, device)
    window._apply_color()
    assert started.wait(1)
    assert not window.apply_button.isEnabled()

    window._spinboxes[0].setValue(18)
    window._apply_color()
    finish.set()
    wait_until(app, lambda: window._pending_action is None)

    device.apply_color.assert_called_once_with(PRESETS["red"])
    assert window.rgb == (18, 0, 0)
    assert "RGB(255, 0, 0)" in window.message_label.text()
    assert window.apply_button.isEnabled()
    close_window(app, window)
