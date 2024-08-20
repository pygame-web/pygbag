# builtins.__EMSCRIPTEN__
# builtins.__WASI__
# builtins.__ANDROID__   also defines __ANDROID_API__
# builtins.__UPY__ too can point to this module

import sys, os, builtins
import json

builtins.builtins = builtins

builtins.true = True
builtins.false = False


def breakpointhook(*argv, **kw):
    aio.paused = True


def shed_yield():
    # TODO: coroutine id as pid
    print("21", time_time() - aio.enter, aio.spent)
    return True


this = __import__(__name__)

# those  __dunder__ are usually the same used in C conventions.

# try:
#    __UPY__
# except:
#    if hasattr(sys.implementation, "_mpy"):
#        builtins.__UPY__ = this
#    else:
#        builtins.__UPY__ = None


# force use a fixed, tested version of uasyncio to avoid non-determinism
if __UPY__:
    sys.modules["sys"] = sys
    sys.modules["builtins"] = builtins

#    try:
#        from . import uasyncio as uasyncio
#
#        print("Warning : using WAPY uasyncio")
#    except Exception as e:
#        sys.print_exception(e)

else:
    sys.breakpointhook = breakpointhook

    # fallback to asyncio based implementation
    try:
        from . import uasyncio_cpy as uasyncio
    except:
        pdb("INFO: no uasyncio implementation found")
        uasyncio = aio

    sys.modules["uasyncio"] = uasyncio


# detect if cpython is really running on a emscripten browser

if hasattr(sys, "_emscripten_info"):
    is_browser = not sys._emscripten_info.runtime.startswith("Node.js")
    builtins.__EMSCRIPTEN__ = this
    try:
        from embed import *
        from platform import *
        from embed_emscripten import *
        from embed_browser import window, document, navigator
        from embed_browser import Audio, File, Object
        from embed_browser import fetch, console, prompt, alert, confirm

        # broad pyodide compat
        sys.modules["js"] = this  # instead of just sys.modules["embed_browser"]

        Object_type = type(Object())
    except Exception as e:
        sys.print_exception(e)
        pdb(__file__, ":47 no browser/emscripten modules yet", e)

    AnimatedFrames = None

    frames = []

    def requestAnimationFrame(fn):
        global AnimatedFrames
        if AnimatedFrames is None:
            print("using requestAnimationFrame asyncio emulation")
            import asyncio

            AnimatedFrames = []

            async def main():
                while not aio.exit:
                    if len(AnimatedFrames):
                        frames.append(AnimatedFrames.pop(0))
                    await asyncio.sleep(0)

            asyncio.run(main())

        AnimatedFrames.append(fn)

    # just a workaround until bridge support js "options" from **kw
    def ffi(arg=0xDEADBEEF, **kw):
        if arg == 0xDEADBEEF:
            return window.JSON.parse(json.dumps(kw))
        return window.JSON.parse(json.dumps(arg))

    async def jsiter(iterator):
        mark = None
        value = undefined
        while mark != undefined:
            value = mark
            await aio.sleep(0)
            mark = next(iterator, undefined)
        return value

    async def jsprom(prom):
        return await jsiter(platform.window.iterator(prom))

else:
    is_browser = False
    pdb("101: no emscripten browser interface")
    builtins.__EMSCRIPTEN__ = None


def init_platform(embed):
    # simulator won't run javascript for now
    if not hasattr(embed, "run_script"):
        pdb("186: no js engine")
        return False

    import json

    def js(code, delay=0):
        # keep a ref till next loop
        aio.protect.append(code)
        if not delay:
            result = embed.run_script(f"JSON.stringify({code})")
            if result is not None:
                return json.loads(result)
        elif delay < 0:
            embed.run_script(code)
        else:
            embed.run_script(code, int(delay))

    embed.js = js

    if __WASM__:
        import _thread

        try:
            _thread.start_new_thread(lambda: None, ())
        except RuntimeError:
            pdb("WARNING: that wasm build does not support threads")


# ========================================== DOM EVENTS ===============

# TODO: get that from browser
frametime = 1.0 / 60


if is_browser:
    # implement "js.new"

    def new(oclass, *argv):
        from embed_browser import Reflect, Array

        return Reflect.construct(oclass, Array(*argv))

    # dom events
    class EventTarget:
        clients = {}
        events = []

        def addEventListener(self, host, type, listener, options=None, useCapture=None):
            cli = self.__class__.clients.setdefault(type, [])
            cli.append(listener)

        def build(self, evt_name, jsondata):
            try:
                self.__class__.events.append([evt_name, json.loads(jsondata.strip('"'))])
            except Exception as e:
                sys.print_exception(e)
                print(jsondata)

        # def dispatchEvent
        async def rpc(self, method, *argv):
            import inspect

            # TODO resolve whole path
            if hasattr(__import__("__main__"), method):
                client = getattr(__import__("__main__"), method)
                is_coro = inspect.iscoroutinefunction(client)
                if is_coro:
                    await client(*argv)
                else:
                    client(*argv)
            else:
                print(f"RPC not found: {method}{argv}")

        # This is a green thread handling events from js -> python

        async def process(self):
            import inspect
            from types import SimpleNamespace

            # notify event queue we are ready to process
            window.python.is_ready = 1

            while not aio.exit:
                if len(self.events):
                    evtype, evdata = self.events.pop(0)
                    if evtype == "rpc":
                        print("rpc.id", evdata.pop("rpcid"))
                        await self.rpc(evdata.pop("call"), *evdata.pop("argv"))
                        continue

                    discarded = True
                    for client in self.clients.get(evtype, []):
                        is_coro = inspect.iscoroutinefunction(client)
                        discarded = False
                        sns = SimpleNamespace(**evdata)
                        if is_coro:
                            await client(sns)
                        else:
                            client(sns)

                    if discarded:
                        console.log(f"221: DISCARD : {evtype} {evdata}")

                await aio.sleep(0)

    EventTarget = EventTarget()
    add_event_listener = EventTarget.addEventListener

