"""PyUSB device discovery and the preserved color-apply sequence."""

from __future__ import annotations

import errno
import logging
import time
from collections.abc import Callable
from typing import Protocol

import usb.core

from .presets import resolve_color
from .protocol import (
    HANDSHAKE_DELAY_SECONDS,
    HANDSHAKE_PACKET,
    HANDSHAKE_VALUE,
    INTERFACE_INDEX,
    PRODUCT_ID,
    PROFILE_VALUE,
    REQUEST,
    REQUEST_TYPE,
    VENDOR_ID,
    build_profile,
)

logger = logging.getLogger(__name__)


class USBDevice(Protocol):
    """Subset of a PyUSB device used by the controller."""

    def is_kernel_driver_active(self, interface: int) -> bool: ...

    def detach_kernel_driver(self, interface: int) -> None: ...

    def attach_kernel_driver(self, interface: int) -> None: ...

    def ctrl_transfer(
        self,
        *,
        bmRequestType: int,
        bRequest: int,
        wValue: int,
        wIndex: int,
        data_or_wLength: bytes | bytearray,
    ) -> int: ...

    def reset(self) -> None: ...


class USBDiscovery(Protocol):
    """Subset of PyUSB used to locate the supported device."""

    def find(self, *, idVendor: int, idProduct: int) -> USBDevice | None: ...


class DeviceError(RuntimeError):
    """Base class for expected device-operation failures."""


class DeviceNotFoundError(DeviceError):
    """The supported USB device was not discovered."""


class USBPermissionError(DeviceError):
    """The process lacks permission to access the USB device."""


class USBTransferError(DeviceError):
    """A USB query, transfer, reset, or cleanup operation failed."""


def _translate_usb_error(error: usb.core.USBError) -> DeviceError:
    error_number = getattr(error, "errno", None)
    if error_number in (errno.EACCES, errno.EPERM):
        return USBPermissionError(
            "USB access denied; check the device permissions or udev rule"
        )
    return USBTransferError(f"USB operation failed: {error}")


class UrageDevice:
    """Apply a uniform color using the existing device protocol."""

    def __init__(
        self,
        *,
        usb_core: USBDiscovery = usb.core,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self._usb_core: USBDiscovery = usb_core
        self._sleep = sleeper

    def is_available(self) -> bool:
        """Return whether PyUSB currently discovers the target device."""
        try:
            return (
                self._usb_core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
                is not None
            )
        except usb.core.USBError as exc:
            raise _translate_usb_error(exc) from exc

    def apply_color(self, rgb: tuple[object, object, object]) -> None:
        """Send the handshake and profile, reset, then restore detached drivers."""
        color = resolve_color(rgb)
        profile = build_profile(color)
        try:
            device = self._usb_core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
        except usb.core.USBError as exc:
            raise _translate_usb_error(exc) from exc
        if device is None:
            raise DeviceNotFoundError(
                f"uRage mouse not found (VID {VENDOR_ID:04x}, PID {PRODUCT_ID:04x})"
            )

        detached_interfaces: list[int] = []
        operation_error: DeviceError | None = None
        operation_cause: usb.core.USBError | None = None
        try:
            for interface_id in (1, 0):
                if device.is_kernel_driver_active(interface_id):
                    device.detach_kernel_driver(interface_id)
                    detached_interfaces.append(interface_id)

            device.ctrl_transfer(
                bmRequestType=REQUEST_TYPE,
                bRequest=REQUEST,
                wValue=HANDSHAKE_VALUE,
                wIndex=INTERFACE_INDEX,
                data_or_wLength=HANDSHAKE_PACKET,
            )
            self._sleep(HANDSHAKE_DELAY_SECONDS)
            device.ctrl_transfer(
                bmRequestType=REQUEST_TYPE,
                bRequest=REQUEST,
                wValue=PROFILE_VALUE,
                wIndex=INTERFACE_INDEX,
                data_or_wLength=profile,
            )
            device.reset()
        except usb.core.USBError as exc:
            operation_error = _translate_usb_error(exc)
            operation_cause = exc
        finally:
            cleanup_error: usb.core.USBError | None = None
            for interface_id in detached_interfaces:
                try:
                    device.attach_kernel_driver(interface_id)
                except usb.core.USBError as exc:
                    logger.warning(
                        "Could not restore kernel driver on interface %s: %s",
                        interface_id,
                        exc,
                    )
                    cleanup_error = cleanup_error or exc

            if operation_error is not None:
                if cleanup_error is not None:
                    logger.warning(
                        "USB driver restoration also failed: %s", cleanup_error
                    )
                raise operation_error from operation_cause
            if cleanup_error is not None:
                raise _translate_usb_error(cleanup_error) from cleanup_error
