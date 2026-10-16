"""Command-line interface for applying a preset or RGB color."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence

from .device import DeviceError, UrageDevice
from .presets import InvalidColorError, get_preset, resolve_color

logger = logging.getLogger(__name__)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="urage-control",
        description="Set a uniform lighting color on the supported uRage mouse.",
        epilog="Presets: red, green, blue, yellow, purple, cyan, white, orange",
    )
    parser.add_argument("--debug", action="store_true", help="show diagnostic logging")
    parser.add_argument(
        "color", nargs="+", help="preset name or three integer RGB values"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    try:
        if len(args.color) == 1:
            rgb = get_preset(args.color[0])
        elif len(args.color) == 3:
            try:
                values = tuple(int(value, 10) for value in args.color)
            except ValueError as exc:
                raise InvalidColorError("RGB values must be integers") from exc
            rgb = resolve_color(values)
        else:
            raise InvalidColorError(
                "provide one preset name or exactly three RGB values"
            )

        UrageDevice().apply_color(rgb)
    except (InvalidColorError, DeviceError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except (
        Exception
    ) as exc:  # Keep unexpected failures diagnosable without a routine traceback.
        if args.debug:
            logger.exception("Unexpected error while applying the color")
        else:
            print(
                f"Unexpected error: {exc} (rerun with --debug for details)",
                file=sys.stderr,
            )
        return 1

    print(f"Mouse color updated to RGB({rgb[0]}, {rgb[1]}, {rgb[2]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
