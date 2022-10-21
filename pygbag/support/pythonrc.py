#!pythonrc.py

import os, sys, json, builtins

# to be able to access aio.cross.simulator
import aio
import aio.cross

import time

PYCONFIG_PKG_INDEXES_DEV = ["http://localhost:<port>/archives/repo/"]
PYCONFIG_PKG_INDEXES = ["https://pygame-web.github.io/archives/repo/"]

# the sim does not preload assets and cannot access currentline
# unless using https://github.com/pmp-p/aioprompt/blob/master/aioprompt/__init__.py

if not defined("undefined"):

    class sentinel:
        def __bool__(self):
            return False

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


try:
    # mpy already has execfile
    execfile
except:

    def execfile(filename):
        global pgzrun

        imports = []

        with __import__("tokenize").open(str(filename)) as f:
            __prepro = []
            myglobs = ["setup", "loop", "main"]
            tmpl = []

            pgzrun = None

            for l in f.readlines():
                if pgzrun is None:
                    pgzrun = l.find("pgzrun") > 0

                testline = l.split("#")[0].strip(" \r\n,\t")

                if testline.startswith("global ") and (
                    testline.endswith(" setup")
                    or testline.endswith(" loop")
                    or testline.endswith(" main")
                ):
                    tmpl.append([len(__prepro), l.find("g")])
                    __prepro.append("#globals")
                    continue

                elif testline.startswith("import "):
                    testline = testline.replace("import ", "").strip()
                    imports.extend(map(str.strip, testline.split(",")))

                elif testline.startswith("from "):
                    testline = testline.replace("from ", "").strip()
                    imports.append(testline.split(" import ")[0].strip())

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
                if pgzrun or "pgzrun" in imports:
                    # Indicate that we're running with the pgzrun runner
                    # and disable the pgzrun module
                    sys._pgzrun = True

                    sys.modules["pgzrun"] = type(__main__)("pgzrun")
                    import pgzrun

                    pgzrun.go = lambda: None

                    import pgzero
                    import pgzero.runner

                    pgzero.runner.prepare_mod(__main__)
                print("*" * 40)
                print(imports)
                print("*" * 40)

                exec(code, __main__dict, __main__dict)
                if pgzrun:
                    pgzero.runner.run_mod(__main__)

        return __import__("__main__")

    define("execfile", execfile)

