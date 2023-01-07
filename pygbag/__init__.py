""" packager+server for pygbag wasm loader """

__version__ = "0.6.2"


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


def CSI(*argv):
    for arg in argv:
        sys.__stdout__.write(chr(0x1B))
        sys.__stdout__.write("[")
        sys.__stdout__.write(arg)


builtins.ESC = ESC
builtins.CSI = CSI
