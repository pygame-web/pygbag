import asyncio

asyncrun = asyncio.run

import sys
from .__init__ import __version__

print(f" *pygbag {__version__}*")

from pathlib import Path
from .app import main_run, set_args


async def import_site():
    import sys
    from pathlib import Path

    app_folder, mainscript = set_args(sys.argv[-1])

    if ("--sim" not in sys.argv) and ("--piny" not in sys.argv):
        # run pygbag build/server
        await main_run(app_folder, mainscript)
        return True

    # or run as a native simulator

    mod_dir = Path(__file__).parent
    support = mod_dir / "support"

    print(" - simulator -", mod_dir, support)

    import sys, os, builtins

    sys.path.insert(0, str(support / "cross"))

    # need them earlier than aio

    def pdb(*argv):
        print(*argv, file=sys.__stderr__)

    builtins.pdb = pdb

    def print_exception(e, out=sys.stderr, **kw):
        kw["file"] = out
        traceback.print_exc(**kw)

    # cannot fake a cpu __WASM__ will be False

    # but fake the platform AND the module
    sys.platform = "emscripten"

    class fake_EventTarget:
        clients = {}
        events = []

        async def process(self):
            ...

    # et = EventTarget()
    class __EMSCRIPTEN__(object):
        EventTarget = fake_EventTarget()
        ticks = 0

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
        def system(cls):
            return "Linux"

        @classmethod
        def no_op(cls, *argv, **kw):
            ...

        run = no_op

        set_ps1 = no_op

        prompt = no_op

        is_browser = False

        js = pdb
        run_script = pdb

    __EMSCRIPTEN__ = __EMSCRIPTEN__()

    sys.modules["__EMSCRIPTEN__"] = __EMSCRIPTEN__
    sys.modules["embed"] = __EMSCRIPTEN__

    with open(support / "pythonrc.py", "r") as file:
        exec(file.read(), globals(), globals())

    import zipfile
    import aio.toplevel
    import ast
    from pathlib import Path

    class TopLevel_async_handler(aio.toplevel.AsyncInteractiveConsole):
        HTML_MARK = '""" # BEGIN -->'

        @classmethod
        async def async_repos(cls):
            abitag = f"cp{sys.version_info.major}{sys.version_info.minor}"
            print(f"{abitag=}")

        @classmethod
        async def async_imports(cls, callback, *wanted, **kw):
            ...

        @classmethod
        def list_imports(cls, code=None, file=None):
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

    # start async top level machinery and add a console.
    await TopLevel_async_handler.start_toplevel(platform.shell, console=True)
    ns = vars(__import__(__name__))

    ns["TopLevel_async_handler"] = TopLevel_async_handler

    sourcefile = sys.argv[-1]

    __import__(__name__).__file__ = str(sourcefile)

    if "--piny" in sys.argv:
        from . import mutator

        mutator.transform_file(sourcefile, f"{sourcefile[:-3]}.pn")

    else:
        import aio.clock

        # asyncio.create_task( aio.clock.loop() )
        aio.clock.start(x=80)

        print(__name__, "sim repl ready for", __file__)

        await shell.runpy(__file__)
        shell.interactive()

        # if you don't reach that step
        # your main.py has an infinite sync loop somewhere !
        print(f"{platform.is_browser=}, sim ready, press enter to start")

        while not aio.exit:
            await aio.sleep(0.016)
        print(__name__, "sim terminated")


if __name__ == "__main__":
    asyncio.run(import_site())


#