if defined("embed") and hasattr(embed, "readline"):
    import inspect
    from pathlib import Path
    import json
    # import urllib.request
    # import aio.toplevel

    class shell:
        out = []

        if aio.cross.simulator:
            ROOT = os.getcwd()
            HOME = os.getcwd()
        else:
            ROOT = f"/data/data/{sys.argv[0]}"
            HOME = f"/data/data/{sys.argv[0]}/assets"

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
        def clear(cls, *argv, **kw):
            """clear terminal screen"""
            import pygame

            screen = pygame.display.set_mode([1024, 600])
            screen.fill((0, 0, 0))
            pygame.display.update()

        @classmethod
        def display(cls, *argv, **kw):
            """show images, or last repl pygame surface from _"""
            import pygame

            if not len(argv):
                surf = _
            else:
                ext = argv[-1].lower()
                if ext.endswith(".six"):
                    cls.more(argv[-1])
                    return
                if ext.endswith("bmp"):
                    surf = pygame.image.load_basic(argv[-1])
                else:
                    surf = pygame.image.load(argv[-1])

            screen = pygame.display.set_mode([1024, 600])
            screen.blit(surf, (1, 1))
            pygame.display.update()

        @classmethod
        def pgzrun(cls, *argv):
            global pgzrun
            pgzrun = True
            cls.exec(*argv)

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
                fn = filename or str(argv[0]).rsplit('/')[-1]
                try:
                    filename, _ = urllib.request.urlretrieve(str(arg), filename=fn)
                except Exception as e:
                    yield e

            return True

        @classmethod
        def pwd(cls, *argv):
            print(os.getcwd())

        # only work if pkg name == dist name
        @classmethod
        async def pip(cls, *argv):
            if argv[0] == "install":
                import aio.toplevel

                await aio.toplevel.importer.async_imports(argv[1])

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
            global pgzrun
            # TODO extract env from __main__ snapshot
            if cmd.endswith(".py"):
                if pgzrun:
                    print(
                        "a program is already running, using 'stop' cmd before retrying"
                    )
                    cls.stop()
                    pgzrun = None
                    aio.defer(cls.spawn, (cmd, *argv), env, delay=500)

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
                    zip_ref.extractall(os.getcwd())

        @classmethod
        def install(cls, *argv, **env):
            import aio.toplevel

            for pkg_file in argv:
                try:
                    aio.toplevel.install(pkg_file)
                    yield f"{pkg_file} installed"
                except (IOError, zipfile.BadZipFile):
                    pdb("397: invalid package", pkg_file)
                except Exception as ex:
                    sys.print_exception(ex)

        @classmethod
        def dll(cls, *argv):
            cdll = __import__("ctypes").CDLL(None)
            print(getattr(cdll, argv[0])(*argv[1:]))
            return True

        @classmethod
        def strace(cls, *argv, **env):
            import aio.trace

            sys.settrace(aio.trace.calls)
            return _process_args(argv, env)

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
                return cls._process_args(argv, env)
            return False

        time = run

        @classmethod
        def ps(cls, *argv, **env):
            for t in aio.all_tasks():
                print(t)
            return True

        @classmethod
        def stop(cls, *argv, **env):
            global pgzrun
            aio.exit = True
            # pgzrun will reset to None next exec
            if not pgzrun:
                # pgzrun does its own cleanup call
                aio.defer(aio.recycle.cleanup, (), {}, delay=500)
                aio.defer(embed.prompt, (), {}, delay=800)

        @classmethod
        def uptime(cls, *argv, **env):
            import asyncio, platform

            if platform.is_browser:

                def load_display(ft):
                    avg = sum(ft) / len(ft)
                    try:
                        platform.window.load_avg.innerText = "{:.4f}".format(avg)
                        platform.window.load_min.innerText = "{:.4f}".format(min(ft))
                        platform.window.load_max.innerText = "{:.4f}".format(max(ft))
                        return True
                    except:
                        pdb("366:uptime: window.load_* widgets not found")
                        return False

                async def perf_index():
                    ft = [0.00001] * 60 * 10
                    while not aio.exit:
                        ft.pop(0)
                        ft.append(aio.spent / 0.016666666666666666)
                        if not (aio.ticks % 60):
                            if not load_display(ft):
                                break
                        await asyncio.sleep(0)

                aio.create_task(perf_index())
            else:
                print(f"last frame : {aio.spent / 0.016666666666666666:.4f}")

        @classmethod
        async def exec(cls, sub, *argv):
            if inspect.isgenerator(sub):
                for _ in sub:
                    print(_)
                return
            elif inspect.isgeneratorfunction(sub):
                for _ in sub(*argv):
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
            elif isinstance(sub, (str, Path,) ):
                # subprocess
                print("N/I", sub)
            else:
                await sub


        @classmethod
        async def preload(cls, main, callback=None):
            # get a relevant list of modules likely to be imported
            # and prefetch them if found in repo trees
            imports = TopLevel_async_handler.list_imports(code=None, file=main)
            print(f"579: {list(imports)}")
            await TopLevel_async_handler.async_imports(*imports, callback=callback)
            PyConfig.imports_ready = True
            return True

        @classmethod
        async def source(cls, main, *args):
            code = ""

            def check_code(file_name):
                nonlocal code
                maybe_sync = False
                has_pygame = False
                with open(file_name,"r") as code_file:
                    code = code_file.read()
                    if code.find('asyncio.run')<0:
                        print("575 possibly synchronous code found")
                        maybe_sync = True

                    has_pygame =  code.find('display.flip(')>0 or code.find('display.update(')>0

                    if maybe_sync and has_pygame:
                        return False
                return True

            if check_code(main):
                print("585: running main and resuming EventTarget in a few seconds")
                aio.defer(execfile, (main,), {} )

                # makes all queued events arrive after program has looped a few cycles
                # note that you need a call to asyncio.run in your main to continue past
                # that check
                while not aio.run_called:
                    await asyncio.sleep(.1)


                # if you don't reach that step
                # your main.py has an infinite sync loop somewhere !
                print("590: ready")


                aio.create_task(platform.EventTarget.process())

                pdb("platform event loop started")


            else:
                for base in ('pygame','pg'):
                    for func in ('flip','update'):
                        block =  f'{base}.display.{func}()'
                        code = code.replace( block, f'{block};await asyncio.sleep(0)')

                #print(" -> won't run synchronous code with a pygame loop")
                shell.debug()

                TopLevel_async_handler.instance.eval(code)
                TopLevel_async_handler.instance.start_console(shell)




    def _process_args(argv, env):
        import inspect

        catch = True
        for cmd in argv:
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
            else:
                catch = shell.exec(cmd, *args, **env)
        return catch


