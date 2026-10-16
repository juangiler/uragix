import pytest

from urage_control.presets import PRESETS
from urage_control.protocol import (
    BASE_PROFILE_HEX,
    EXPECTED_PROFILE_LENGTH,
    RGB_OFFSETS,
    InvalidPacketError,
    build_profile,
    validate_profile_template,
)


def test_baseline_length_and_rgb_offsets():
    baseline = validate_profile_template()
    assert len(BASE_PROFILE_HEX) == EXPECTED_PROFILE_LENGTH * 2
    assert len(baseline) == EXPECTED_PROFILE_LENGTH
    assert RGB_OFFSETS == (57, 58, 59)


def test_profile_changes_only_rgb_offsets():
    baseline = validate_profile_template()
    profile = build_profile((1, 2, 3))
    assert len(profile) == EXPECTED_PROFILE_LENGTH
    assert tuple(profile[index] for index in RGB_OFFSETS) == (1, 2, 3)
    assert [
        index
        for index, (before, after) in enumerate(zip(baseline, profile))
        if before != after
    ] == list(RGB_OFFSETS)


@pytest.mark.parametrize("color", PRESETS.values())
def test_each_preset_is_written_to_the_profile(color):
    profile = build_profile(color)
    assert tuple(profile[index] for index in RGB_OFFSETS) == color


@pytest.mark.parametrize("template", ["00", "z" + BASE_PROFILE_HEX[1:]])
def test_template_validation_rejects_wrong_length_or_hex(template):
    with pytest.raises(InvalidPacketError):
        validate_profile_template(template)
