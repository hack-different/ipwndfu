import platform
import struct
import sys
import device_platform
import dfu
import typing


class ExecConfig:
    info: typing.Tuple[str, str, str]
    aes_crypto_command: int

    def __init__(self, info: typing.Tuple[str, str, str], aes_crypto_cmd: int):
        self.info = info
        self.aes_crypto_cmd = aes_crypto_cmd

    def match(self, info):
        return info == self.info[0].ljust(0x40, '\0') + self.info[1].ljust(0x40, '\0') + self.info[2].ljust(0x80, '\0')


configs = [
    ExecConfig(
        ('SecureROM for s5l8947xsi, Copyright 2011, Apple Inc.',
         'RELEASE',
         'iBoot-1458.2'),
        aes_crypto_cmd=0x7060 + 1),
    ExecConfig(
        ('SecureROM for s5l8950xsi, Copyright 2011, Apple Inc.',
         'RELEASE',
         'iBoot-1145.3'),
        aes_crypto_cmd=0x7300 + 1),
    ExecConfig(
        ('SecureROM for s5l8955xsi, Copyright 2011, Apple Inc.',
         'RELEASE',
         'iBoot-1145.3.3'),
        aes_crypto_cmd=0x7340 + 1),
    ExecConfig(
        ('SecureROM for t8002si, Copyright 2007-2014, Apple Inc.',
         'ROMRELEASE',
         'iBoot-2651.0.0.1.31'),
        aes_crypto_cmd=0x86DC + 1),
    ExecConfig(
        ('SecureROM for t8004si, Copyright 2007-2014, Apple Inc.',
         'ROMRELEASE',
         'iBoot-2651.0.0.3.3'),
        aes_crypto_cmd=0x786C + 1),
    ExecConfig(
        ('SecureROM for s5l8960xsi, Copyright 2012, Apple Inc.',
         'RELEASE',
         'iBoot-1704.10'),
        aes_crypto_cmd=0x10000B9A8),
    ExecConfig(
        ('SecureROM for t8010si, Copyright 2007-2015, Apple Inc.',
         'ROMRELEASE',
         'iBoot-2696.0.0.1.33'),
        aes_crypto_cmd=0x10000C8F4),
    ExecConfig(
        ('SecureROM for t8011si, Copyright 2007-2015, Apple Inc.',
         'ROMRELEASE',
         'iBoot-3135.0.0.2.3'),
        aes_crypto_cmd=0x10000C994),
    ExecConfig(
        ('SecureROM for t8015si, Copyright 2007-2016, Apple Inc.',
         'ROMRELEASE',
         'iBoot-3332.0.0.1.23'),
        aes_crypto_cmd=0x100009E9C),
    ExecConfig(
        ('SecureROM for t8012si, Copyright 2007-2016, Apple Inc.',
         'ROMRELEASE',
         'iBoot-3401.0.0.1.16'),
        aes_crypto_cmd=0x1000082AC),
]

EXEC_MAGIC = b'execexec'[::-1]
DONE_MAGIC = b'donedone'[::-1]
MEMC_MAGIC = b'memcmemc'[::-1]
MEMS_MAGIC = b'memsmems'[::-1]
if platform.system() == 'Linux':
    USB_READ_LIMIT = 0xFFF
else:
    USB_READ_LIMIT = 0x8000
CMD_TIMEOUT = 5000
AES_BLOCK_SIZE = 16
AES_ENCRYPT = 16
AES_DECRYPT = 17
AES_GID_KEY = 0x20000200
AES_UID_KEY = 0x20000201


