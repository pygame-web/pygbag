import sys
import asyncio

asyncrun = asyncio.run

from .__init__ import VERSION

print(f" *pygbag {VERSION}*")

from pathlib import Path


async def import_site(sourcefile=None, simulator=False, async_input=None, async_pkg=None):
    import sys
    import os
    from pathlib import Path

    if ("--sim" not in sys.argv) and ("--piny" not in sys.argv) and not simulator:
        from .app import main_run, set_args

        app_folder, mainscript = set_args(sys.argv[-1])
        # run pygbag build/server
        await main_run(app_folder, mainscript)
        return True

    # or run as a native simulator

    mod_dir = Path(__file__).parent
    support = mod_dir / "support"
    cur_dir = os.getcwd()
    print(
        f"""
            - single thread no-os wasm simulator -

    module directory : {mod_dir}
    platform support : {support}
    {sys.argv=}
    {sourcefile=}
    {cur_dir=}

"""
    )

    import sys, os, builtins

    # sys.path.append(str(support / "cross"))

    # need them earlier than aio

    def pdb(*argv):
        print(*argv, file=sys.__stderr__)

    builtins.pdb = pdb

    def print_exception(e, out=sys.stderr, **kw):
        kw["file"] = out
        traceback.print_exc(**kw)

    # abstract placeholder for missing host objects
    class NoOp(object):
        def __init__(self, *argv, **env):
            self.__descr = " ".join(map(str, argv))
            self.__lastc = "__init__"

        def __call__(self, *argv, **env):
            print(self, "call:", argv, env)
            return None

        def __nop(self, *argv, **env):
            print(f"{self}.{self.__lastc}(*{argv}, **{env})")
            return self

        def __nonzero__(self):
            return 0

        def __nop__(self, other):
            return 0

        __add__ = __iadd__ = __sub__ = __isub__ = __mul__ = __imul__ = __div__ = __idiv__ = __nop__

        def __getattr__(self, attr):
            self.__lastc = attr
            return self.__nop

        def iteritems(self):
            print(self, "iterator")
            return []

        def __del__(self):
            pass

        def __repr__(self):
            return "\nNoOp: %s" % self.__descr

        __str__ = __repr__

    class window_navigator:
        userAgent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"

    # fake host document.window
    import platform as fakehost

    def truc(*argv, **kw):
        print("truc", argv, kw)

    def prompt():
        # FIXME for js style console should be
        # CSI(f"{TTY.LINES+TTY.CONSOLE};1H{prompt}")
        print("\r>X> ", end="")

    fakehost.is_browser = False
    fakehost.async_input = async_input
    fakehost.window = NoOp("platform.window")
    fakehost.window.console = NoOp("platform.window.console")
    fakehost.window.console.log = print
    fakehost.window.get_terminal_console = truc
    fakehost.window.RAW_MODE = 0
    fakehost.window.navigator = window_navigator
    fakehost.readline = lambda: ""
    fakehost.prompt = prompt

    def set_raw_mode(mode):
        import platform as fakehost

        fakehost.window.RAW_MODE = mode

    fakehost.window.set_raw_mode = set_raw_mode
    fakehost.window.set_raw_mode(0)

    import aio.filelike

    fakehost.fopen = aio.filelike.fopen

    # cannot fake a wasm cpu but fake the platform AND the module

    sys.platform = "emscripten"

    class fake_EventTarget:
        clients = {}
        events = []

        async def process(self): ...

    def patch_platform_system():
        return "Emscripten"

    # et = EventTarget()
    class __EMSCRIPTEN__(object):
        EventTarget = fake_EventTarget()
        ticks = 0

        def __init__(self):
            import platform

            platform.system = patch_platform_system
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
        def system(cls):
            return "Linux"

        @classmethod
        def no_op(cls, *argv, **kw): ...

        run = no_op

        set_ps1 = no_op

        set_ps2 = no_op

        prompt = no_op

        is_browser = False

        js = pdb
        run_script = pdb

    __EMSCRIPTEN__ = __EMSCRIPTEN__()

    sys.modules["__EMSCRIPTEN__"] = __EMSCRIPTEN__
    sys.modules["embed"] = __EMSCRIPTEN__

    print(" =============== pythonrc =================")
    with open(support / "cpythonrc.py", "r") as file:
        exec(file.read(), globals(), globals())

    print(" =============== /pythonrc =================")

    import zipfile
    import aio.toplevel
    import ast
    from pathlib import Path

    class TopLevel_async_handler(aio.toplevel.AsyncInteractiveConsole):
        HTML_MARK = '"' * 3 + " # BEGIN -->"

        #        @classmethod
        #        async def async_imports(cls, callback, *wanted, **kw):
        #            ...

        @classmethod
        def list_imports(cls, code=None, file=None, hint=""):
            return []

        def eval(self, source):
            for count, line in enumerate(source.split("\n")):
                if not count:
                    if line.startswith("<"):
                        self.buffer.append(f"#{line}")
                        continue
                self.buffer.append(line)

            if count:
                self.line = None
                self.buffer.insert(0, "#")
            print(f"178: {count} lines queued for async eval")

        async def async_get_pkg(cls, want, ex, resume):
            print(
                """
224:TODO: PEP723
    async def async_get_pkg(cls, want, ex, resume)
"""
            )

    # start async top level machinery and add a console.
    await TopLevel_async_handler.start_toplevel(platform.shell, console=True)

    # ns = vars(__import__(__name__))

    # ns["TopLevel_async_handler"] = TopLevel_async_handler

    aio.toplevel.handler = TopLevel_async_handler

    sourcefile = sourcefile or str(sys.argv[-1])

    __import__("__main__").__file__ = sourcefile

    await async_pkg

    if "--piny" in sys.argv:
        from . import mutator

        mutator.transform_file(sourcefile, f"{sourcefile[:-3]}.pn")

    else:
        import aio.clock

        # asyncio.create_task( aio.clock.loop() )
        aio.clock.start(x=80)

        print(__name__, "sim repl ready for", sourcefile)

        if sys.path[0] != cur_dir:
            sys.path.insert(0, cur_dir)

        await shell.runpy(sourcefile)
        shell.interactive()

        # if you don't reach that step
        # your main.py has an infinite sync loop somewhere !
        print(f"{platform.is_browser=}, sim is running")

        while not aio.exit:
            await aio.sleep(0.016)
        print(__name__, "sim terminating")


if __name__ == "__main__":
    asyncio.run(import_site())


#
