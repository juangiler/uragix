import errno
from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest
import usb.core

from urage_control.device import (
    DeviceNotFoundError,
    UrageDevice,
    USBPermissionError,
    USBTransferError,
)
from urage_control.protocol import (
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


def make_driver(device):
    core = SimpleNamespace(find=Mock(return_value=device))
    sleeper = Mock()
    return UrageDevice(usb_core=core, sleeper=sleeper), device, sleeper, core


def test_device_not_found():
    driver, _, _, core = make_driver(None)
    with pytest.raises(DeviceNotFoundError):
        driver.apply_color((1, 2, 3))
    core.find.assert_called_once_with(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)


def test_usb_permission_error_is_distinguished():
    error = usb.core.USBError("access denied")
    error.errno = errno.EACCES
    core = SimpleNamespace(find=Mock(side_effect=error))
    driver = UrageDevice(usb_core=core, sleeper=Mock())
    with pytest.raises(USBPermissionError):
        driver.apply_color((1, 2, 3))


def test_expected_transfer_sequence_and_only_detached_interfaces_restored():
    device = Mock()
    device.is_kernel_driver_active.side_effect = lambda interface: interface == 1
    driver, _, sleeper, _ = make_driver(device)
    driver.apply_color((10, 20, 30))

    device.detach_kernel_driver.assert_called_once_with(1)
    device.attach_kernel_driver.assert_called_once_with(1)
    assert device.ctrl_transfer.call_args_list == [
        call(
            bmRequestType=REQUEST_TYPE,
            bRequest=REQUEST,
            wValue=HANDSHAKE_VALUE,
            wIndex=INTERFACE_INDEX,
            data_or_wLength=HANDSHAKE_PACKET,
        ),
        call(
            bmRequestType=REQUEST_TYPE,
            bRequest=REQUEST,
            wValue=PROFILE_VALUE,
            wIndex=INTERFACE_INDEX,
            data_or_wLength=build_profile((10, 20, 30)),
        ),
    ]
    sleeper.assert_called_once_with(0.05)
    device.reset.assert_called_once_with()


def test_handshake_failure_still_restores_detached_interface():
    device = Mock()
    device.is_kernel_driver_active.side_effect = lambda interface: interface == 0
    original_error = usb.core.USBError("handshake failed")
    device.ctrl_transfer.side_effect = original_error
    driver, _, _, _ = make_driver(device)

    with pytest.raises(USBTransferError) as captured:
        driver.apply_color((1, 2, 3))

    assert captured.value.__cause__ is original_error
    device.attach_kernel_driver.assert_called_once_with(0)
    device.reset.assert_not_called()


def test_profile_failure_does_not_reset_and_restores_detached_interfaces():
    device = Mock()
    device.is_kernel_driver_active.side_effect = lambda interface: True
    device.ctrl_transfer.side_effect = [None, usb.core.USBError("profile failed")]
    driver, _, _, _ = make_driver(device)

    with pytest.raises(USBTransferError):
        driver.apply_color((1, 2, 3))

    assert device.attach_kernel_driver.call_args_list == [call(1), call(0)]
    device.reset.assert_not_called()


def test_driver_restore_failure_is_reported():
    device = Mock()
    device.is_kernel_driver_active.side_effect = lambda interface: interface == 0
    device.attach_kernel_driver.side_effect = usb.core.USBError("restore failed")
    driver, _, _, _ = make_driver(device)

    with pytest.raises(USBTransferError):
        driver.apply_color((1, 2, 3))


def test_no_kernel_driver_means_no_detach_or_attach():
    device = Mock()
    device.is_kernel_driver_active.return_value = False
    driver, _, _, _ = make_driver(device)

    driver.apply_color((1, 2, 3))

    device.detach_kernel_driver.assert_not_called()
    device.attach_kernel_driver.assert_not_called()
    assert device.ctrl_transfer.call_count == 2
    device.reset.assert_called_once_with()
