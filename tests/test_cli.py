from typing import ClassVar

from urage_control import cli
from urage_control.device import DeviceNotFoundError


class FakeDevice:
    calls: ClassVar[list[tuple[int, int, int]]] = []
    error: ClassVar[DeviceNotFoundError | None] = None

    def __init__(self):
        pass

    def apply_color(self, rgb):
        type(self).calls.append(rgb)
        if type(self).error is not None:
            raise type(self).error


def setup_function():
    FakeDevice.calls = []
    FakeDevice.error = None


def test_cli_applies_named_preset(monkeypatch, capsys):
    monkeypatch.setattr(cli, "UrageDevice", FakeDevice)

    result = cli.main(["red"])

    assert result == 0
    assert FakeDevice.calls == [(255, 0, 0)]
    assert "RGB(255, 0, 0)" in capsys.readouterr().out


def test_cli_applies_direct_rgb_values(monkeypatch, capsys):
    monkeypatch.setattr(cli, "UrageDevice", FakeDevice)

    result = cli.main(["255", "120", "0"])

    assert result == 0
    assert FakeDevice.calls == [(255, 120, 0)]
    assert "RGB(255, 120, 0)" in capsys.readouterr().out


def test_cli_rejects_invalid_rgb_without_device_io(monkeypatch, capsys):
    monkeypatch.setattr(cli, "UrageDevice", FakeDevice)

    result = cli.main(["256", "0", "0"])

    assert result == 2
    assert FakeDevice.calls == []
    assert "0 to 255" in capsys.readouterr().err


def test_cli_reports_device_error_without_traceback(monkeypatch, capsys):
    FakeDevice.error = DeviceNotFoundError("mouse missing")
    monkeypatch.setattr(cli, "UrageDevice", FakeDevice)

    result = cli.main(["blue"])

    captured = capsys.readouterr()
    assert result == 2
    assert "mouse missing" in captured.err
    assert "Traceback" not in captured.err
