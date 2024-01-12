import sys
import builtins
import inspect


DEBUG = True
NICE = 0.010

perf_index = None
load_avg = "0.000"
load_min = "0.000"
load_max = "0.000"

frame = 1.0 / 60

builtins.aio = sys.modules[__name__]

# try to acquire syslog early

# TODO: use PyConfig debug flag
try:
    import embed

    def pdb(*argv):
        # print(*argv, file=sys.__stderr__)
        pass

    # builtins.pdb = embed.log
    builtins.pdb = pdb
except:

    def pdb(*argv):
        # print(*argv, file=sys.__stderr__)
        pass

    builtins.pdb = pdb


# cascade debug by default
from . import cross

if not __UPY__:
    from time import time as time_time

    # file+socket support  fopen/sopen
    from .filelike import *
else:
    import utime

    time_time = utime.ticks_ms


cross.DEBUG = DEBUG


# =========================================================================

# TODO: dbg stuff should be in the platform module in aio.cross
# usefull https://pymotw.com/3/sys/tracing.html
# upy has no trace module
if DEBUG and not __UPY__:
    import trace

    _tracer = trace.Trace(count=False, trace=True)

    def sys_trace(fn, *argv, **kw):
        global _tracer
        return _tracer.runfunc(fn, *argv, **kw)

else:

    def sys_trace(fn, *argv, **kw):
        pdb("debugging is OFF")
        return fn(*argv, **kw)


define("sys_trace", sys_trace)

try:
    import embed

    flush = embed.flush
except:

    def flush():
        sys.stdout.flush()
        sys.stderr.flush()

    if __WASM__:
        print(
            """



    WARNING: no flush method available, raw TTY may suffer



"""
        )


# ==================================================================

try:
    undefined
except:

    class sentinel:
        def __bool__(self):
            return False

        def __len__(self):
            return 0

        def __repr__(self):
            return "∅"

        def __nonzero__(self):
            return 0

        def __call__(self, *argv, **kw):
            if len(argv) and argv[0] is self:
                return True
            print("Null Pointer Exception")

    sentinel = sentinel()
    define("undefined", sentinel)
    del sentinel


def overloaded(i, *attrs):
    for attr in attrs:
        if attr in vars(i.__class__):
            if attr in vars(i):
                return True
    return False


define("overloaded", overloaded)
del overloaded

# by default no thread support.
sync = True
builtins.synchronized = lambda f: f


started = False
paused = False
exit = False
steps = []
oneshots = []
ticks = 0
protect = []
last_state = None
tasks = []
is_async_ctx = False
no_exit = True

enter = time_time()
spent = 0.00001
leave = enter + spent

from asyncio import *
from asyncio import exceptions

__run__ = run

if __UPY__:

    def _set_running_loop(l):
        pass

    sys.modules["asyncio.events"] = aio
    aio.get_running_loop = aio.get_event_loop
    events = aio
else:
    from asyncio.events import _set_running_loop


# Within a coroutine, simply use `asyncio.get_running_loop()`,
# since the coroutine wouldn't be able
# to execute in the first place without a running event loop present.
try:
    loop = get_running_loop()
except RuntimeError:
    # depending on context, you might debug or warning log that a running event loop wasn't found
    loop = get_event_loop()


# import asyncio.events
# asyncio.events._set_running_loop(loop)
_set_running_loop(loop)


sys.modules["asyncio"] = __import__(__name__)


def defer(fn, argv=(), kw={}, delay=0, framerate=60):
    global ticks, oneshots
    # FIXME: set ticks + deadline for alarm
    if __UPY__:
        tb = "n/i"
    else:
        try:
            frm = inspect.currentframe().f_back
            tb = f"{inspect.getframeinfo(frm).filename}:{frm.f_lineno}"
        except:
            tb = "no frame"

    oneshots.append(
        [
            ticks + int(delay / framerate),
            fn,
            argv,
            kw,
            tb,
        ]
    )


inloop = False


