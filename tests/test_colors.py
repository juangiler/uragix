import pytest

from urage_control.presets import PRESETS, InvalidColorError, get_preset, validate_rgb


def test_inclusive_boundaries():
    assert validate_rgb(0, 255, 0) == (0, 255, 0)


@pytest.mark.parametrize(
    "values",
    [(-1, 0, 0), (256, 0, 0), (1.5, 0, 0), (True, 0, 0), ("1", 0, 0)],
)
def test_invalid_channel_values_are_rejected(values):
    with pytest.raises(InvalidColorError):
        validate_rgb(*values)


def test_preset_lookup_is_case_insensitive():
    assert get_preset("ReD") == PRESETS["red"]
    for name, color in PRESETS.items():
        assert get_preset(name) == color


def test_unknown_preset_is_rejected():
    with pytest.raises(InvalidColorError):
        get_preset("ultraviolet")
