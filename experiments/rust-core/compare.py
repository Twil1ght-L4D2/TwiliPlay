"""Compare two leaf functions on the same Cortex-M Thumb inputs."""
import random
import sys
from pathlib import Path
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_MODE_MCLASS, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_LR

def results(file, cases):
    code = Path(file).read_bytes()
    cpu = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
    cpu.mem_map(0x1000, 0x2000)
    cpu.mem_write(0x1000, code)
    steps = 0
    def tick(*_):
        nonlocal steps
        steps += 1
    cpu.hook_add(UC_HOOK_CODE, tick)
    outputs = []
    for a, b, t in cases:
        for reg, value in zip((UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_LR),
                              (a, b, t, 0x2001)):
            cpu.reg_write(reg, value)
        cpu.emu_start(0x1001, 0x2000, count=100)
        outputs.append(cpu.reg_read(UC_ARM_REG_R0))
    print(f"{file}: {len(code)} function bytes, {steps} executed instructions")
    return outputs

colors = (0, 0xffff, 0xf800, 0x07e0, 0x001f, 0xaaaa, 0x5555)
rng = random.Random(2026)
cases = [(a, b, t) for a in colors for b in colors for t in range(33)]
cases += [(rng.randrange(65536), rng.randrange(65536), t) for t in range(33) for _ in range(128)]
def reference(a,b,t):
    return sum(((((a >> shift) & mask)*(32-t) + ((b >> shift) & mask)*t) // 32) << shift
               for shift,mask in ((11,31),(5,63),(0,31)))
expected = [reference(*args) for args in cases]
for file in sys.argv[1:]:
    assert results(file, cases) == expected, file
print(f"PASS {len(cases)} cases per implementation")