# this runs both asyncio loop and the arduino style stepper
def step(*argv):
    global inloop, last_state, paused, started, loop, oneshots, protect
    global ticks, steps, step, flush, exit, is_async_ctx
    global enter, leave, spent

    enter = time_time()

    # those hold variable that could be processed by C
    # outside the pyloop, to keep them from GC
    if protect:
        protect.clear()

    # this one is for full stop
    if not started:
        return

    try:
        # TODO: OPTIM: remove later
        if inloop:
            pdb("97: FATAL: aio loop not re-entrant !")
            paused = True
            return
        inloop = True

        if paused is not last_state:
            if not exit:
                pdb(f" - aio is {'paused' if paused else 'resuming'} -")
            else:
                print(f" - aio is exiting -")
            last_state = paused

        ticks += 1

        try:
            # defer and oneshot can run even if main loop is paused
            # eg for timekeep, or vital remote I/O sakes

            # NEED a scheduler + timesort
            early = []
            while len(oneshots):
                deferred = oneshots.pop()
                if deferred[0] > ticks:
                    deferred[0] -= 1
                    early.append(deferred)
                else:
                    _, fn, argv, kw, tb = deferred
                    try:
                        fn(*argv, **kw)
                    except Exception as e:
                        sys.print_exception(e)
                        print("--- stack -----", file=sys.__stderr__)
                        print(_, fn, argv, kw, file=sys.__stderr__)
                        print("--- stack -----", file=sys.__stderr__)
                        print("deferred from", tb, file=sys.__stderr__)

            while len(early):
                oneshots.append(early.pop())

            # TODO: fix global clock accordingly
            if not paused:
                for onestep in steps:
                    onestep()

                # loop.call_soon(loop.stop)
                # loop.run_forever()
                if started:
                    is_async_ctx = True
                    loop._run_once()
                    is_async_ctx = False

        except Exception as e:
            sys.print_exception(e)
            paused = True
            pdb("- aio paused -")

        # if using external loop handler (eg  PyOS_InputHook ) then call us again
        if started and cross.scheduler and not exit:
            cross.scheduler(step, 1)

        flush()
        inloop = False
    finally:
        leave = time_time()
        spent = leave - enter


def delta(t=None):
    global enter
    if t:
        return t - enter
    return time_time() - enter


def shed_yield():
    global enter, NICE
    return (time_time() - enter) > NICE


async def sleep_ms(ms=0):
    await sleep(float(ms) / 1000)


def _set_task_name(task, name):
    if name is not None:
        try:
            set_name = task.set_name
        except AttributeError:
            warnings.warn(
                "Task.set_name() was added in Python 3.8, "
                "the method support will be mandatory for third-party "
                "task implementations since 3.13.",
                DeprecationWarning,
                stacklevel=3,
            )
        else:
            set_name(name)


def create_task(coro, *, name=None, context=None):
    global loop, tasks

    tasks.append(coro)
    if context is None:
        # Use legacy API if context is not needed
        task = loop.create_task(coro, name=name)
    else:
        task = loop.create_task(coro, name=name, context=context)

    _set_task_name(task, name)
    return task


#
run_called = False


def is_running():
    global started
    return started


# prevent warnings in aiohttp
loop.is_running = is_running


def run(coro, *, debug=False):
    global paused, loop, started, step, DEBUG, run_called, exit

    debug = debug or DEBUG

    if coro is not None:
        wrapper = coro
        if coro.__name__ == "main":
            if "aio.fetch" in sys.modules:

                async def __main__():
                    import aio.fetch

                    await aio.fetch.preload()
                    await coro

                wrapper = __main__()
        task = loop.create_task(wrapper)
        _set_task_name(task, coro.__name__)

    if not started:
        exit = False
        run_called = True
        started = True

        # the stepper fonction when in simulator is called from pygbag.aio
        # and is blocking script
        if aio.cross.simulator:
            # cannot be sure asyncio.run() will be used
            # so don't handle loop here
            return

        #        if cross.scheduler:
        #            if debug:
        #                pdb("261: asyncio handler is", cross.scheduler)
        #            paused = False
        #            cross.scheduler(step, 1)

        # the stepper when called from  window.requestAnimationFrame()
        # https://developer.mozilla.org/en-US/docs/Web/API/window/requestAnimationFrame
        elif __EMSCRIPTEN__ or __wasi__:
            # handle special custom_site() case
            if coro.__name__ == "import_site":
                embed.run()
                run_called = False
            elif coro.__name__ == "custom_site":
                run_called = False
            elif not aio.cross.simulator:
                # let prelinker start asyncio loop
                print("AIO will auto-start at 0+, now is", embed.counter())

        # fallback to blocking asyncio
        else:
            _set_running_loop(None)
            # TODO: implement RaF from here
            try:
                loop.run_forever()
            except KeyboardInterrupt:
                print("301: closing loop")
                loop.close()

    elif run_called:
        pdb("273: aio.run called twice !!!")

    # run called after a custom_site() completion
    elif coro.__name__ != "custom_site":
        pdb("360: * custom_site done *")
    else:
        pdb("364: aio.run", coro.__name__)


