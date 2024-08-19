#!pythonrc.py

import os, sys, json, builtins


# to be able to access aio.cross.simulator
import aio
import aio.cross

# placeholder until v1.0
sys.modules["pygbag"] = aio

import time
import inspect
from pathlib import Path
import json


PYCONFIG_PKG_INDEXES_DEV = ["http://localhost:<port>/archives/repo/"]
# normal index or PYGPY env is handled after env conversion around line 255

# the sim does not ospreload assets and cannot access currentline
# unless using https://github.com/pmp-p/aioprompt/blob/master/aioprompt/__init__.py
# or a thread

if not defined("undefined"):

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

    define("undefined", sentinel())
    del sentinel

    define("false", False)
    define("true", True)

    # fix const without writing const in that .py because of faulty micropython parser.
    exec("__import__('builtins').const = lambda x:x", globals(), globals())


def overloaded(i, *attrs):
    for attr in attrs:
        if attr in vars(i.__class__):
            if attr in vars(i):
                return True
    return False


builtins.overloaded = overloaded


def DBG(*argv):
    if PyConfig.dev_mode > 0:
        print(*argv)


try:
    # mpy already has execfile
    execfile
except:

    def execfile(filename):
        imports = []

        # this buggy parser is for implementations that do not have ast module.
        # and should not be used with cpython
        with __import__("tokenize").open(str(filename)) as f:
            __prepro = []
            myglobs = ["setup", "loop", "main"]
            tmpl = []

            for l in f.readlines():
                testline = l.split("#")[0].strip(" \r\n,\t")

                if testline.startswith("global ") and (
                    testline.endswith(" setup") or testline.endswith(" loop") or testline.endswith(" main")
                ):
                    tmpl.append([len(__prepro), l.find("g")])
                    __prepro.append("#globals")
                    continue

                elif testline.startswith("import "):
                    testline = testline.replace("import ", "").strip()
                    for elem in map(str.strip, testline.split(",")):
                        elem = elem.split(" as ")[0]
                        if not elem in imports:
                            imports.append(elem)

                elif testline.startswith("from "):
                    testline = testline.replace("from ", "").strip()
                    elem = testline.split(" import ")[0].strip()
                    if not elem in imports:
                        imports.append(elem)

                __prepro.append(l)

                if l[0] in ("""\n\r\t'" """):
                    continue

                if not l.find("=") > 0:
                    continue

                l = l.strip()

                if l.startswith("def "):
                    continue
                if l.startswith("class "):
                    continue

                # maybe found a global assign
                varname = l.split("=", 1)[0].strip(" []()")

                for varname in map(str.strip, varname.split(",")):
                    if varname.find(" ") > 0:
                        continue

                    # it's a comment on an assign !
                    if varname.find("#") >= 0:
                        continue

                    # skip attr assign
                    if varname.find(".") > 0:
                        continue

                    # not a tuple assign
                    if varname.find("(") > 0:
                        continue

                    # not a list assign
                    if varname.find("[") > 0:
                        continue

                    # TODO handle (a,)=(0,) case types

                    if not varname in myglobs:
                        myglobs.append(varname)

            myglob = f"global {', '.join(myglobs)}\n"

            # for helping fixing freshly ported code
            if aio.cross.simulator:
                print(myglob)

            for mark, indent in tmpl:
                __prepro[mark] = " " * indent + myglob

            def dump_code():
                nonlocal __prepro
                print()
                print("_" * 70)
                for i, l in enumerate(__prepro):
                    print(str(i).zfill(5), l, end="")
                print("_" * 70)
                print()

            # if aio.cross.simulator:
            #    dump_code()

            # use of globals() is only valid in __main__ scope
            # we really want the module __main__ dict here
            # whereever from we are called.
            __main__ = __import__("__main__")
            __main__dict = vars(__main__)
            __main__dict["__file__"] = str(filename)
            try:
                code = compile("".join(__prepro), str(filename), "exec")
            except SyntaxError as e:
                # if not aio.cross.simulator:
                dump_code()
                sys.print_exception(e)
                code = None

            if code:
                print(f"180: imports: {imports}")
                exec(code, __main__dict, __main__dict)

        return __import__("__main__")

    define("execfile", execfile)


try:
    PyConfig
except NameError:
    PyConfig = None

# in simulator there's no PyConfig
# would need to get one from live cpython
if PyConfig is None:
    # TODO: build a pyconfig extracted from C here
    PyConfig = {}
    PyConfig["dev_mode"] = 1
    PyConfig["run_filename"] = "main.py"

    # TODO: use location of python js module.
    if __UPY__:
        PyConfig["executable"] = "upy"
    else:
        PyConfig["executable"] = sys.executable

    PyConfig["interactive"] = 1
    print(" - running in wasm simulator - ")
    aio.cross.simulator = True
else:

    # for the various emulations/tools provided
    sys.path.append("/data/data/org.python/assets")

    PyConfig["pkg_repolist"] = []

    aio.cross.simulator = False
    sys.argv.clear()
    sys.argv.extend(PyConfig.pop("argv", []))

    sys.executable = PyConfig["executable"]
    sys.orig_argv.clear()

    sys.orig_argv.append(sys.executable)

    # env is passed in orig_argv ?ENV1=V1&ENV2=V2#
    for arg in PyConfig["orig_argv"]:
        if "=" not in arg:
            sys.orig_argv.append(arg)
        else:
            k, v = arg.split("=", 1)
            os.environ[k] = v

    home = f"/home/{os.environ.get('USER','web_user')}"
    if home != "/home/web_user":
        # in case user name is not fs compatible
        try:
            os.rename("/home/web_user", home)
        except:
            home = "/home/web_user"

    os.environ["HOME"] = home
    os.environ["APPDATA"] = home
    del home

