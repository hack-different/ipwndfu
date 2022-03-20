import pathlib

import unicorn
from unicorn import *
from unicorn.arm64_const import *

TESTS_DIR = pathlib.Path(__file__).parent
ROMS_DIR = TESTS_DIR.parent / "ext" / "roms" / "resources" / "APROM"


def test_run_secure_rom_8015():
    t8015_rom = ROMS_DIR / "SecureROM for t8015si, iBoot-3332.0.0.1.23"
    stat = t8015_rom.stat()

    def reg_callback(uc, reg, var, data):
        print(reg)
        print(var)

    engine = unicorn.Uc(UC_ARCH_ARM64, UC_MODE_ARM)

    engine.hook_add(UC_ARM64_INS_MRS, reg_callback)
    engine.hook_add(UC_ARM64_INS_MSR, reg_callback)

    with t8015_rom.open("rb") as rom:
        engine.mmio_map(0x18001C000, stat.st_size, rom.read, None, None, None)
        engine.mem_protect(0x18001C000, stat.st_size, UC_PROT_READ | UC_PROT_EXEC)

        engine.mem_map(0x800000000, stat.st_size)

        engine.emu_start(0x18001C000, 0x880000000, 10)
