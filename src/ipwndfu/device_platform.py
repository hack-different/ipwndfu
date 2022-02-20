import pkgutil
import typing
from dataclasses import dataclass, field
from typing import Optional

import yaml


@dataclass
class USBConstants:
    load_address: int
    exec_magic: int
    done_magic: int
    memc_magic: int
    mems_magic: int
    payload_offset: int
    payload_size: int
    usb_core_do_io: int


@dataclass
class DevicePlatform:
    cpid: int
    cprv: int
    scep: int
    arch: str
    srtg: str
    rom_base: int
    rom_size: int
    rom_sha1: str
    sram_base: int
    sram_size: int
    dram_base: int
    nonce_length: int
    sep_nonce_length: Optional[int]
    demotion_reg: int
    sigcheck_addr: int
    sigcheck_patch: int
    heap_state: int
    heap_write_hash: int
    heap_check_all: int
    usb: USBConstants
    gadgets: typing.Dict[str, int] = field(default_factory=dict)
    exploit_configs: typing.Dict[str, dict] = field(default_factory=dict)

    def name(self) -> str:
        if 0x8720 <= self.cpid <= 0x8960:
            return f"s5l{self.cpid}xsi"
        elif self.cpid in [0x7002, 0x8000, 0x8001, 0x8003]:
            return f"s{self.cpid}si"
        else:
            return f"t{self.cpid}si"


def _load_platforms() -> typing.Sequence[DevicePlatform]:
    data = pkgutil.get_data("ipwndfu", "data/platforms.yaml")

    assert data

    entries = yaml.safe_load(data)

    return [DevicePlatform(**entry) for entry in entries["modern_platforms"]]


all_platforms = _load_platforms()