# now in pep0723
# PYCONFIG_PKG_INDEXES = [
#    os.environ.get('PYGPY', "https://pygame-web.github.io/archives/repo/"),
# ]

PyConfig["imports_ready"] = False
PyConfig["pygbag"] = 0

PyConfig.setdefault("user_site_directory", 0)


class shell:
    # pending async tasks
    coro = []

    # async top level instance compiler/runner
    runner = None
    is_interactive = None

    if aio.cross.simulator or not len(sys.argv):
        ROOT = os.getcwd()
        HOME = os.getcwd()
    else:
        ROOT = f"/data/data/{sys.argv[0]}"
        HOME = f"/data/data/{sys.argv[0]}/assets"

    pgzrunning = None

    @classmethod
    def mktemp(cls, suffix=""):
        return aio.filelike.mktemp(suffix)

    @classmethod
    def cat(cls, *argv):
        """dump binary file content"""
        for fn in map(str, argv):
            with open(fn, "rb") as out:
                print(out.read())

    @classmethod
    def more(cls, *argv):
        """dump text file content"""
        for fn in map(str, argv):
            with open(fn, "r") as out:
                print(out.read())

    @classmethod
    def pp(cls, *argv):
        """pretty print objects via json"""
        for obj in argv:
            obj = eval(obj, vars(__import__("__main__")))
            if isinstance(obj, platform.Object_type):
                obj = json.loads(platform.window.JSON.stringify(obj))
            yield json.dumps(obj, sort_keys=True, indent=4)

    @classmethod
    def ls(cls, *argv):
        """list directory content"""
        if not len(argv):
            argv = ["."]
        for arg in map(str, argv):
            for out in sorted(os.listdir(arg)):
                print(out)

    @classmethod
    def reset(cls, *argv, **kw):
        ESC("c")

    @classmethod
    def pg_init(cls):
        import pygame

        screen = None
        if pygame.display.get_init():
            screen = pygame.display.get_surface()
        else:
            pygame.init()
            pygame.display.get_init()

        if not screen:
            screen = pygame.display.set_mode([cls.screen_width, cls.screen_height])
        return screen

    @classmethod
    def find(cls, *argv):
        from pathlib import Path

        if not len(argv):
            argv = [os.getcwd()]
        for root in argv:
            root = Path(root)
            for current, dirnames, filenames in os.walk(root):
                dirname = root.joinpath(Path(current))
                for file in filenames:
                    yield str(dirname / file)

    @classmethod
    def grep(cls, match, *argv):
        for arg in argv:
            if arg.find(match) > 0:
                yield arg

    @classmethod
    def clear(cls, *argv, **kw):
        """clear terminal screen"""
        import pygame

        screen = cls.pg_init()
        screen.fill((0, 0, 0))
        pygame.display.update()

    @classmethod
    def display(cls, *argv, **kw):
        """show images, or last repl pygame surface from _"""
        import pygame

        if not len(argv):
            surf = _
        else:
            arg = argv[-1]
            ext = arg.lower()
            if ext.endswith(".b64"):
                import base64

                ext = arg[:-4]
                with open(arg, "rb") as infile:
                    arg = arg[:-4]
                    with open(arg, "wb") as outfile:
                        base64.decode(infile, outfile)

            if ext.endswith(".six"):
                cls.more(arg)
                return

            if ext.endswith(".bmp"):
                surf = pygame.image.load_basic(arg)
            else:
                surf = pygame.image.load(arg)

        screen = cls.pg_init()
        screen.blit(surf, (1, 1))
        pygame.display.update()

    @classmethod
    def mkdir(cls, *argv):
        exist_ok = "-p" in argv
        for arg in map(str, argv):
            if arg == "-p":
                continue
            os.makedirs(arg, exist_ok=exist_ok)

    @classmethod
    def rx(cls, *argv, **env):
        for arg in map(str, argv):
            if arg.startswith("-"):
                continue
            platform.window.MM.download(arg)
            yield f"file {arg} sent"
        return True

    @classmethod
    async def async_pgzrun(cls, *argv, **env):
        await __import__("pgzero").runner.PGZeroGame(__import__("__main__")).async_run()

    @classmethod
    def pgzrun(cls, *argv, **env):
        import pgzero
        import pgzero.runner

        pgzt = pgzero.runner.PGZeroGame(__import__("__main__")).async_run()
        asyncio.create_task(pgzt)
        return True

    @classmethod
    def wget(cls, *argv, **env):
        import urllib.request

        filename = None
        for arg in map(str, argv):
            if arg.startswith("-O"):
                filename = arg[2:].strip()
                yield f'saving to "{filename}"'
                break

        for arg in map(str, argv):
            if arg.startswith("-O"):
                continue
            fn = filename or str(argv[0]).rsplit("/")[-1]
            try:
                filename, _ = urllib.request.urlretrieve(str(arg), filename=fn)
            except Exception as e:
                yield e

        return True

    @classmethod
    def env(cls, *argv):
        for k in os.environ:
            yield f"{k}={os.environ[k]}"
        return True

    @classmethod
    def pwd(cls, *argv):
        print(os.getcwd())

    # only work if pkg name == dist name
    @classmethod
    async def pip(cls, *argv):
        for arg in argv:
            if arg == "install":
                continue
            import aio.pep0723

            # yield f"attempting to install {arg}"
            await aio.pep0723.pip_install(arg)

    @classmethod
    def cd(cls, *argv):
        if len(argv):
            os.chdir(argv[-1])
        else:
            os.chdir(cls.HOME)
        print("[ ", os.getcwd(), " ]")

    @classmethod
    def sha256sum(cls, *argv):
        import hashlib

        for arg in map(str, argv):
            sha256_hash = hashlib.sha256()
            with open(arg, "rb") as f:
                # Read and update hash string value in blocks of 4K
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
                hx = sha256_hash.hexdigest()
                yield f"{hx}  {arg}"

    @classmethod
    def spawn(cls, cmd, *argv, **env):
        # TODO extract env from __main__ snapshot
        if cmd.endswith(".py"):
            if cls.pgzrunning:
                print("a program is already running, using 'stop' cmd before retrying")
                cls.stop()
                cls.pgzrunning = None
                args = [cmd]
                args.extend(argv)
                aio.defer(cls.spawn, args, env, delay=500)
            else:
                execfile(cmd)
            return True
        return False

    @classmethod
    def umask(cls, *argv, **kw):
        yield oct(os.umask(0))
        return True

    @classmethod
    def chmod(cls, *argv, **kw):
        def _current_umask() -> int:
            mask = os.umask(0)
            os.umask(mask)
            return mask

        for arg in argv:
            if arg.startswith("-"):
                continue
            mode = 0o777 & ~_current_umask() | 0o111
            print(f"{mode=}")
            os.chmod(arg, mode)

    @classmethod
    def unzip(cls, *argv, **env):
        import zipfile

        for zip in argv:
            with zipfile.ZipFile(zip, "r") as zip_ref:
                zip_ref.printdir()
                zip_ref.extractall(os.getcwd())

    @classmethod
    def install(cls, *argv, **env):
        import aio.pep0723

        for pkg_file in argv:
            try:
                aio.pep0723.install(pkg_file)
                yield f"{pkg_file} installed"
            except (IOError, zipfile.BadZipFile):
                pdb("397: invalid package", pkg_file)
            except Exception as ex:
                sys.print_exception(ex)

    @classmethod
    def dll(cls, *argv):
        cdll = __import__("ctypes").CDLL(None)
        sym = getattr(cdll, argv[0])
        print("symbol :", sym)
        print(sym(*argv[1:]))
        return True

    @classmethod
    def strace(cls, *argv, **env):
        import aio.tracer

        print("497: trace on")
        sys.settrace(aio.tracer.calls)
        return True

    @classmethod
    def mute(cls, *argv, **env):
        try:
            pygame.mixer.music.unload()
            yield "music muted"
        except:
            pass

    @classmethod
    def debug(cls, *argv, **env):
        try:
            platform.window.debug()
            yield f"debug mode : on, canvas divider {window.python.config.gui_debug}"
        except:
            pass

    @classmethod
    def help(cls, *objs):
        print(
            """
pygbag shell help
________________________
"""
        )
        if not len(objs):
            objs = [cls]
        for obj in objs:
            for cmd, item in vars(obj).items():
                if isinstance(item, str):
                    continue
                if cmd[0] != "_" and item.__doc__:
                    print(cmd, ":", item.__doc__)
                    print()

    # TODO: use run interactive c-api to run this one.
    @classmethod
    def run(cls, *argv, **env):
        __main__ = __import__("__main__")
        __main__dict = vars(__main__)

        builtins._ = undefined
        cmd = " ".join(argv)

        try:
            time_start = time.time()
            code = compile("builtins._ =" + cmd, "<stdin>", "exec")
            exec(code, __main__dict, __main__dict)
            if builtins._ is undefined:
                return True
            if aio.iscoroutine(_):

                async def run(coro):
                    print(f"async[{cmd}] :", await coro)
                    print(f"time[{cmd}] : {time.time() - time_start:.6f}")

                aio.create_task(run(_), name=cmd)
            else:
                print(builtins._)
                print(f"time[{cmd}] : {time.time() - time_start:.6f}")
                return True
        except SyntaxError as e:
            # try run a file or cmd
            return cls.parse_sync(argv, env)
        return False

    time = run

    @classmethod
    def ps(cls, *argv, **env):
        for t in aio.all_tasks():
            print(t)
        return True

    @classmethod
    def stop(cls, *argv, **env):
        aio.exit = True
        # pgzrun will reset to None next exec
        if not cls.pgzrunning:
            # pgzrun does its own cleanup call
            aio.defer(aio.recycle.cleanup, (), {}, delay=500)
            aio.defer(platform.prompt, (), {}, delay=800)

    @classmethod
    def uptime(cls, *argv, **env):
        import asyncio, platform

        if not aio.perf_index:

            async def perf_index():
                ft = [0.00001] * 60 * 10
                while not aio.exit:
                    ft.pop(0)
                    ft.append(aio.spent / 0.016666666666666666)
                    if not (aio.ticks % 60):
                        avg = sum(ft) / len(ft)
                        aio.load_avg = "{:.4f}".format(avg)
                        aio.load_min = "{:.4f}".format(min(ft))
                        aio.load_max = "{:.4f}".format(max(ft))
                    await asyncio.sleep(0)

            aio.perf_index = perf_index()
            aio.create_task(aio.perf_index)

    @classmethod
    async def preload_code(cls, code, callback=None, loaderhome=".", hint=""):
        # get a relevant list of modules likely to be imported
        PyConfig.dev_mode = 1
        DBG(f"655: preload_code({len(code)=} {hint=} {loaderhome=})")

        if loaderhome != ".":
            os.chdir(loaderhome)
        if not loaderhome in sys.path:
            sys.path.append(loaderhome)

        import aio
        import aio.pep0723
        from aio.pep0723 import Config

        if not aio.cross.simulator:
            # env path is set by pep0723
            sconf = __import__("sysconfig").get_paths()
            env = Path(sconf["purelib"])

            if not len(Config.repos):
                await aio.pep0723.async_repos()

                # TODO switch to METADATA:Requires-Dist
                #   see https://github.com/pygame-web/pygbag/issues/156

                for cdn in Config.PKG_INDEXES:
                    async with platform.fopen(Path(cdn) / Config.REPO_DATA) as source:
                        Config.repos.append(json.loads(source.read()))

                DBG("650: FIXME (this is pyodide maintened stuff, use (auto)PEP723 asap)")
                print("651: referenced packages :", len(Config.repos[0]["packages"]))

            DBG(f"654: aio.pep0723.check_list {aio.pep0723.env=}")
            deps = await aio.pep0723.check_list(code)

            DBG(f"656: aio.pep0723.pip_install {deps=}")

            # auto import plumbing to avoid rely too much on import error
            maybe_wanted = list(TopLevel_async_handler.list_imports(code, file=None, hint=hint))
            DBG(f"635: {maybe_wanted=} known failed {aio.pep0723.hint_failed=}")

            # FIXME use an hybrid wheel
            if "pyodide" in aio.pep0723.hint_failed:

                for no_need in ("_zengl", "pyodide", "beautifulsoup4"):
                    if no_need in maybe_wanted:
                        maybe_wanted.remove(no_need)
                # force
                maybe_wanted.append("beautifulsoup4")

            for dep in maybe_wanted:
                if not dep in deps:
                    deps.append(dep)

            for dep in deps:
                await aio.pep0723.pip_install(dep)

            aio.pep0723.do_patches()

        PyConfig.imports_ready = True
        return True

    @classmethod
    def interactive(cls, prompt=False):
        if prompt:
            aio.toplevel.handler.mute_state = False
            aio.toplevel.handler.muted = False

        if cls.is_interactive:
            return
        # if you don't reach that step
        # your main.py has an infinite sync loop somewhere !
        DBG("651: starting EventTarget in a few seconds")

        print()
        aio.toplevel.handler.instance.banner()

        aio.create_task(platform.EventTarget.process())
        cls.is_interactive = True

        if not shell.pgzrunning:
            # __main__@stdin has no __file__
            if hasattr(__import__("__main__"), "__file__"):
                del __import__("__main__").__file__
            if prompt:
                cls.runner.prompt()
        else:
            shell.pgzrun()

    @classmethod
    async def runpy(cls, main, *args, **kw):
        def check_code(file_name):
            nonlocal code
            maybe_sync = False
            has_pygame = False
            with open(file_name, "r") as code_file:
                code = code_file.read()
                code = code.rsplit(aio.toplevel.handler.HTML_MARK, 1)[0]

                # do not check site/final/packed code
                # preload code must be fully async and no pgzero based
                if aio.toplevel.handler.muted:
                    return True

                if code[0:320].find("#!pgzrun") >= 0:
                    shell.pgzrunning = True

                if code.find("asyncio.run") < 0:
                    DBG("606: possibly synchronous code found")
                    maybe_sync = True

                has_pygame = code.find("display.flip(") > 0 or code.find("display.update(") > 0

                if maybe_sync and has_pygame:
                    DBG("694: possibly synchronous+pygame code found")
                    return False
            return True

        code = ""
        shell.pgzrunning = None

        DBG(f"690: : runpy({main=})")
        # REMOVE THAT IT SHOULD BE DONE IN SIM ANALYSER AND HANDLED PROPERLY
        if not check_code(main):
            for base in ("pygame", "pg"):
                for func in ("flip", "update"):
                    block = f"{base}.display.{func}()"
                    code = code.replace(block, f"{block};await asyncio.sleep(0)")

        # fix cwd to match a run of main.py from its folder
        realpath = str(main)
        if realpath[0] not in "./":
            realpath = str(Path.cwd() / main)
        __import__("__main__").__file__ = str(realpath)
        cls.HOME = Path(realpath).parent
        os.chdir(cls.HOME)

        # TODO: should be $0 / sys.argv[0] from there and while running
        kw.setdefault("hint", main)
        # get requirements
        await cls.preload_code(code, **kw)

        # get an async executor to catch import errors
        if aio.toplevel.handler.instance:
            DBG("715: starting shell")
            aio.toplevel.handler.instance.start_console(shell)
        else:
            pdb("718: no async handler loader, starting a default async console")
            shell.debug()
            await aio.toplevel.handler.start_toplevel(platform.shell, console=True)

        # TODO: check if that thing really works
        if shell.pgzrunning:
            DBG("728 : pygame zero detected")
            __main__ = __import__("__main__")
            sys._pgzrun = True
            sys.modules["pgzrun"] = type(__main__)("pgzrun")
            import pgzrun

            pgzrun.go = lambda: None
            cb = kw.pop("callback", None)
            await aio.toplevel.handler.async_imports(cb, "pygame.base", "pgzero", "pyfxr", **kw)
            import pgzero
            import pgzero.runner

            pgzero.runner.prepare_mod(__main__)

        # finally eval async
        aio.toplevel.handler.instance.eval(code)

        # go back to prompt
        if not aio.toplevel.handler.muted:
            print("going interactive")
            DBG("746: TODO detect input/print to select repl debug")
            cls.interactive()

        return code

    @classmethod
    async def source(cls, main, *args, **kw):
        # this is not interactive turn off prompting
        aio.toplevel.handler.muted = True
        try:
            return await cls.runpy(main, *args, **kw)
        finally:
            aio.toplevel.handler.muted = aio.toplevel.handler.mute_state

    @classmethod
    def parse_sync(shell, line, **env):
        catch = True
        for cmd in line.strip().split(";"):
            cmd = cmd.strip()
            if cmd.find(" ") > 0:
                cmd, args = cmd.split(" ", 1)
                args = args.split(" ")
            else:
                args = ()

            if hasattr(shell, cmd):
                fn = getattr(shell, cmd)

                try:
                    if inspect.isgeneratorfunction(fn):
                        for _ in fn(*args):
                            print(_)
                    elif inspect.iscoroutinefunction(fn):
                        aio.create_task(fn(*args))
                    elif inspect.isasyncgenfunction(fn):
                        print("asyncgen N/I")
                    elif inspect.isawaitable(fn):
                        print("awaitable N/I")
                    else:
                        fn(*args)

                except Exception as cmderror:
                    print(cmderror, file=sys.stderr)
            elif cmd.endswith(".py"):
                shell.coro.append(shell.source(cmd, *args, **env))
            else:
                catch = undefined
        return catch

    @classmethod
    async def exec(cls, sub, **env):
        if inspect.isgenerator(sub):
            for _ in sub:
                print(_)
            return
        elif inspect.isgeneratorfunction(sub):
            for _ in sub(**env):
                print(_)
            return
        elif inspect.iscoroutinefunction(sub):
            await sub(*args)
            return

        from collections.abc import Iterator

        if isinstance(sub, Iterator):
            for _ in sub:
                print(_)
            return
        elif isinstance(
            sub,
            (
                str,
                Path,
            ),
        ):
            # subprocess
            return cls.parse_sync(sub, **env)
        else:
            await sub


