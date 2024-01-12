import sys
import aio
import platform

MODULES = list(sys.modules.keys())
MAIN = list(vars(__import__("__main__")).keys())
BUILTINS = list(vars(__import__("builtins")).keys())


def cleanup():
    import sys, random

    for mod in list(sys.modules.keys()):
        if mod in ("asyncio"):
            continue
        if not mod in MODULES:
            sys.modules.pop(mod, None)

    md = vars(__import__("__main__"))
    for name in list(md.keys()):
        if not name in MAIN:
            md.pop(name, None)

    md = vars(__import__("builtins"))
    for var in list(md.keys()):
        if not name in BUILTINS:
            md.pop(name, None)

    del mod, name, md
    __import__("importlib").invalidate_caches()
    __import__("gc").collect()

    random.seed(1)

    aio.exit = False
    aio.paused = False
    print(" - cycling done -")
    try:
        platform.set_window_title("idle")
        platform.prompt()
    except:
        pass

    def resume():
        aio.paused
