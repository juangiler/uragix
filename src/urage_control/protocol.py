"""Immutable baseline packet data and profile construction."""

from .presets import resolve_color

VENDOR_ID = 0x258A
PRODUCT_ID = 0x1007
HANDSHAKE_PACKET = bytes.fromhex("051100000000")
REQUEST_TYPE = 0x21
REQUEST = 0x09
INTERFACE_INDEX = 1
HANDSHAKE_VALUE = 0x0305
PROFILE_VALUE = 0x0304
HANDSHAKE_DELAY_SECONDS = 0.05

RGB_RED_OFFSET = 57
RGB_GREEN_OFFSET = 58
RGB_BLUE_OFFSET = 59
RGB_OFFSETS = (RGB_RED_OFFSET, RGB_GREEN_OFFSET, RGB_BLUE_OFFSET)
EXPECTED_PROFILE_LENGTH = 520

# Exact 1,040-character baseline sent by the legacy implementation. The old
# source template has 1,061 hex characters (including a dangling nibble), and
# its existing [:1040] operation truncates that source to this transmitted
# payload. Keeping the transmitted bytes explicit avoids runtime normalization.
BASE_PROFILE_HEX = (
    "0411007b0000000064080357800102030405070d000000000000000000ff00000000ff00ff00ff460000ffffff00ffffffff"
    "0000000200004f00ff00000002320000400000ff4107ff00000000ff00ff008000fffac603fa036afa00fa42424000c000ff"
    "8000ff8000800000000000000000000000000000000042ff00000000ff4141028000ff00ff00000000ffff00ffffff000000"
    "0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
    "0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
    "0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
    "0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
    "0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
    "0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
    "0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
    "0000000000000000000000000000000000000000"
)


class InvalidPacketError(ValueError):
    """Raised when the immutable profile baseline is malformed."""


def validate_profile_template(template_hex: str = BASE_PROFILE_HEX) -> bytes:
    """Parse a complete, correctly sized hexadecimal profile template."""
    if not isinstance(template_hex, str):
        raise InvalidPacketError("profile template must be hexadecimal text")
    if len(template_hex) != EXPECTED_PROFILE_LENGTH * 2:
        raise InvalidPacketError(
            f"profile template must contain {EXPECTED_PROFILE_LENGTH * 2} hex characters"
        )
    try:
        profile = bytes.fromhex(template_hex)
    except ValueError as exc:
        raise InvalidPacketError(
            "profile template contains invalid hexadecimal data"
        ) from exc
    if len(profile) != EXPECTED_PROFILE_LENGTH:
        raise InvalidPacketError(
            f"profile must be exactly {EXPECTED_PROFILE_LENGTH} bytes"
        )
    if max(RGB_OFFSETS) >= len(profile):
        raise InvalidPacketError("RGB offsets fall outside the profile")
    return profile


def build_profile(rgb: tuple[object, object, object]) -> bytes:
    """Create a profile copy with only the three RGB bytes replaced."""
    red, green, blue = resolve_color(rgb)
    profile = bytearray(validate_profile_template())
    profile[RGB_RED_OFFSET] = red
    profile[RGB_GREEN_OFFSET] = green
    profile[RGB_BLUE_OFFSET] = blue
    return bytes(profile)