try:
    PyConfig
    PyConfig["pkg_repolist"] = []

    aio.cross.simulator = False
    sys.argv = PyConfig.pop("argv", [])

except Exception as e:
    sys.print_exception(e)
    # TODO: build a pyconfig extracted from C here
    PyConfig = {}
    PyConfig["dev_mode"] = 1
    PyConfig["run_filename"] = "main.py"
    PyConfig["executable"] = sys.executable
    PyConfig["interactive"] = 1
    print(" - running in wasm simulator - ")
    aio.cross.simulator = True

PyConfig["imports_ready"] = false


from types import SimpleNamespace
import builtins

builtins.PyConfig = SimpleNamespace(**PyConfig)
del PyConfig


# make simulations same each time, easier to debug
import random

random.seed(1)


if not aio.cross.simulator:
    import __EMSCRIPTEN__ as platform

    platform.shell = shell

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

    __EMSCRIPTEN__.fix_url = fix_url

    del fix_url

    def apply_patches():


        # use shell generators instead of subprocesses
        # ==========================================================

        import os

        def popen(iterator, **kw):
            import io
            kw.setdefault("file", io.StringIO(newline="\r\n"))
            for line in iterator:
                print(line,**kw)
            kw['file'].seek(0)
            return kw['file']

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
                platform.EventTarget.addEventListener("upload", target)
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
            filename = filename or f"/tmp/uru-{aio.ticks}"
            rc = platform.window.python.DEPRECATED_wget_sync(str(url), str(filename))
            if rc == 200:
                return filename, []
            raise Exception(f"urlib.error {rc}")

        urllib.request.urlretrieve = urlretrieve

    if (__WASM__ and __EMSCRIPTEN__) or platform.is_browser:
        port = "443"

        # pygbag mode
        if platform.window.location.href.find("localhost") > 0:
            port = str(platform.window.location.port)

            # pygbag developer mode
            if port == "8666":
                PyConfig.dev_mode = 1

        if PyConfig.dev_mode > 0:
            print(sys._emscripten_info)
            # in pygbag dev mode use local repo
            PyConfig.pkg_indexes = []
            for idx in PYCONFIG_PKG_INDEXES_DEV:
                PyConfig.pkg_indexes.append(idx.replace("<port>", port))
        else:
            # address cdn
            PyConfig.pkg_indexes = PYCONFIG_PKG_INDEXES

        from platform import window, document

        class fopen:
            ticks = 0

            def __init__(self, maybe_url, mode="r"):
                self.url = __EMSCRIPTEN__.fix_url(maybe_url)
                self.mode = mode
                self.tmpfile = None

            async def __aenter__(self):
                import platform

                # print(f'572: Download start: "{self.url}"')

                if "b" in self.mode:
                    self.__class__.ticks += 1
                    self.tmpfile = f"/tmp/cf-{self.ticks}"
                    cf = platform.window.cross_file(self.url, self.tmpfile)
                    content = await platform.jsiter(cf)
                    self.filelike = open(content, "rb")
                    self.filelike.path = content

                    def rename_to(target):
                        print("rename_to", content, target)
                        # will be closed
                        self.filelike.close()
                        os.rename(self.tmpfile, target)
                        self.tmpfile = None
                        del self.filelike.rename_to
                        return target

                else:
                    import io

                    jsp = platform.window.fetch(self.url)
                    response = await platform.jsprom(jsp)
                    content = await platform.jsprom(response.text())
                    if len(content) == 4:
                        print("585 fopen", f"Binary {self.url=} ?")
                    self.filelike = io.StringIO(content)

                    def rename_to(target):
                        with open(target, "wb") as data:
                            date.write(self.filelike.read())
                        del self.filelike.rename_to
                        return target

                self.filelike.rename_to = rename_to
                return self.filelike

            async def __aexit__(self, *exc):
                if self.tmpfile:
                    self.filelike.close()
                    os.unlink(self.tmpfile)
                del self.filelike, self.url, self.mode, self.tmpfile
                return False

        platform.fopen = fopen

        async def jsiter(iterator):
            mark = None
            value = undefined
            while mark != undefined:
                value = mark
                await asyncio.sleep(0)
                mark = next(iterator, undefined)
            return value

        platform.jsiter = jsiter

        async def jsprom(prom):
            mark = None
            value = undefined
            wit = platform.window.iterator(prom)
            while mark != undefined:
                value = mark
                await aio.sleep(0)
                mark = next(wit, undefined)
            return value

        platform.jsprom = jsprom

        apply_patches()

    del apply_patches

    # =================== async import , async console ===================================

    import os

    # set correct umask ( emscripten default is 0 )
    os.umask(0o022)  # already done in aio.toplevel

    import zipfile
    import aio.toplevel
    import ast
    from pathlib import Path



    class TopLevel_async_handler(aio.toplevel.AsyncInteractiveConsole):

        repos = []
        mapping = {}
        may_need = []
        ignore = ["distutils", "installer", "sysconfig"]
        ignore += ["python-dateutil", "matplotlib-pyodide"]
        # ???
        ignore += ["pillow", "fonttools"]

        from pathlib import Path

        repodata = "repodata.json"



        def raw_input(self, prompt):
            if len(self.buffer):
                return self.buffer.pop(0)

            maybe = embed.readline()

            if len(maybe):
                return maybe
            else:
                return None
            # raise EOFError


        def eval(self, source):
            for line in source.split('\n'):
                self.buffer.append( line )
            self.buffer.append("")
            print(f"917 {len(self.buffer)} lines queued for async eval")

        @classmethod
        def scan_imports(cls, code, filename, load_try=False):
            root = ast.parse(code, filename)
            required = []
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

                    required.append(mod)
            return required

        @classmethod
        def list_imports(cls, code=None, file=None):
            import platform
            import json

            if code is None:
                with open(file) as fcode:
                    code = fcode.read()

            for want in cls.scan_imports(code, file):
                for repo in PyConfig.pkg_repolist:
                    if want in cls.may_need:
                        continue

                    if want in sys.modules:
                        continue

                    if want in repo:
                        cls.may_need.append(want)
                        yield want
                        break

        @classmethod
        def imports(cls, *mods, lvl=0, wants=[]):
            unseen = False
            for mod in mods:
                for dep in cls.repos[0]["packages"].get(mod, {}).get("depends", []):
                    if mod in sys.modules:
                        continue

                    if (not dep in wants) and (not dep in cls.ignore):
                        unseen = True
                        wants.insert(0, dep)

            if lvl < 3 and unseen:
                cls.imports(*wants, lvl=lvl + 1, wants=wants)

            if not lvl:
                for dep in mods:
                    if mod in sys.modules:
                        continue

                    if (not dep in wants) and (not dep in cls.ignore):
                        wants.append(dep)
            return wants

        @classmethod
        async def async_imports(cls, *wanted, **kw):
            def default_cb(pkg, error=None):
                if error:
                    pdb(msg)
                else:
                    print(f"\tinstalling {pkg}")

            kw.setdefault('callback',default_cb)


            #        # using pyodide repodata
            #            refresh = False
            #            for pkg in packages:
            #                pkg_info = cls.repos[0]["packages"].get(pkg, None)
            #                file_name = pkg_info.get("file_name", "")
            #                valid = False
            #                if file_name:
            #                    pkg_file = f"/tmp/{file_name}"

            #                    async with platform.fopen(
            #                        cls.dl_cdn / file_name, "rb"
            #                    ) as source:
            #                        source.rename_to(pkg_file)
            #                        for hex in shell.sha256sum(pkg_file):
            #                            expected = hex.split(" ", 1)[0].lower()
            #                            maybe = pkg_info.get("sha256", "").lower()
            #                            if maybe and (maybe != expected):
            #                                pdb(
            #                                    f"158: {pkg} download to {pkg_file} corrupt",
            #                                    pkg_info.get("sha256", ""),
            #                                    expected,
            #                                )
            #                                break
            #                        else:
            #                            valid = True
            #                            refresh = True
            #                else:
            #                    pdb(f'144: package "{pkg}" invalid in repodata')
            #                    continue


            # init dep solver.
            if not len(cls.repos):
                for cdn in PyConfig.pkg_indexes:
                    async with platform.fopen(Path(cdn) / cls.repodata) as source:
                        cls.repos.append(json.loads(source.read()))

                # print(json.dumps(cls.repos[0]["packages"], sort_keys=True, indent=4))

                print("referenced packages :", len(cls.repos[0]["packages"]))

            if not len(PyConfig.pkg_repolist):
                await cls.async_repos()

            if PyConfig.dev_mode > 0:
                for idx, repo in enumerate(PyConfig.pkg_repolist):
                    print(repo["-CDN-"], "REMAPPED TO", PyConfig.pkg_indexes[idx])
                    repo["-CDN-"] = PyConfig.pkg_indexes[idx]

            all = cls.imports(*wanted)
            if "numpy" in all:
                kw['callback']('numpy')
                try:
                    await cls.get_pkg("numpy")
                    import numpy
                    all.remove("numpy")
                except (IOError, zipfile.BadZipFile):
                    pdb("914: cannot load numpy")
                    return

            for req in all:
                if req == "python-dateutil":
                    req = "dateutil"

                if req == "pillow":
                    req = "PIL"

                if req in cls.ignore or req in sys.modules:
                    continue
                kw['callback'](req)
                try:
                    await cls.get_pkg(req)
                except (IOError, zipfile.BadZipFile):
                    msg=f"928: cannot download {req} pkg"
                    kw['callback'](req,error=msg)



        # TODO: re order repo on failures
        # TODO: try to download from pypi with
        # https://github.com/brettcannon/mousebender/blob/main/mousebender/simple.py
        # https://peps.python.org/pep-0503/
        # https://wiki.python.org/moin/PyPIJSON

        # TODO: gets deps from pygbag
        # https://github.com/thebjorn/pydeps

        @classmethod
        async def async_get_pkg(cls, want, ex, resume):
            pkg_file = ""
            for repo in PyConfig.pkg_repolist:
                # print("954:", want, want in repo)
                if want in repo:
                    pkg_url = f"{repo['-CDN-']}{repo[want]}"

                    pkg_file = f"/tmp/{repo[want].rsplit('/',1)[-1]}"

                    cfg = {"io": "url", "type": "fs", "path": pkg_file}
                    print("pkg :", pkg_url)

                    track = platform.window.MM.prepare(pkg_url, json.dumps(cfg))

                    try:
                        await cls.pv(track)
                        zipfile.ZipFile(pkg_file).close()
                        break
                    except (IOError, zipfile.BadZipFile):
                        pdb(
                            f"960: network error on {repo['-CDN-']}, cannot install {pkg_file}"
                        )
            else:
                print(f"PKG NOT FOUND : {want=}, {resume=}, {ex=}")
                return None
            return await aio.toplevel.get_repo_pkg(pkg_file, want, resume, ex)

        @classmethod
        def get_pkg(cls, want, ex=None, resume=None):
            return cls.async_get_pkg(want, ex, resume)

        async def pv(
            track, prefix="", suffix="", decimals=1, length=70, fill="X", printEnd="\r"
        ):

            # Progress Bar Printing Function
            def print_pg_bar(total, iteration):
                if iteration > total:
                    iteration = total
                percent = ("{0:." + str(decimals) + "f}").format(
                    100 * (iteration / float(total))
                )
                filledLength = int(length * iteration // total)
                bar = fill * filledLength + "-" * (length - filledLength)
                print(f"\r{prefix} |{bar}| {percent}% {suffix}", end=printEnd)

            # Update Progress Bar
            while True:
                if track.pos < 0:
                    raise IOError(404)
                print_pg_bar(track.len or 100, track.pos or 0)
                if track.avail:
                    break
                await asyncio.sleep(0.02)

            # Print New Line on Complete
            print()

        @classmethod
        async def async_repos(cls):
            abitag = f"cp{sys.version_info.major}{sys.version_info.minor}"
            for repo in PyConfig.pkg_indexes:
                async with fopen(f"{repo}index.json", "r") as index:
                    try:
                        data = index.read().replace("<abi>", abitag)
                        repo = json.loads(data)
                    except:
                        pdb(f"{repo}: malformed json index {data}")
                        continue
                    PyConfig.pkg_repolist.append(repo)


    # convert a emscripten FS path to a blob url
    # TODO: weakmap and GC collect
    def File(path):
        return platform.window.blob(str(path))

else:
    pdb("TODO: js simulator")

# ======================================================


def ESC(*argv):
    for arg in argv:
        sys.__stdout__.write(chr(0x1B))
        sys.__stdout__.write(arg)


def CSR(*argv):
    for arg in argv:
        ESC("[", arg)


pgzrun = None

if os.path.isfile("/data/data/usersite.py"):
    execfile("/data/data/usersite.py")

import aio.recycle

# ============================================================
# DO NOT ADD ANYTHING FROM HERE OR APP RECYCLING WILL TRASH IT


#