import os

os.shell = shell
builtins.shell = shell
# end shell


if __UPY__:
    import types

    class SimpleNamespace:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

        def __repr__(self):
            keys = sorted(self.__dict__)
            items = ("{}={!r}".format(k, self.__dict__[k]) for k in keys)
            return "{}({})".format(type(self).__name__, ", ".join(items))

        def __eq__(self, other):
            return self.__dict__ == other.__dict__

    types.SimpleNamespace = SimpleNamespace
else:
    from types import SimpleNamespace

import builtins

builtins.PyConfig = SimpleNamespace(**PyConfig)
del PyConfig


# make simulations same each time, easier to debug
import random

random.seed(1)

import __EMSCRIPTEN__ as platform

platform.shell = shell
import aio.filelike

platform.fopen = aio.filelike.fopen
platform.sopen = aio.filelike.sopen

if not aio.cross.simulator:

    def fix_url(maybe_url):
        url = str(maybe_url)
        if url.startswith("http://"):
            pass
        elif url.startswith("https://"):
            pass
        elif url.startswith("https:/"):
            url = "https:/" + url[6:]
        elif url.startswith("http:/"):
            url = "http:/" + url[5:]
        return url

    platform.fix_url = fix_url

    del fix_url

    def apply_patches():
        # use shell generators instead of subprocesses
        # ==========================================================

        import os

        def popen(iterator, **kw):
            import io

            kw.setdefault("file", io.StringIO(newline="\r\n"))
            for line in iterator:
                print(line, **kw)
            kw["file"].seek(0)
            return kw["file"]

        os.popen = popen

        # add real browser functions
        # ===========================================================

        import webbrowser

        def browser_open(url, new=0, autoraise=True):
            platform.window.open(url, "_blank")

        def browser_open_new(url):
            return browser_open(url, 1)

        def browser_open_new_tab(url):
            return browser_open(url, 2)

        webbrowser.open = browser_open
        webbrowser.open_new = browser_open_new
        webbrowser.open_new_tab = browser_open_new_tab

        # extensions

        def browser_open_file(target=None, accept="*"):
            if target:
                platform.EventTarget.addEventListener(window, "upload", target)
            platform.window.dlg_multifile.click()

        webbrowser.open_file = browser_open_file

        # merge emscripten browser module here ?
        # https://rdb.name/panda3d-webgl.md.html#supplementalmodules/asynchronousloading
        #

        # use bad and deprecated sync XHR for urllib
        # ============================================================

        import urllib
        import urllib.request

        def urlretrieve(maybe_url, filename=None, reporthook=None, data=None):
            url = __EMSCRIPTEN__.fix_url(maybe_url)
            filename = str(filename or f"/tmp/uru-{aio.ticks}")
            rc = platform.window.python.DEPRECATED_wget_sync(str(url), filename)
            if rc == 200:
                return filename, []
            raise Exception(f"urlib.error {rc}")

        urllib.request.urlretrieve = urlretrieve

    if (__WASM__ and __EMSCRIPTEN__) or platform.is_browser:
        port = "443"

        # pygbag mode
        if platform.window.location.href.find("//localhost:") > 0:
            port = str(platform.window.location.port)

            # pygbag developer mode ( --dev )
            if ("-i" in PyConfig.orig_argv) or (port == "8666"):
                PyConfig.dev_mode = 1
                print(sys._emscripten_info)

            PyConfig.pygbag = 1
        else:
            PyConfig.pygbag = 0

        if (PyConfig.dev_mode > 0) or PyConfig.pygbag:
            # in pygbag dev mode use local repo
            PyConfig.pkg_indexes = []
            for idx in PYCONFIG_PKG_INDEXES_DEV:
                redirect = idx.replace("<port>", port)
                PyConfig.pkg_indexes.append(redirect)

            print("807: DEV MODE ON", PyConfig.pkg_indexes)
        # now in pep0723
        #        else:
        #            # address cdn
        #            PyConfig.pkg_indexes = PYCONFIG_PKG_INDEXES

        from platform import window, document, ffi

        apply_patches()

    del apply_patches

    # convert a emscripten FS path to a blob url
    # TODO: weakmap and GC collect
    def File(path):
        return platform.window.blob(str(path))

    # =================== async import , async console ===================================

    import os

    # set correct umask ( emscripten default is 0 )
    if hasattr(os, "umask"):
        os.umask(0o022)  # already done in aio.toplevel
        import zipfile
    else:
        pdb("1010: missing os.umask")
        pdb("1011: missing zipfile")

    import aio.toplevel

    # import ast
    from pathlib import Path

    class TopLevel_async_handler(aio.toplevel.AsyncInteractiveConsole):
        # be re entrant
        import_lock = []

        mute_state = False

        HTML_MARK = '"' * 3 + " # BEGIN -->"

        repos = []

        may_need = []
        ignore = ["ctypes", "distutils", "installer", "sysconfig"]
        ignore += ["python-dateutil", "matplotlib-pyodide"]
        # ???
        ignore += ["pillow", "fonttools"]

        # for ursina
        # ignore +=  ["ursina","gltf","pyperclip","screeninfo"]

        manual_deps = {
            "matplotlib": ["numpy", "six", "cycler", "PIL", "pygame-ce"],
            "bokeh": ["numpy", "yaml", "typing_extensions", "jinja2", "markupsafe"],
            "igraph": ["texttable"],
            "pygame_gui": ["pygame.base", "i18n"],
            "ursina": ["numpy", "screeninfo", "gltf", "PIL", "pyperclip", "panda3d"],
        }

        missing_fence = []

        from pathlib import Path

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

            DBG(f"1039: {count} lines queued for async eval")

        @classmethod
        def scan_imports(cls, code, filename, load_try=False, hint=""):
            import aio.pep0723
            import ast

            required = []
            try:
                root = ast.parse(code, filename)
            except SyntaxError as e:
                print("_" * 40)
                print("1111:", filename, hint)
                print("_" * 40)
                for count, line in enumerate(code.split("\n")):
                    print(str(count).zfill(3), line)
                sys.print_exception(e)
                return required

            for node in ast.walk(root):
                if isinstance(node, ast.Import):
                    module = []
                elif isinstance(node, ast.ImportFrom):
                    module = node.module.split(".")
                else:
                    continue

                for n in node.names:
                    if len(module):
                        mod = module[0] or n.name.split(".")[0]
                    else:
                        mod = n.name.split(".")[0]

                    mod = aio.pep0723.Config.mapping.get(mod, mod)

                    if mod in cls.ignore:
                        continue

                    if mod in cls.may_need:
                        continue

                    if mod in sys.modules:
                        continue

                    if load_try:
                        try:
                            __import__(mod)
                            continue
                        except (ModuleNotFoundError, ImportError):
                            pass

                    if not mod in required:
                        required.append(mod)

            DBG(f"1153: scan_imports {hint=} {filename=} {len(code)=} {required}")
            return required

        @classmethod
        def list_imports(cls, code=None, file=None, hint=""):
            import aio.pep0723

            if not len(aio.pep0723.Config.pkg_repolist):
                print(
                    """
1208: pep0723 REPOSITORY MISSING
"""
                )
            else:
                DBG(
                    f"""
1214: list_imports {len(code)=} {file=} {hint=}")
{aio.pep0723.Config.pkg_repolist[0]['-CDN-']=}

"""
                )

            if code is None:
                if file:
                    with open(file) as fcode:
                        code = fcode.read()
                else:
                    code = ""

            file = file or "<stdin>"

            for want in cls.scan_imports(code, file, hint=hint):
                # DBG(f"1114: requesting module {want=} for {file=} ")
                repo = None
                for repo in aio.pep0723.Config.pkg_repolist:
                    if want in cls.may_need:
                        DBG(f"1118: skip module {want=} reason: already requested")
                        break

                    if want in sys.modules:
                        DBG(f"1122: skip module {want=} reason: sys.modules")
                        break

                    if want in repo:
                        cls.may_need.append(want)
                        # DBG(f"1127: module {want=} requested")
                        yield want
                        break
                else:
                    if repo:
                        DBG(f"1187: {repo['-CDN-']=} does not provide {want=}")
                    else:
                        print("1189: no pkg repository available")
                    if not want in aio.pep0723.hint_failed:
                        aio.pep0723.hint_failed.append(want)

        # TODO: re order repo on failures
        # TODO: try to download from pypi with
        # https://github.com/brettcannon/mousebender/blob/main/mousebender/simple.py
        # https://peps.python.org/pep-0503/
        # https://wiki.python.org/moin/PyPIJSON

        # TODO: gets deps from pygbag
        # https://github.com/thebjorn/pydeps

        @classmethod
        def import_one(cls, mod, lvl=0):
            wants = []

            if mod in sys.modules:
                return []

            if mod in cls.missing_fence:
                return []
            from aio.pep0723 import Config

            for dep in Config.repos[0]["packages"].get(mod, {}).get("depends", []):
                if dep in cls.ignore:
                    continue

                if dep in cls.missing_fence:
                    continue

                cls.missing_fence.append(dep)

                if lvl < 3:
                    for subdep in cls.imports(mod, lvl=lvl + 1):
                        if not subdep in cls.missing_fence:
                            cls.missing_fence.append(subdep)

            if mod in cls.manual_deps:
                deps = list(cls.manual_deps[mod])
                deps.reverse()
                DBG(
                    f"""
1242:
    added {deps=} for {mod=}
1243:
    {cls.missing_fence=}

"""
                )
                for missing in deps:
                    if missing in cls.missing_fence:
                        continue

                    if missing in wants:
                        continue

                    # no need to request
                    if missing in sys.modules:
                        continue

                    # prio missing
                    wants.insert(0, missing)
                    DBG(f"1108: added {missing=} for {mod=}")

            wants.append(mod)
            return wants

        @classmethod
        def imports(cls, *mods, lvl=0):
            wants = []
            unseen = False
            for mod in mods:
                # get potential sub deps
                for dep in cls.import_one(mod, lvl=lvl):
                    if dep in wants:
                        continue

                    if dep in sys.modules:
                        continue

                    if dep in cls.missing_fence:
                        continue

                    if dep in cls.ignore:
                        continue

                    wants.append(dep)

                if not mod in wants:
                    wants.append(mod)

            return wants

    # end TopLevel_async_handler

    aio.toplevel.handler = TopLevel_async_handler

    async def dlopen(pkg):
        import platform
        import binascii
        import json

        dlref = await platform.jsiter(platform.window.dlopen(pkg))

        class dlproxy(object):
            def __init__(self, *argv, **env):
                self.__dlref = " ".join(map(str, argv))
                self.__lastc = "__init__"
                self.__serial = 0

            def __call__(self, callid, fn, *argv, **env):
                stack: list = [callid, fn, argv, env]
                jstack: str = binascii.hexlify(json.dumps(stack).encode()).decode("ascii")
                jshex = f"{self.__dlref}:{jstack}"
                if not callid:
                    window.dlvoid(jshex)
                    return None

                print(f"{self.__dlref}.{fn}({argv},{env}) {callid=}")

                async def rv():
                    obj = await platform.jsiter(window.dlcall(callid, jshex))
                    return json.loads(obj)

                return rv()

            def thread(self, fn, *argv, **env):
                return self.__call__("", fn, *argv, **env)

            def __all(self, *argv, **env):
                self.__serial += 1
                return self.__call__(f"C{self.__serial}", self.__lastc, *argv, **env)

            def __nonzero__(self):
                return 0

            def __nop__(self, other):
                return 0

            __add__ = __iadd__ = __sub__ = __isub__ = __mul__ = __imul__ = __div__ = __idiv__ = __nop__

            def __getattr__(self, attr):
                self.__lastc = attr
                return self.__all

            def iteritems(self):
                print(self, "iterator")
                return []

            def __del__(self):
                pass

            def __repr__(self):
                return "\ndlproxy: %s" % self.__dlref

            __str__ = __repr__

        return dlproxy(dlref)

    builtins.dlopen = dlopen

