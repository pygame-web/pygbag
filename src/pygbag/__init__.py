""" packager+server for pygbag wasm loader """

" ^(⌒(oo)⌒)^ "

import sys

# some Linux distro are stuck in the past. Better safe than sorry
sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path

VERSION = "0.9.2"

# hack to test git cdn build without upgrading pygbag
# beware can have side effects when file packager behaviour must change !
if "--git" in sys.argv:
    print(
        """

    ******* forcing git cdn *********

"""
    )
    VERSION = "0.0.0"

# make aio available
if not sys.platform in ("emscripten", "wasi"):
    # must be first for readline
    sys.path.insert(0, str(Path(__file__).parent / "support"))
sys.path.append(str(Path(__file__).parent / "support/cross"))


# WaPy/Micropython <=> CPython compat

import builtins

try:
    # embed builtin module handles I/O on wasm
    import embed

    # aio function implemented only on stackless WaPy
    sched_yield
except:
    builtins.sched_yield = lambda: None

import sys, traceback

if not hasattr(sys, "print_exception"):

    def print_exception(e, out=sys.stderr, **kw):
        kw["file"] = out
        traceback.print_exc(**kw)

    sys.print_exception = print_exception


def iter_byte(ba):
    for idx in range(len(ba)):
        yield bytes([ba[idx]])


builtins.iter_byte = iter_byte


def iter_ord(ba):
    for idx in range(len(ba)):
        yield ba[idx]


builtins.iter_ord = iter_ord


def ESC(*argv, flush=True):
    for arg in argv:
        sys.__stdout__.write(chr(0x1B))
        sys.__stdout__.write(arg)
    if flush:
        sys.stdout.flush()


def CSI(*argv):
    for arg in argv:
        ESC(f"[{arg}", flush=False)
    sys.stdout.flush()


builtins.CSI = CSI
builtins.ESC = ESC
