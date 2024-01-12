import aio
import inspect
import sys
import threading as __threading__

sys.modules["__threading__"] = __threading__
from __threading__ import *

# mark not started but no error
aio.error = None

aio.paused = False
aio.fd = {}
aio.pstab = {}


def _shutdown():
    print(__file__, "_shutdown")


# https://docs.python.org/3/library/threading.html#threading.excepthook

# a green thread
# FIXME: fix wapy BUG 882 so target can be None too in preempt mode

# TODO: default granularity with https://docs.python.org/3/library/sys.html#sys.setswitchinterval


def excepthook(*argv, **kw):
    print("24 threading.excepthook", __file__, argv, kw)


class _dangling:
    @classmethod
    def copy(cls):
        # __threading__._MainThread()
        return set([])

    @classmethod
    def clear(cls):
        pass

    @classmethod
    def update(cls, saved):
        pass


class Local:
    pass


def local():
    return Local


class Lock:
    count = 0

    def __enter__(self):
        self.acquire()

    def __exit__(self, *tb):
        self.release()

    def acquire(self, blocking=True, timeout=-1):
        self.count += 1
        return True

    def release(self):
        self.count -= 1

    def locked(self):
        return self.count > 0


RLock = Lock


class Condition:
    def __init__(self, lock=None):
        self.lock = lock or Lock()

    def acquire(self, *args):
        return self.lock.acquire()

    def release(self):
        self.lock.release()

    def wait(self, timeout=None):
        raise RuntimeError("notify not supported")

    def wait_for(self, predicate, timeout=None):
        raise RuntimeError("wait not supported")


class Thread:
    def __init__(self, group=None, target=None, name=None, args=(), kwargs={}, *, daemon=None):
        # def __init__(self, group=None, target=None, name=None, args=(), kwargs={}):
        self.args = args
        self.kwargs = kwargs
        self.name = name
        self.slice = 0
        self.last = aio.rtclock()
        self.native_id = None
        self.ident = None
        if target:
            if hasattr(target, "run"):
                if name is None:
                    self.name = name or target.__class__.__name__
                self.run = target.run
            else:
                self.run = target

            if name is None:
                try:
                    self.name = "%s-%s" % (self.run.__name__, self.native_id)
                except:
                    pass
        else:
            target = self

        if self.name is None:
            self.name = "%s-%s" % (self.__class__.__name__, self.native_id)
        self.status = None

    async def wrap(self):
        for idle in self.run(*self.args, **self.kwargs):
            await aio.sleep(0)

    async def runner(self, coro):
        self.status = True
        try:
            # TODO: pass thread local context here
            async with aio.ctx(self.slice).call(coro):
                self.status = False
        except Exception as e:
            self.status = repr(e)
            sys.print_exception(e, sys.stderr)

    if __UPY__:

        def __iter__(self):
            if self.status is True:
                rtc = aio.rtclock()
                self.delta = (rtc - self.last) - self.slice
                if self.delta < 0:
                    self.delta = 0
                yield from aio.sleep_ms(self.slice - int(self.delta / 2))
                self.last = rtc

        __await__ = __iter__
    else:

        def __await__(self):
            if self.status is True:
                rtc = aio.rtclock()
                self.delta = (rtc - self.last) - self.slice
                if self.delta < 0:
                    self.delta = 0
                # no sleep_ms on cpy
                yield from aio.sleep_ms(float(self.slice - int(self.delta / 2)) / 1_000).__await__()
                # return aio.sleep( float(self.slice - int(self.delta / 2)) / 1_000 )
                self.last = rtc

    def rt(self, slice):
        self.slice = int(float(slice) * 1_000)
        return self

    def start(self):
        aio.pstab.setdefault(self.name, [])
        if self.run:
            if not inspect.iscoroutinefunction(self.run):
                self.status = True
                thr = self.wrap()
            else:
                coro = self.run(*self.args, **self.kwargs)
                pdb("177:", self.name, "starting", coro)
                thr = self.runner(coro)
            self.ident = self.native_id = id(self)
            aio.create_task(thr)
            aio.pstab[self.name].append(self)

        return self

    def join(self):
        embed.enable_irq()
        while self.is_alive():
            aio_suspend()
        embed.disable_irq()

    def __bool__(self):
        return self.is_alive() and not aio.exit

    def is_alive(self):
        return self.status is True


class Timer:
    def __init__(self, interval, function, args=None, kwargs=None):
        self.abort = False
        self.interval = interval
        self.thread = Thread(group=None, target=self.function, args=args, kwargs=kwargs)

    async def defer(self):
        await asyncio.sleep(self.interval)
        if not self.abort:
            self.thread.start()
        del self.abort, self.interval, self.thread

    def start(self):
        aio.create_task(self.defer())
        return self

    def cancel(self):
        self.abort = True


def service(srv, *argv, **kw):
    embed.log(f"starting green thread : {srv}")
    thr = aio.Thread(group=None, target=srv, args=argv, kwargs=kw).start()
    srv.__await__ = thr.__await__
    return aio.pstab.setdefault(srv, thr)


aio.task = service


def proc(srv):
    return aio.pstab.get(srv)


def _register_atexit(proc):
    print(__name__, "_register_atexit not implemented")


class Runnable:
    def __await__(self):
        yield from aio.pstab.get(self).__await__()


# replace with green threading
import sys

sys.modules["threading"] = sys.modules["aio.gthread"]
sys.modules["dummy_threading"] = sys.modules["aio.gthread"]