def exit_now(ec):
    global exit, paused
    if exit:
        print("already exiting ...")
        return
    # rescheduling happens only where started is True
    exit = True
    while len(tasks):
        task = tasks.pop(0)
        if hasattr(task, "cancel"):
            print(f"290: canceling {task}")
            task.cancel()

    #  will prevent another asyncio loop call, we exit next cycle on oneshots queue
    paused = True
    if not __WASM__:
        pdb("291: exiting with code", ec)
    defer(__exit__, (ec,), {}, 0)


# replace sys.exit on wasm

if __WASM__:

    def __exit__(ec):
        global loop, no_exit
        if no_exit:
            pdb(f"sys.exit({ec})")
        else:
            loop.close()
        try:
            aio.recycle.cleanup()
            aio.defer(embed.prompt, (), {}, delay=300)
        except:
            pass

else:
    __exit__ = sys.exit


def aio_exit(maybecoro=0):
    if inspect.iscoroutine(maybecoro):

        async def atexit(coro):
            exit_now(await coro)

        run(atexit(maybecoro))
    else:
        # if __WASM__:
        #    pdb("309: NOT A CORO", maybecoro)
        exit_now(maybecoro)


if not __UPY__:
    sys.exit = aio_exit


# check if we have a Time handler.
try:
    Time
except:
    import time as Time


def rtclock():
    return int(Time.time() * 1_000)


class after:
    def __init__(self, oprom):
        self.oprom = oprom

    def then(self, fn, *argv, **kw):
        create_task(self.executor(fn, argv, kw))

    async def executor(self, fn, argv, kw):
        import embed

        mark = None
        value = undefined
        wit = cross.platform.window.iterator(self.oprom)
        while mark != undefined:
            value = mark
            await aio.sleep(0)
            mark = next(wit, undefined)
        del self.oprom
        if fn:
            fn(*argv, **kw)


#
import time as Time


class aioctx:
    def __init__(self, delta, coro):
        self.coro = coro
        self.tnext = Time.time() + delta
        self.tmout = 0


class _(list):
    current = None

    async def __aenter__(self):
        if self.__class__.current is None:
            self.__class__.current = aioctx(0, None)
        self.append(self.__class__.current)
        self.__class__.current = None
        if self[-1].coro is not None:
            pdb("__aenter__ awaiting", self[-1].coro)
            try:
                return await self[-1].coro
            except KeyboardInterrupt:
                aio.paused = None
                aio.loop.call_soon(aio.loop.stop)
                pdb("326: aio exit on KeyboardInterrupt")
                return await aio.sleep(0)
        else:
            print("__aenter__ no coro")
            self.__class__.current = None
            return self

    async def __aexit__(self, type, value, traceback):
        len(self) and self.pop()

    def __enter__(self):
        self.append(0)

    def __exit__(self, type, value, traceback):
        len(self) and self.pop()

    def __bool__(self):
        if self.__class__.current:
            return True
        if len(self) and self[-1]:
            return True
        return False

    def __call__(self, frametime):
        print("__call__", len(self), frametime)
        self.__class__.current = aioctx(frametime, None)
        return self

    def call(self, coro):
        print(".call", len(self), coro)
        if self.__class__.current is None:
            self.__class__.current = aioctx(0, coro)
        else:
            self.__class__.current.coro = coro
        # self.__class__.current.tmout = tmout
        return self


aio.ctx = _()
