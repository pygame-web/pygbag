""" packager+server for pygbag wasm loader """

import sys

# some Linux distro are stuck in the past. Better safe than sorry
sys.stdout.reconfigure(encoding="utf-8")

from pathlib import Path

__version__ = "0.8.2"

# hack to test git cdn build without upgrading pygbag
# beware can have side effects when file packager behaviour must change !
if "--git" in sys.argv:
    print(
        """

    ******* forcing git cdn *********

"""
    )
    __version__ = "0.0.0"


# make aio available

sys.path.append(str(Path(__file__).parent / "support/cross"))


# WaPy<=>CPython compat

try:
    # embed builtin module handles I/O on wasm
    import embed

    # aio function implemented only on stackless WaPy
    sched_yield
except:
    import builtins

    builtins.sched_yield = lambda: None

import sys, traceback

if not hasattr(sys, "print_exception"):

    def print_exception(e, out=sys.stderr, **kw):
        kw["file"] = out
        traceback.print_exc(**kw)

    sys.print_exception = print_exception


def ESC(*argv):
    for arg in argv:
        sys.__stdout__.write(chr(0x1B))
        sys.__stdout__.write(arg)
    embed.flush()


def CSI(*argv):
    for arg in argv:
        ESC(f"[{arg}")
