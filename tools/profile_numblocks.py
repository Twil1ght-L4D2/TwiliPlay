"""Sample the packaged NumBlocks module during the existing world creation / walking replay."""
import argparse
from bisect import bisect_right
from collections import Counter
from hashlib import sha256
from pathlib import Path
import sys

from elftools.elf.elffile import ELFFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from test_games import CHECKS, GAMES, emu, records, through_launcher
from foundation import GAMES as CATALOGUE


def module_symbols(module, calculator):
    with module.open("rb") as stream:
        elf = ELFFile(stream)
        table = elf.get_section_by_name(".symtab")
        text = elf.get_section_index(".text")
        entry = calculator.symbols["np_numblocks_main"] & ~1
        base = entry - (table.get_symbol_by_name("main")[0]["st_value"] & ~1)
        functions = []
        counters = {}
        for symbol in table.iter_symbols():
            name = symbol.name.split(".")[0]
            if name in ("ticks_run", "perf_frames"):
                section = elf.get_section(symbol["st_shndx"]).name
                if section not in (".data", ".bss") or symbol["st_size"] != 4 or name in counters:
                    raise ValueError(f"unexpected counter definition: {symbol.name}")
                counters[name] = calculator.symbols[f"np_numblocks_{section[1:]}"] + symbol["st_value"]
            if (symbol["st_shndx"] == text and symbol["st_info"]["type"] == "STT_FUNC"
                    and symbol["st_size"]):
                start = base + (symbol["st_value"] & ~1)
                functions.append((start, start + symbol["st_size"], symbol.name))
        return sorted(functions), counters


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build", type=Path)
    args = parser.parse_args()
    emu.configure("n0120", "epsilon", 148928, apps_start=0x90180000)
    calc = emu.Calculator(str(args.build / "TwiliPlay.nwa"))
    calc.enable_checks()
    functions, counters = module_symbols(args.build / "modules/numblocks.1.o", calc)

    def counter(name):
        return int.from_bytes(calc.uc.mem_read(counters[name], 4), "little")

    starts = [start for start, _, _ in functions]
    _, save, keys, home, _, _ = GAMES["numblocks"]
    navigation, quit_at = through_launcher(CATALOGUE.index("numblocks"), keys, home)
    shift = quit_at - home
    calc.keys = navigation + [(quit_at, quit_at + 400, emu.KEYS["home"])]
    calc.run(shift + 8700)
    frames_before, ticks_before = counter("perf_frames"), counter("ticks_run")
    calc.samples = []
    calc.run(shift + 10200)
    frames = counter("perf_frames") - frames_before
    ticks = counter("ticks_run") - ticks_before
    if frames <= 0 or ticks <= 0:
        raise RuntimeError("Walking replay did not advance frames and simulation ticks")
    samples = calc.samples
    calc.samples = None
    screen_hash = sha256(calc.screen).hexdigest()
    calc.run(quit_at + 3000)
    world = dict(records(calc.storage_bytes())).get(save, b"")
    if not (calc.exited and calc.left_home and calc.app_ram_clean() and CHECKS["numblocks"][0](world)):
        raise RuntimeError("World creation, Home exit or RAM cleanup failed")
    stack = calc.stack_used()
    if stack > 30 * 1024 or calc.violations or calc.firmware_ram_changes():
        raise RuntimeError(f"Memory guard failed (stack {stack}, violations {calc.violations[:3]})")
    counts = Counter()
    for pc in samples:
        i = bisect_right(starts, pc) - 1
        name = functions[i][2] if i >= 0 and pc < functions[i][1] else "(outside mapped functions)"
        counts[name] += 1
    if sum(counts.values()) == counts["(outside mapped functions)"]:
        raise RuntimeError("No samples inside mapped NumBlocks functions")
    print(f"Walking window 8700-10200 ms relative to replay; {len(samples)} CPU samples")
    print(f"Game loop advanced {frames} frames and {ticks} simulation ticks in this window")
    for name, count in counts.most_common(12):
        print(f"{count:5d} {100 * count / len(samples):5.1f}%  {name}")
    print(f"RGB565 SHA256 {screen_hash}; world SHA256 {sha256(world).hexdigest()}")
    print(f"PASS saved world, Home exit, clean app RAM; observed stack {stack} bytes")


if __name__ == "__main__":
    main()