else:
    pdb("TODO: js simulator")


try:
    shell.screen_width = int(platform.window.canvas.width)
    shell.screen_height = int(platform.window.canvas.height)
except:
    shell.screen_width = 1024
    shell.screen_height = 600

# ======================================================
# patching
# import platform_wasm.todo


# ======================================================
# x10 mouse and xterm stuff
# https://github.com/muesli/termenv/pull/104
# https://xtermjs.org/docs/api/vtfeatures/

if not aio.cross.simulator:

    def ESC(*argv):
        for arg in argv:
            sys.__stdout__.write(chr(0x1B))
            sys.__stdout__.write(arg)
        embed.flush()

    def CSI(*argv):
        for arg in argv:
            ESC(f"[{arg}")

    builtins.ESC = ESC
    builtins.CSI = CSI

try:
    console
except:

    class console:
        def log(*argv, **kw):
            import io

            kw["file"] = io.StringIO(newline="\r\n")
            print(*argv, **kw)
            embed.warn(kw["file"].getvalue())


import aio.recycle

# ============================================================
# DO NOT ADD ANYTHING FROM HERE OR APP RECYCLING WILL TRASH IT

#
try:
    LOCK
except:
    import builtins

    builtins.LOCK = False


async def import_site(__file__, run=True):
    import builtins

    if builtins.LOCK:
        platform.window.console.error("1473: import_site IS NOT RE ENTRANT")
        return
    builtins.LOCK = True

    try:
        from pathlib import Path

        embed = False
        hint = "main.py"

        is_py = sys.argv[0].endswith(".py")

        # if not imported by simulator then aio is handled externally
        if "pygbag.aio" not in sys.modules:
            import aio

            sys.modules["pygbag.aio"] = aio

        # if running a script be silent for prompt
        TopLevel_async_handler.mute_state = ".py" in "".join(sys.argv)

        # always start async handler or we could not do imports on import errors.
        await TopLevel_async_handler.start_toplevel(platform.shell, console=True)

        # RUNNING GIVEN DISK FILE with no prompt
        # this is usually the import site given by javascript loader or a template loader (pygbag apk mode)
        # or the user script (script mode).

        if Path(__file__).is_file():
            DBG(f"1755: shell.source({__file__=})")
            await shell.source(__file__)

            # allow to set user site customization network, or embedded js to be processed
            await asyncio.sleep(0)

            if PyConfig.user_site_directory:
                DBG(f"1768: {__file__=} done, giving hand to user_site")
                return __file__
            else:
                DBG(f"1764: {__file__=} done : now trying user sources")
        else:
            DBG(f"1767: {__file__=} NOT FOUND : now trying user sources")

        # NOW CHECK OTHER SOURCES

        # where to retrieve
        import tempfile

        tmpdir = Path(tempfile.gettempdir())

        # maybe a script filename or content passed as frozen config.

        source = getattr(PyConfig, "frozen", "")
        if source:
            if Path(source).is_file():
                source_path = getattr(PyConfig, "frozen_path", "")
                handler = getattr(PyConfig, "frozen_handler", "")
                DBG("1786: embed path", source_path, "will embed", source, "handled by", handler)
                local = tmpdir / "embed.py"
                with open(source, "r") as src:
                    with open(local, "w") as file:
                        file.write("import sys, pygame;from aio.fetch import FS\n")
                        file.write(src.read())

                        # default handler is run() when embedding
                        if not handler:
                            file.write(
                                """
    __main__ = vars().get('run')
    async def main():
        global __main__
        if 'aio.fetch' in sys.modules:
            import aio.fetch
            await aio.fetch.preload()
            await asyncio.sleep(0)
        if __main__:
            await __main__()
    asyncio.run(main())
    """
                            )
                        else:
                            async with platform.fopen(handler) as handle:
                                file.write("\n")
                                file.write(handle.read())
                embed = True
            else:
                print(f"1814: invalid embed {source=}")
                return None

            # file has been retrieved stored in local
        else:
            local = None
            # no embed, try sys.argv[0] first, but main.py can only be a hint.
            # of what to run in an archive

            if sys.argv[0] == "main.py" or not is_py:
                source = PyConfig.orig_argv[-1]
                if is_py:
                    hint = sys.argv[0]
            else:
                source = sys.argv[0]

        DBG(f"1830: {local=} {source=} {is_py=} {hint=}")

        if local is None:

            ext = str(source).rsplit(".")[-1].lower()

            if ext == "py":
                local = tmpdir / source.rsplit("/", 1)[-1]
                await shell.exec(shell.wget(f"-O{local}", source))
            # TODO: test tar.bz2 lzma tar.xz
            elif ext in ("zip", "gz", "tar", "apk", "jar"):
                DBG(f"1841: found archive source {source=}")
                # download and unpack into tmpdir
                fname = tmpdir / source.rsplit("/")[-1]

                if ext in ("apk", "jar"):
                    fname = fname + ".zip"

                async with platfom.fopen(source, "rb") as zipdata:
                    with open(fname, "wb") as file:
                        file.write(zipdata.read())
                import shutil

                shutil.unpack_archive(fname, tmpdir)
                os.unlink(fname)

                # locate for an entry point after decompression
                hint = "/" + hint.strip("/")
                for file in shell.find(tmpdir):
                    if file.find(hint) > 0:
                        local = tmpdir / file
                        break
                DBG("1862: import_site: found ", local)
            elif str(source).startswith("http"):
                print("Remote file :", source)
                local = tmpdir / "remote.py"
                await shell.exec(shell.wget(f"-O{local}", source))
            else:
                # maybe base64 or frozen code in html.
                ...

        DBG(f"1867: {local=} {source=} {is_py=} {hint=}")

        if local and local.is_file():
            pdir = str(local.parent)
            os.chdir(pdir)
            if "-v" in PyConfig.orig_argv:
                print()
                print("_" * 70)
                with open(local, "r") as source:
                    for i, l in enumerate(source.readlines()):
                        print(str(i).zfill(5), l, end="")
                print()
                print("_" * 70)
                print()

            # TODO: check orig_argv for isolation parameters
            if not pdir in sys.path:
                sys.path.insert(0, pdir)

            if run:
                await shell.runpy(local)
            return str(local)
        else:
            # show why and drop to prompt
            print(f"404: embed={source} or {sys.argv=}")
            shell.interactive(prompt=True)
            return None
    finally:
        builtins.LOCK = False