# =============================  PRELOADING      ==============================

preloading = -1
prelist = {}
ROOTDIR = f"/data/data/{sys.argv[0]}/assets"


def explore(root, verbose=False):
    global prelist, preloading

    import embed

    if preloading < 0:
        preloading = 0

    for current, dirnames, filenames in os.walk(root):
        for filename in filenames:
            if filename.endswith(".so"):
                preloading += 1
                src = f"{current}/{filename}"
                if verbose:
                    print(f"# 260: preload {src=}")
                embed.preload(src)


def fix_preload_table():
    global prelist, preloadedWasm, preloadedImages, preloadedAudios

    if embed.counter() < 0:
        pdb("212: asset manager not ready 0>", embed.counter())
        aio.defer(fix_preload_table, (), {}, delay=60)

    for (
        src,
        dst,
    ) in prelist.items():
        ext = dst.rsplit(".", 1)[-1]
        if ext in preloadedImages:
            ptype = "preloadedImages"
        elif ext in preloadedAudios:
            ptype = "preloadedAudios"
        elif ext == "so":
            ptype = "preloadedWasm"

        src = f"{ptype}[{repr(src)}]"
        dst = f"{ptype}[{repr(dst)}]"
        swap = f"({src}={dst}) && delete {dst}"
        embed.js(swap, -1)
        # print(swap)


def run_main(PyConfig, loaderhome=None, loadermain="main.py"):
    global ROOTDIR
    global preloadedWasm, preloadedImages, preloadedAudios

    if loaderhome:
        pdb(f"241: appdir mapped to {loaderhome} by loader")
        ROOTDIR = str(loaderhome)
    #
    #    # simulator won't run javascript for now
    #    if not hasattr(embed, "run_script"):
    #        pdb("246: no js engine")
    #        return False
    #
    #    # do not do stuff if not called properly from our js loader.
    #    if PyConfig.executable is None:
    #        # running in sim
    #        pdb("252: running in simulator")
    #        return False
    #
    #    #sys.executable = PyConfig.executable or "python"

    preloadedWasm = "so"
    preloadedImages = "png jpeg jpg gif"
    preloadedAudios = "wav ogg mp4"

    def preload_apk(p=None):
        global preloading, prelist, ROOTDIR
        global explore, preloadedWasm, preloadedImages, preloadedAudios
        ROOTDIR = p or ROOTDIR
        if os.path.isdir(ROOTDIR):
            os.chdir(ROOTDIR)
        else:
            pdb(f"cannot chdir to {ROOTDIR=}")
            return

        ROOTDIR = os.getcwd()
        LSRC = len(ROOTDIR) + 1
        preloading = -1
        prelist = {}

        sys.path.insert(0, ROOTDIR)

        explore(ROOTDIR)

        if preloading < 0:
            pdb(f"{ROOTDIR=}")
            pdb(f"{os.getcwd()=}")

        print(f"309: assets found :", preloading)
        if not preloading:
            embed.run()

        return True

    import aio

    if PyConfig.interactive:
        # import aio.clock
        # aio.clock.start(x=80)

        # org.python REPL no preload !
        preload = sys.argv[0] != "org.python"
    else:
        # org.python script
        preload = True

    pdb(f"274: preload status {preload}")

    if preload and preload_apk():

        def fix_preload_table_apk():
            global fix_preload_table, ROOTDIR
            fix_preload_table()
            os.chdir(ROOTDIR)
            sys.path.insert(0, ROOTDIR)
            if loadermain:
                if os.path.isfile("main.py"):
                    print(f"315: running {ROOTDIR}/{loadermain} for {sys.argv[0]} (deferred)")
                    aio.defer(execfile, [f"{ROOTDIR}/{loadermain}"], {})
                else:
                    pdb(f"no {loadermain} found for {sys.argv[0]} in {ROOTDIR}")
                # aio.defer(embed.prompt, (), {}, delay=2000)

    # C should unlock aio loop when preload count reach 0.

    else:

        def fix_preload_table_apk():
            global fix_preload_table_apk, ROOTDIR
            pdb("no assets preloaded")
            os.chdir(ROOTDIR)
            # aio.defer(embed.prompt, (), {})

        # unlock embed looper because no preloading
        embed.run()

    aio.defer(fix_preload_table_apk, (), {}, delay=1000)

    if not aio.started:
        aio.started = True
        aio.create_task(EventTarget.process())
    else:
        print("364: EventTarget delayed by loader")


# ===============================================================================================
# platform


def rcp(source, destination):
    import urllib
    import urllib.request

    filename = Path(destination)
    filename.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(source_url, str(filename))
