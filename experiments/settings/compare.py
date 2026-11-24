"""Compare the actual C loaders and candidate wrappers against the v1 record contract."""
import ctypes as ct
import re
import subprocess
from pathlib import Path

source = Path("launcher/src/storage.c").read_text()
legacy = subprocess.check_output(["git", "show", "HEAD:launcher/src/storage.c"], text=True)
def functions(text):
    return "\n".join(re.search(r"bool " + name + r"\([^)]*\) \{.*?\n\}", text, re.S)[0]
                     for name in ("np_motion_load", "np_theme_load"))
fixture = """
#include <stdint.h>
#include <stdbool.h>
#define THEME_NAME "twili.set"
#define MOTION_NAME "twili_anim.set"
static const uint8_t *buf;
static uint32_t size;
void record(const uint8_t *p, uint32_t n) { buf=p; size=n; }
static const uint8_t *ef_read(const char *name, uint32_t *n) { *n=size; return buf; }
extern int tw_theme_id(const uint8_t *, uint32_t);
extern bool tw_motion(const uint8_t *, uint32_t);
"""
out = Path("build/settings-pilot")
out.mkdir(parents=True, exist_ok=True)
apis = []
for kind, text in (("c", legacy), ("rust", source)):
    c = out / (kind + ".c")
    lib = out / (kind + ".so")
    c.write_text(fixture + functions(text))
    objects = [str(out / "host.o")] if kind == "rust" else []
    subprocess.run(["cc", "-O2", "-shared", "-fPIC", str(c), *objects, "-o", str(lib)], check=True)
    api = ct.CDLL(str(lib.resolve()))
    api.record.argtypes = [ct.c_void_p, ct.c_uint32]
    api.np_motion_load.restype = api.np_theme_load.restype = ct.c_bool
    api.np_theme_load.argtypes = [ct.POINTER(ct.c_int)]
    apis.append(api)

def check(buf, length):
    for api in apis:
        api.record(buf, length)
        theme = ct.c_int(-7)
        valid = buf is not None and length == 3 and buf[:2] == b"T\x01"
        assert api.np_theme_load(ct.byref(theme)) == valid
        assert theme.value == (buf[2] if valid else -7)
        assert api.np_motion_load() == (buf is None or length != 2 or buf != b"\x01\x00")

count = 0
for n in (0,1,2,3,4,0xffffffff):
    check(None,n)
    count += 1
for n in (0,1,4,5):
    check(bytes(range(n)),n)
    count += 1
for a in range(256):
    for b in range(256):
        check(bytes((a,b)),2)
        check(bytes((84,a,b)),3)
        check(bytes((a,1,b)),3)
        count += 3
print(f"PASS {count} settings cases per implementation")
