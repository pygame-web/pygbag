""" packager+server for pygbag wasm loader """

import sys
from pathlib import Path


__version__ = "0.7.2"

# make aio available

sys.path.append(str(Path(__file__).parent / "support/cross"))

# hack to test git cdn build without upgrading pygbag
# beware can have side effects when file packager behaviour must change !
if "--git" in sys.argv:
    print(
        """

    ******* forcing git cdn *********

"""
    )
    __version__ = "0.0.0"
    sys.argv.remove("--git")


# WaPy=>CPython compat

import builtins

try:
    sched_yield
except:
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


builtins.ESC = ESC
builtins.CSI = CSI
