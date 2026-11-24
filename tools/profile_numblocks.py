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


def module_functions(module, entry):
    with module.open("rb") as stream:
        elf = ELFFile(stream)
        table = elf.get_section_by_name(".symtab")
        text = elf.get_section_index(".text")
        base = entry - (table.get_symbol_by_name("main")[0]["st_value"] & ~1)
        functions = []
        for symbol in table.iter_symbols():
            if (symbol["st_shndx"] == text and symbol["st_info"]["type"] == "STT_FUNC"
                    and symbol["st_size"]):
                start = base + (symbol["st_value"] & ~1)
                functions.append((start, start + symbol["st_size"], symbol.name))
        return sorted(functions)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build", type=Path)
    args = parser.parse_args()
    emu.configure("n0120", "epsilon", 148928, apps_start=0x90180000)
    calc = emu.Calculator(str(args.build / "TwiliPlay.nwa"))
    functions = module_functions(args.build / "modules/numblocks.1.o",
                                 calc.symbols["np_numblocks_main"] & ~1)
    starts = [start for start, _, _ in functions]
    _, save, keys, home, _, _ = GAMES["numblocks"]
    navigation, quit_at = through_launcher(CATALOGUE.index("numblocks"), keys, home)
    shift = quit_at - home
    calc.keys = navigation + [(quit_at, quit_at + 400, emu.KEYS["home"])]
    calc.run(shift + 8700)
    calc.samples = []
    calc.run(shift + 10200)
    samples = calc.samples
    calc.samples = None
    screen_hash = sha256(calc.screen).hexdigest()
    calc.run(quit_at + 3000)
    world = dict(records(calc.storage_bytes())).get(save, b"")
    if not (calc.exited and calc.left_home and calc.app_ram_clean() and CHECKS["numblocks"][0](world)):
        raise RuntimeError("World creation, Home exit or RAM cleanup failed")
    counts = Counter()
    for pc in samples:
        i = bisect_right(starts, pc) - 1
        name = functions[i][2] if i >= 0 and pc < functions[i][1] else "(outside mapped functions)"
        counts[name] += 1
    if sum(counts.values()) == counts["(outside mapped functions)"]:
        raise RuntimeError("No samples inside mapped NumBlocks functions")
    print(f"Walking window 8700-10200 ms relative to replay; {len(samples)} CPU samples")
    for name, count in counts.most_common(12):
        print(f"{count:5d} {100 * count / len(samples):5.1f}%  {name}")
    print(f"RGB565 SHA256 {screen_hash}; world SHA256 {sha256(world).hexdigest()}")
    print(f"PASS saved world, Home exit, clean app RAM; observed stack {calc.stack_used()} bytes")


if __name__ == "__main__":
    main()
