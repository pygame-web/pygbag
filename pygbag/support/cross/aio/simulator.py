print("= ${__FILE__} in websim  for  ${PLATFORM} =")


# ===============================================
import sys, os, builtins
try:
    import pymunk4 as pymunk
    sys.modules['pymunk'] = pymunk
except:
    print("pymunk4 was not build for simulator")


# need them earlier than aio


def pdb(*argv):
    print(*argv, file=sys.__stderr__)


builtins.pdb = pdb


def print_exception(e, out=sys.stderr, **kw):
    kw["file"] = out
    traceback.print_exc(**kw)


sys.print_exception = print_exception


# aioprompt ======== have asyncio loop runs interleaved with repl ============
# from https://github.com/pmp-p/aioprompt

scheduled = []
scheduler = None
wrapper_ref = None
loop = None

next_tick = 0

unsupported = ("bionic", "wasm", "emscripten", "wasi", "android")

# TODO: all readline replacement with accurate timeframes
# TODO: droid integrate application lifecycle

if sys.platform not in unsupported:
    import sys
    import builtins
    import ctypes
    import time

    if not sys.flags.inspect:
        print(
            "Error: interpreter must be run with -i or PYTHONINSPECT must be set for using",
            __name__,
        )
        raise SystemExit

    def sched_init():
        global scheduled, scheduler, wrapper_ref
        #! KEEP IT WOULD BE GC OTHERWISE!
        # wrapper_ref

        #scheduled = []
        import ctypes

        try:
            ctypes = ctypes.this
        except:
            pass

        c_char_p = ctypes.c_char_p
        c_void_p = ctypes.c_void_p

        HOOKFUNC = ctypes.CFUNCTYPE(c_char_p)
        PyOS_InputHookFunctionPointer = c_void_p.in_dll(
            ctypes.pythonapi, "PyOS_InputHook"
        )

        def scheduler():
            global scheduled
            # prevent reenter
            lq = len(scheduled)
            while lq:
                fn, a = scheduled.pop(0)
                fn(a)
                lq -= 1

        wrapper_ref = HOOKFUNC(scheduler)
        scheduler_c = ctypes.cast(wrapper_ref, c_void_p)
        PyOS_InputHookFunctionPointer.value = scheduler_c.value

#        # replace with faster function
#        def schedule(fn, a):
#            scheduled.append((fn, a))
#
        sys.modules[__name__].schedule = schedule

        # now the init code is useless
        del sys.modules[__name__].sched_init

    def schedule(fn, a):
        global scheduled, next_tick
        if next_tick==0:
            sched_init()
        next_tick = time.time() + .016
        # cpu cool down
        cooldown = next_tick - time.time()
        if cooldown>0:
            time.sleep(cooldown)
        scheduled.append((fn, a))

else:
    pdb("aiorepl no possible on", sys.platform, "expect main to block")
    schedule = None

# =====================================================

sys.path.append("${PLATFORM}")


# cannot fake a cpu __WASM__ will be False

# but fake the platform AND the module
sys.platform = "emscripten"


class __EMSCRIPTEN__(object):
    def __init__(self):
        import platform
        self.platform = platform

    def __getattribute__(self, name):
        try:
            return object.__getattribute__(self, name)
        except:
            return object.__getattribute__(self.platform, name)

    @classmethod
    def PyConfig_InitPythonConfig(*argv):
        pass

    @classmethod
    def init_platform(*argv):
        pass

    @classmethod
    def flush(cls):
        sys.stdout.flush()
        sys.stderr.flush()

    @classmethod
    def trap(cls, *argv, **kw):
        pass

    @classmethod
    def system(cls):
        return 'Linux'

    is_browser = False

    js = pdb
    run_script = pdb

__EMSCRIPTEN__ = __EMSCRIPTEN__()

sys.modules["__EMSCRIPTEN__"] = __EMSCRIPTEN__
sys.modules["embed"] = __EMSCRIPTEN__


import aio
import aio.prepro
import aio.cross

aio.cross.simulator = True


exec(open("${PYTHONRC}").read(), globals(), globals())


# ===============================================================================

import aio.clock


# ===============================================================================
import inspect
import asyncio

DEBUG = 1

if __name__ == "__main__":
    aio.DEBUG = DEBUG

    print("main may block depending on your platform readline implementation")

    if schedule:
        aio.cross.scheduler = schedule

    # asyncio.create_task( aio.clock.loop() )
    aio.clock.start(x=80)

    __main__ = execfile("${__FILE__}")
    # on not arduino style, expect user to run main with asyncio.run( main() )
    # should be already called at this point.

    setup = vars(__main__).get("setup", None)
    loop = vars(__main__).get("loop", None)

    # arduino naming is just wrong anyway
    if loop is None:
        loop = vars(__main__).get("step", None)

    if loop and setup:
        print("found setup, loop")
        if setup:
            setup()
    if loop:
        if not inspect.iscoroutinefunction(loop):
            if loop and setup:
                print("loop is not a coroutine, running arduino style")
                aio.steps.append(loop)
            # TODO : use a wrapper for non readline systems.

            async def coro():
                loop()

        else:
            coro = loop

        if not aio.started:
            aio.started = True
            if DEBUG:
                pdb("200: starting aio scheduler")
            aio.cross.scheduler(aio.step, 1)

    print(" -> asyncio.run passed")
    sys.stdout.flush()
    sys.stderr.flush()


#
