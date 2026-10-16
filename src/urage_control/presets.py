"""Color presets and strict RGB validation."""

from collections.abc import Iterable
from typing import cast


class InvalidColorError(ValueError):
    """Raised when an RGB color or preset name is invalid."""


PRESETS: dict[str, tuple[int, int, int]] = {
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "purple": (128, 0, 128),
    "cyan": (0, 255, 255),
    "white": (255, 255, 255),
    "orange": (255, 127, 0),
}


def validate_rgb(red: object, green: object, blue: object) -> tuple[int, int, int]:
    """Return validated RGB channels without coercion or clamping."""
    channels = (red, green, blue)
    for name, value in zip(("red", "green", "blue"), channels):
        if type(value) is not int or not 0 <= value <= 255:
            raise InvalidColorError(f"{name} must be an integer from 0 to 255")
    return cast(tuple[int, int, int], channels)


def get_preset(name: str) -> tuple[int, int, int]:
    """Look up a preset without regard to letter case."""
    if not isinstance(name, str):
        raise InvalidColorError("preset name must be text")
    try:
        return PRESETS[name.lower()]
    except KeyError as exc:
        choices = ", ".join(PRESETS)
        raise InvalidColorError(
            f"unknown preset {name!r}; choose from: {choices}"
        ) from exc


def resolve_color(values: Iterable[object]) -> tuple[int, int, int]:
    """Validate an iterable containing exactly three RGB channel values."""
    try:
        channels = tuple(values)
    except TypeError as exc:
        raise InvalidColorError(
            "RGB values must be an iterable of three integers"
        ) from exc
    if len(channels) != 3:
        raise InvalidColorError("exactly three RGB values are required")
    return validate_rgb(*channels)