class PwnedUSBDevice:
    match: typing.Optional[str]
    serial_number: str

    def __init__(self, match=None):
        self.config = None
        self.platform = None
        self.match = match

        device = dfu.acquire_device(match=self.match)
        self.serial_number = device.serial_number
        dfu.release_device(device)

        for dp in device_platform.all_platforms:
            if self.serial_number.startswith(
                    'CPID:%04x CPRV:%02x ' %
                    (dp.cpid, dp.cprv)):
                self.platform = dp
                break
        if self.platform is None:
            print(self.serial_number)
            print('ERROR: No matching usbexec.platform found for this device.')
            sys.exit(1)

        info = self.read_memory(self.image_base() + 0x200, 0x100)
        for config in configs:
            if config.match(info):
                self.config = config
                break
        if self.config is None:
            print(info)
            print('ERROR: No matching usbexec.config found for this image.')
            sys.exit(1)

    def memset(self, address: int, c: int, length: int) -> None:
        self.command(self.cmd_memset(address, c, length), 0)

    def memcpy(self, dest: int, src: int, length: int) -> None:
        self.command(self.cmd_memcpy(dest, src, length), 0)

    def read_memory_ptr(self, address: int) -> int:
        return struct.unpack(
            '<%s' %
            self.cmd_arg_type(),
            self.read_memory(
                address,
                self.cmd_arg_size()))[0]

    def read_memory_uint8(self, address: int) -> int:
        return struct.unpack('<B', self.read_memory(address, 1))[0]

    def read_memory_uint16(self, address: int) -> int:
        return struct.unpack('<H', self.read_memory(address, 2))[0]

    def read_memory_uint32(self, address: int) -> int:
        return struct.unpack('<I', self.read_memory(address, 4))[0]

    def read_memory_uint64(self, address: int) -> int:
        return struct.unpack('<Q', self.read_memory(address, 8))[0]

    def write_memory(self, address: int, data: bytes) -> None:
        self.command(
            self.cmd_memcpy(
                address,
                self.cmd_data_address(3),
                len(data)) + data,
            0)

    def write_memory_ptr(self, address: int, value: int) -> None:
        self.write_memory(
            address,
            struct.pack(
                '<%s' %
                self.cmd_arg_type(),
                value))

    def write_memory_uint8(self, address: int, value: int) -> None:
        self.write_memory(address, struct.pack('<B', value))

    def write_memory_uint16(self, address: int, value: int) -> None:
        self.write_memory(address, struct.pack('<H', value))

    def write_memory_uint32(self, address: int, value: int) -> None:
        self.write_memory(address, struct.pack('<I', value))

    def write_memory_uint64(self, address: int, value: int) -> None:
        self.write_memory(address, struct.pack('<Q', value))

    def cmd_arg_type(self) -> str:
        return 'Q' if self.platform.arch == 'arm64' else 'I'

    def cmd_arg_size(self) -> int:
        return 8 if self.platform.arch == 'arm64' else 4

    def cmd_data_offset(self, index: int) -> int:
        return 16 + index * self.cmd_arg_size()

    def cmd_data_address(self, index: int) -> int:
        return self.load_base() + self.cmd_data_offset(index)

    def cmd_memcpy(self, dest: int, src: int, length: int) -> bytes:
        return struct.pack(
            '<8s8x3%s' %
            self.cmd_arg_type(),
            MEMC_MAGIC,
            dest,
            src,
            length)

    def cmd_memset(self, address: int, c: int, length: int) -> bytes:
        return struct.pack(
            '<8s8x3%s' %
            self.cmd_arg_type(),
            MEMS_MAGIC,
            address,
            c,
            length)

    def load_base(self) -> int:
        if 'SRTG:' in self.serial_number:
            return self.platform.dfu_image_base
        else:
            return self.platform.dfu_load_base

    def image_base(self) -> int:
        if 'SRTG:' in self.serial_number:
            return self.platform.rom_base
        else:
            return self.platform.dfu_image_base

    def usb_serial_number(self, key: str) -> typing.Union[str, int, None]:
        for pair in self.serial_number.split(' '):
            if pair.startswith(key + ':'):
                k, v = pair.split(':')
                if v[0] == '[' and v[-1] == ']':
                    return v[1:-1]
                else:
                    return int(v, 16)
        return None

    def aes(self, data, action, key):
        assert len(data) % AES_BLOCK_SIZE == 0
        (retval,
         received) = self.execute(len(data),
                                  self.config.aes_crypto_cmd,
                                  action,
                                  self.cmd_data_address(7),
                                  self.cmd_data_address(0),
                                  len(data),
                                  key,
                                  0,
                                  0,
                                  data)
        assert retval & 0xFFFFFFFF == 0
        return received[:len(data)]

    def read_memory(self, address: int, length: int) -> bytes:
        data = bytes()
        while len(data) < length:
            part_length = min(
                length -
                len(data),
                USB_READ_LIMIT -
                self.cmd_data_offset(0))
            response = self.command(
                self.cmd_memcpy(
                    self.cmd_data_address(0),
                    address +
                    len(data),
                    part_length),
                self.cmd_data_offset(0) +
                part_length)
            assert response[:8] == DONE_MAGIC
            data += response[self.cmd_data_offset(0):]
        return data

    def command(self, request_data: bytes, response_length: int):
        assert 0 <= response_length <= USB_READ_LIMIT
        device = dfu.acquire_device(match=self.match)
        assert self.serial_number == device.serial_number
        dfu.send_data(device, '\0' * 16)
        device.ctrl_transfer(0x21, 1, 0, 0, 0, 100)
        device.ctrl_transfer(0xA1, 3, 0, 0, 6, 100)
        device.ctrl_transfer(0xA1, 3, 0, 0, 6, 100)
        dfu.send_data(device, request_data)

        # HACK
        if response_length == 0:
            response = device.ctrl_transfer(
                0xA1,
                2,
                0xFFFF,
                0,
                response_length + 1,
                CMD_TIMEOUT).tostring()[
                       1:]
        else:
            response = device.ctrl_transfer(
                0xA1, 2, 0xFFFF, 0, response_length, CMD_TIMEOUT).tostring()
        dfu.release_device(device)
        assert len(response) == response_length
        return response

    def execute(self, response_length, *args):
        cmd = bytes()
        for i in range(len(args)):
            if isinstance(args[i], int):
                cmd += struct.pack('<%s' % self.cmd_arg_type(), args[i])
            elif isinstance(args[i], bytes) and i == len(args) - 1:
                cmd += args[i]
            else:
                print(
                    'ERROR: usbexec.execute: invalid argument at position %s' %
                    i)
                sys.exit(1)
            if i == 0 and self.platform.arch != 'arm64':
                cmd += '\0' * 4
        response: bytes = self.command(
            EXEC_MAGIC +
            cmd,
            self.cmd_data_offset(0) +
            response_length)
        done, retval = struct.unpack(
            '<8sQ', response[:self.cmd_data_offset(0)])
        assert done == DONE_MAGIC
        return retval, response[self.cmd_data_offset(0):]
