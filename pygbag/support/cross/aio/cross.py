import sys

DEBUG = False

import aio.prepro

aio.prepro.DEBUG = DEBUG


#
platform_impl = False

if not defined("iter_byte"):

    def iter_byte(ba):
        for idx in range(len(ba)):
            yield bytes([ba[idx]])

    define("iter_byte", iter_byte)
    del iter_byte

    # this is default behaviour for cpython over a bytes() sequence.
    def iter_ord(ba):
        for idx in range(len(ba)):
            yield ba[idx]

    define("iter_ord", iter_ord)
    del iter_ord


# ================== leverage known python implementations ====================

# always come down to upy choices because cpython/pkpy syntax can more easily be adapted

if not defined("__UPY__"):
    define("__UPY__", hasattr(sys.implementation, "_mpy"))

    if not __UPY__:
        # setup exception display with same syntax as upy
        import traceback

        def print_exception(e, out=sys.stderr, **kw):
            kw["file"] = out
            traceback.print_exc(**kw)

        sys.print_exception = print_exception
        del print_exception
else:
    define("const", lambda x: x)

# cant mod sys on upy but it does not need flush
if not __UPY__:
    sys.__eot__ = chr(4) + chr(10)

if not defined("__PKPY__"):
    try:
        vars
        __PKPY__ = None
    except:
        import builtins

        if not defined("vars"):

            def vars(o):
                return o.__dict__

            define("vars", vars)
        del vars

        class __PKPY__:
            cm = {}
            current_class = "?"

            def classmethod(fn):
                def cm_fn(*argv, **kw):
                    cr = __PKPY__.cm[cm_fn]
                    if len(argv):
                        if argv[0].__class__ == cr["cc"]:
                            return fn(argv[0].__class__, *argv[1:], **kw)
                    return fn(cr["cc"], *argv, **kw)

                __PKPY__.cm[cm_fn] = {"fn": fn}  # , 'cn': current_class}
                return cm_fn

            def classmethods(klass):
                for fn, func in vars(klass).items():
                    try:
                        if func in __PKPY__.cm:
                            cr = __PKPY__.cm[func]
                            # if cr["cn"] == klass.__name__:
                            cr["cc"] = klass
                    except TypeError:
                        continue
                return klass

        define("classmethod", __PKPY__.classmethod)
        define("classmethods", __PKPY__.classmethods)

    define("__PKPY__", __PKPY__)

# support pkpy methods
if not defined("classmethods"):
    define("classmethods", lambda x: x)


if not defined("__WASM__"):
    try:
        # that sym cannot be overloaded in the simulator
        if __import__("os").uname().machine.startswith("wasm"):
            import __WASM__
        else:
            __WASM__ = False
    except AttributeError:
        # upy does not have os.uname
        __WASM__ = True

    define("__WASM__", __WASM__)


if not defined("__wasi__"):
    if sys.platform == "wasi":
        import __wasi__
    else:
        __wasi__ = False

define("__wasi__", __wasi__)


# this *is* the cpython way
if hasattr(sys, "getandroidapilevel"):
    platform_impl = defined("__ANDROID__")
    if not platform_impl:
        print("importing platform_impl __ANDROID__")
        try:
            import __ANDROID__ as platform_impl
        except Exception as e:
            if hasattr(sys, "print_exception"):
                sys.print_exception(e)
            else:
                __import__("traceback").print_exc()

            pdb("__ANDROID__ failed to load, assuming simulator instead of error :")
            del platform_impl

            # fake it
            platform_impl == __import__("__main__")
        define("__ANDROID__", platform_impl)
    try:
        __ANDROID_API__
    except:
        defined("__ANDROID_API__", sys.getandroidapilevel())

define("__ANDROID__", platform_impl)


if sys.platform == "emscripten":
    platform_impl = defined("__EMSCRIPTEN__")
    if not platform_impl:
        try:
            import __EMSCRIPTEN__ as platform_impl
        except Exception as e:
            if hasattr(sys, "print_exception"):
                sys.print_exception(e)
            else:
                __import__("traceback").print_exc()

            pdb("__EMSCRIPTEN__ failed to load, assuming simulator instead of error :")
            del platform_impl

            # fake it
            platform_impl == __import__("__main__")

define("__EMSCRIPTEN__", platform_impl)


driver = defined("embed")
try:
    if not driver:
        import embed as driver
except:
    # else use the simulator defined platform_impl value as the embed.
    driver = platform_impl
if driver:
    # just in case it was not a module
    sys.modules.setdefault("embed", driver)

    try:
        # check it the embedding module was finished for that platform_impl.
        # the least shoulbe syslog ( js console / adb logcat )
        driver.log
    except:
        pdb(
            """\
    WARNING: embed softrt/syslog functions not found
    WARNING: also not in __main__ or simulator provided platform_impl module
    """
        )
        driver.enable_irq = print
        driver.disable_irq = print
        driver.log = print

    define("embed", driver)

    platform_impl.init_platform(driver)
    sys.modules["platform"] = platform_impl


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
