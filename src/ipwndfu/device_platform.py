import pkgutil
import typing
from dataclasses import dataclass
from typing import Optional

import yaml


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

    return [DevicePlatform(**entry) for entry in entries]


all_platforms = _load_platforms()
