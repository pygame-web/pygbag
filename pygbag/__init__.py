__version__ = "0.1.2"

try:
    sched_yield
except:
    __import__("builtins").sched_yield = lambda: None

import sys, traceback


def print_exception(e, out=sys.stderr, **kw):
    kw["file"] = out
    traceback.print_exc(**kw)


sys.print_exception = print_exception

import builtins


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
