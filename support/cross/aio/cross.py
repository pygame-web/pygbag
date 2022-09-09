import sys

DEBUG = False

import aio.prepro

aio.prepro.DEBUG = DEBUG

# that sym cannot be overloaded in a simulator

if not defined("__WASM__"):
    if __import__("os").uname().machine.startswith("wasm"):
        import __WASM__
    else:
        __WASM__ = False

    define("__WASM__", __WASM__)


# those can


if not defined("__wasi__"):
    if __import__("sys").platform in ["wasi"]:
        import __wasi__
    else:
        __wasi__ = False

    define("__wasi__", __wasi__)

    # setup exception display with same syntax as upy
    import traceback

    def print_exception(e, out=sys.stderr, **kw):
        kw["file"] = out
        traceback.print_exc(**kw)

    sys.print_exception = print_exception
    del print_exception


# this *is* the cpython way
if hasattr(sys, "getandroidapilevel"):
    platform = defined("__ANDROID__")
    if not platform:
        print("importing platform __ANDROID__")
        try:
            import __ANDROID__ as platform
        except Exception as e:
            if hasattr(sys, "print_exception"):
                sys.print_exception(e)
            else:
                __import__("traceback").print_exc()

            pdb("__ANDROID__ failed to load, assuming simulator instead of error :")
            del platform

            # fake it
            platform == __import__("__main__")
        define("__ANDROID__", platform)
    try:
        __ANDROID_API__
    except:
        defined("__ANDROID_API__", sys.getandroidapilevel())


if sys.platform == "emscripten":
    platform = defined("__EMSCRIPTEN__")
    if not platform:
        print("importing platform __EMSCRIPTEN__")
        try:
            import __EMSCRIPTEN__ as platform
        except Exception as e:
            if hasattr(sys, "print_exception"):
                sys.print_exception(e)
            else:
                __import__("traceback").print_exc()

            pdb("__EMSCRIPTEN__ failed to load, assuming simulator instead of error :")
            del platform

            # fake it
            platform == __import__("__main__")
        define("__EMSCRIPTEN__", platform)


driver = defined("embed")
try:
    if not driver:
        import embed as driver

        print("platform embedding module driver :", driver)
except:
    # use the simulator defined platform value as the embed.
    driver = platform

# just in case it was not a module
sys.modules.setdefault("embed", driver)

try:
    # check it the embedding module was finished for that platform.
    # the least shoulbe syslog ( js console / adb logcat )
    driver.log
except:
    pdb(
        """\
WARNING: embed softrt/syslog functions not found
WARNING: also not in __main__ or simulator provided platform module
"""
    )
    driver.enable_irq = print
    driver.disable_irq = print
    driver.log = print

define("embed", driver)

platform.init_platform(driver)
sys.modules["platform"] = platform



# ================== leverage known python implementations ====================

# always come down to upy choices because cpython syntax can more easily be adapted


if not defined("__UPY__"):
    define("__UPY__", hasattr(sys.implementation, "mpy"))


if not __UPY__:
    # setup exception display with same syntax as upy
    import traceback

    def print_exception(e, out=sys.stderr, **kw):
        kw["file"] = out
        traceback.print_exc(**kw)

    sys.print_exception = print_exception
    del print_exception


scheduler = None
simulator = None
