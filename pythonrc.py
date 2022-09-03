#!pythonrc.py

import os, sys, json, builtins

# to be able to access aio.cross.simulator
import aio
import aio.cross

import time

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
            """ dump binary file content """
            for fn in map(str,argv):
                with open(fn, "rb") as out:
                    print(out.read())

        @classmethod
        def more(cls, *argv):
            """ dump text file content """
            for fn in map(str,argv):
                with open(fn, "r") as out:
                    print(out.read())

        @classmethod
        def pp(cls, *argv):
            """ pretty print objects via json """
            for obj in argv:
                obj = eval( obj, vars(__import__("__main__") ) )
                if isinstance(obj, platform.Object_type):
                    obj = json.loads( platform.window.JSON.stringify(obj) )
                yield json.dumps(obj, sort_keys=True, indent=4)


        @classmethod
        def ls(cls, *argv):
            """ list directory content """
            if not len(argv):
                argv = ["."]
            for arg in map(str,argv):
                for out in sorted(os.listdir(arg)):
                    print(out)

        @classmethod
        def clear(cls, *argv,**kw):
            """ clear terminal screen """
            import pygame
            screen = pygame.display.set_mode([1024,600])
            screen.fill( (0, 0, 0) )
            pygame.display.update()

        @classmethod
        def display(cls,*argv,**kw):
            """ show images, or last repl pygame surface from _ """
            import pygame
            if not len(argv):
                surf = _
            else:
                ext = argv[-1].lower()
                if ext.endswith('.six'):
                    cls.more(argv[-1])
                    return
                if ext.endswith('bmp'):
                    surf = pygame.image.load_basic( argv[-1] )
                else:
                    surf = pygame.image.load( argv[-1] )

            screen = pygame.display.set_mode([1024,600])
            screen.blit( surf, (1,1) )
            pygame.display.update()


        @classmethod
        def pgzrun(cls, *argv):
            global pgzrun
            pgzrun = True
            cls.exec(*argv)

        @classmethod
        def mkdir(cls, *argv):
            exist_ok = "-p" in argv
            for arg in argv:
                if arg == "-p":
                    continue
                os.makedirs(arg, exist_ok=exist_ok)

        @classmethod
        def wget(cls, *argv, **env):
            import urllib.request
            filename = None
            for arg in map(str,argv):

                if arg.startswith("-O"):
                    filename = arg[2:].lstrip()
                    continue
                filename,_ = urllib.request.urlretrieve(arg, filename=filename)
                filename = None
            return True

        @classmethod
        def pwd(cls, *argv):
            print(os.getcwd())


        # only work if pkg name == dist name
        @classmethod
        async def pip(cls, *argv):
            if argv[0] == 'install':
                await importer.async_imports(argv[1])


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
            for arg in map(str,argv):
                sha256_hash = hashlib.sha256()
                with open(arg, "rb") as f:
                    # Read and update hash string value in blocks of 4K
                    for byte_block in iter(lambda: f.read(4096),b""):
                        sha256_hash.update(byte_block)
                    hx = sha256_hash.hexdigest()
                    yield f"{hx}  {arg}"

        @classmethod
        def exec(cls, cmd, *argv, **env):
            global pgzrun
            # TODO extract env from __main__ snapshot
            if cmd.endswith(".py"):
                if pgzrun:
                    print("a program is already running, using 'stop' cmd before retrying")
                    cls.stop()
                    pgzrun = None
                    aio.defer(cls.exec,(cmd,*argv),env, delay=500)

                else:
                    execfile(cmd)
                return True
            return False

        @classmethod
        def dll(cls, *argv):
            cdll = __import__("ctypes").CDLL(None)
            print( getattr(cdll, argv[0])(*argv[1:]) )
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
            print("""
pygbag shell help
________________________
""")
            if not len(objs):
                objs = [cls]
            for obj in objs:
                for cmd, item in vars(obj).items():
                    if isinstance(item, str):
                        continue
                    if cmd[0]!='_' and item.__doc__:
                        print(cmd,":", item.__doc__)
                        print()


# TODO: use run interactive c-api to run this one.
        @classmethod
        def run(cls, *argv, **env):

            __main__ = __import__("__main__")
            __main__dict = vars(__main__)

            builtins._ = undefined
            cmd =  " ".join(argv)

            try:
                time_start = time.time()
                code = compile("builtins._ =" + cmd, "<stdin>", "exec")
                exec(code, __main__dict, __main__dict)
                if builtins._ is undefined:
                    return True
                if aio.iscoroutine(_):
                    async def run(coro):
                        print(f"async[{cmd}] :",await coro)
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
                async def perf_index():
                    ft = [0.00001] * 60*10
                    while not aio.exit:
                        ft.pop(0)
                        ft.append(aio.spent / 0.016666666666666666 )
                        if not (aio.ticks % 60):
                            avg =  sum(ft) / len(ft)
                            try:
                                window.load_avg.innerText = '{:.4f}'.format(avg)
                                window.load_min.innerText = '{:.4f}'.format(min(ft))
                                window.load_max.innerText = '{:.4f}'.format(max(ft))
                            except:
                                pdb("366:uptime: window.load_* widgets not found")
                                break

                        await asyncio.sleep(0)
                aio.create_task( perf_index() )
            else:
                print(f"last frame : {aio.spent / 0.016666666666666666:.4f}")

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
                        aio.create_task( fn(*args) )
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

    def excepthook(etype, e, tb):
        global last_fail

        catch = False

        if isinstance(e, NameError):
            catch = True

        if isinstance(e, KeyboardInterrupt):
            print('\r\nKeyboardInterrupt')
            return embed.prompt()


        if catch or isinstance(e, SyntaxError) and (e.filename == "<stdin>"):
            catch = True
            cmdline = embed.readline().strip()

            # TODO: far from perfect !
            if cmdline.find('await ')>=0:
                import aio.toplevel
                aio.create_task( aio.toplevel.retry(cmdline, (etype, e, tb,) ) )
                # no prompt we're going async exec on aio now
                return

            # index = readline.get_current_history_length()

            # asyncio.get_event_loop().create_task(retry(index))
            # store trace
            # last_fail.append([etype, e, tb])


            catch = _process_args(cmdline.strip().split(";"), {})

        if not catch:
            sys.__excepthook__(etype, e, tb)
        else:
            embed.prompt()

    sys.excepthook = excepthook



try:
    PyConfig
    aio.cross.simulator = False
    print(sys._emscripten_info )
#    aio.cross.simulator = (
#        __EMSCRIPTEN__ or __wasi__ or __WASM__
#    ).PyConfig_InitPythonConfig(PyConfig)

# except NameError:
except Exception as e:
    sys.print_exception(e)
    #   TODO: get a pyconfig from C here

    PyConfig = {}
    print(" - running in wasm simulator - ")
    aio.cross.simulator = True


# make simulations same each time, easier to debug
import random
random.seed(1)










if not aio.cross.simulator:
    import __EMSCRIPTEN__ as platform


    """

embed.preload("/usr/lib/python3.10/site-packages/numpy/core/_multiarray_umath.cpython-310-wasm32-emscripten.so")

https://pypi.org/pypi/pygbag/0.1.3/json

"""

    class importer:

        repos = []
        mapping = {}
        may_need = []
        ignore = ["sys", "os", "asyncio", "pathlib", "platform", "pygame", "json"]
        ignore += ["distutils", "installer", "sysconfig", "sys"]

        from pathlib import Path
        if 1:
            if platform.window.location.hostname == "localhost":
                cdn = Path(platform.window.location.origin)
                dl_cdn = cdn
                repodata = "pip.json"
            else:
                cdn = Path("https://pygame-web.github.io/archives/0.2.0")
                dl_cdn = Path("https://cdn.jsdelivr.net/pyodide/v0.20.0/full")
                repodata = "packages.json"
        else:
            dl_cdn = Path("https://cdn.jsdelivr.net/pyodide/dev/full")
            cdn = dl_cdn
            repodata = "repodata.json"

        print(f"552 CDN: {cdn}")

        @classmethod
        def code_imports(cls, code=''):

            import platform
            import json


            def scan_imports(code, filename):
                nonlocal cls
                ast = __import__("ast")
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

                        try:
                            __import__(mod)
                        except (ModuleNotFoundError, ImportError):
                            required.append(mod)
                return required

            if code == '':
                with open(__file__) as fcode:
                    #assert code == fcode.read()
                    cls.may_need.extend( scan_imports(fcode.read(), __file__) )
            else:
                cls.may_need.extend( scan_imports(code, "<stdin>") )

        @classmethod
        async def async_imports(cls, *wanted):

            def imports(*mods, lvl=0, wants=[]):
                nonlocal cls
                unseen = False
                for mod in mods:
                    for dep in cls.repos[0]["packages"][mod].get("depends", []):
                        if (not dep in wants) and (not dep in cls.ignore):
                            unseen = True
                            wants.insert(0, dep)
                if lvl < 3 and unseen:
                    imports(*wants, lvl=lvl + 1, wants=wants)

                if not lvl:
                    for dep in mods:
                        if (not dep in wants) and (not dep in cls.ignore):
                            wants.append(dep)
                return wants


            async def pkg_install(*packages):
                nonlocal cls
                import sys
                import sysconfig
                import importlib
                refresh = False
                for pkg in packages:
                    pkg_info = cls.repos[0]["packages"].get(pkg, None)


                    if pkg_info is None:
                        pdb(f'144: package "{pkg}" not found in repodata')
                        continue

                    file_name = pkg_info.get("file_name",'')
                    valid = False
                    if file_name:
                        pkg_file = f"/tmp/{file_name}"

                        async with platform.fopen(cls.dl_cdn / file_name, "rb") as source:
                            source.rename_to(pkg_file)
                            for hex in shell.sha256sum(pkg_file):
                                expected = hex.split(' ',1)[0].lower()
                                maybe = pkg_info.get("sha256","").lower()
                                if maybe and (maybe!=expected):
                                    pdb(f"158: {pkg} download to {pkg_file} corrupt",pkg_info.get("sha256",""),expected)
                                    break
                            else:
                                valid = True
                                refresh = True
                    else:
                        pdb(f'144: package "{pkg}" invalid in repodata')
                        continue

                    if valid:

                        from installer import install
                        from installer.destinations import SchemeDictionaryDestination
                        from installer.sources import WheelFile

                        # Handler for installation directories and writing into them.
                        destination = SchemeDictionaryDestination(
                            sysconfig.get_paths(),
                            interpreter=sys.executable,
                            script_kind="posix",
                        )

                        with WheelFile.open(pkg_file) as source:
                            install(
                                source=source,
                                destination=destination,
                                # Additional metadata that is generated by the installation tool.
                                additional_metadata={
                                    "INSTALLER": b"pygbag",
                                },
                            )
                if refresh:
                    await asyncio.sleep(0)
                    importlib.invalidate_caches()
                    await asyncio.sleep(0)
                    print("preload cnt", __EMSCRIPTEN__.counter )
                    __EMSCRIPTEN__.explore( sysconfig.get_paths()["platlib"] )
                    print("preload cnt", __EMSCRIPTEN__.counter )

            # init importer

            import sysconfig
            if not sysconfig.get_paths()["platlib"] in sys.path:
                sys.path.append(sysconfig.get_paths()["platlib"])


            if not len(cls.repos):
                async with platform.fopen(cdn / cls.repodata) as source:
                    cls.repos.append( json.loads(source.read()) )

            # print(json.dumps(cls.repo[0]["packages"], sort_keys=True, indent=4))
            print("packages :", len( cls.repos[0]["packages"] ) )

            await pkg_install(*imports(*wanted))




    def fix_url(maybe_url):
        url = str(maybe_url)
        if url.startswith('http://'):
            pass
        elif url.startswith('https://'):
            pass
        elif url.startswith('https:/'):
            url = "https:/"+ url[6:]
        elif url.startswith('http:/'):
            url = "http:/"+ url[5:]
        return url

    __EMSCRIPTEN__.fix_url = fix_url

    del fix_url

    def apply_patches():

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

        def browser_open_file(target=None,accept="*"):
            if target:
                platform.EventTarget.addEventListener("upload", target)
            platform.window.dlg_multifile.click()

        webbrowser.open_file = browser_open_file

        # merge emscripten browser module here ?
        # https://rdb.name/panda3d-webgl.md.html#supplementalmodules/asynchronousloading
        #



        # bad and deprecated use of sync XHR

        import urllib
        import urllib.request

        def urlretrieve(maybe_url, filename=None, reporthook=None, data=None):
            url = __EMSCRIPTEN__.fix_url(maybe_url)
            filename = filename or f"/tmp/uru-{aio.ticks}"
            rc=platform.window.python.DEPRECATED_wget_sync(str(url), str(filename))
            if rc==200:
                return filename, []
            raise Exception(f"urlib.error {rc}")


        urllib.request.urlretrieve = urlretrieve

    if (__WASM__ and __EMSCRIPTEN__) or platform.is_browser:
        from platform import window, document


        class fopen:
            ticks = 0
            def __init__(self, maybe_url, mode ="r"):
                self.url = __EMSCRIPTEN__.fix_url(maybe_url)
                self.mode = mode
                self.tmpfile = None

            async def __aenter__(self):
                import platform
                print(f'572: Download start: "{self.url}"')
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
                        with open(target,"wb") as data:
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
            mark =None
            value = undefined
            while mark!=undefined:
                value = mark
                await asyncio.sleep(0)
                mark = next( iterator, undefined )
            return value
        platform.jsiter = jsiter

        async def jsprom(prom):
            mark = None
            value = undefined
            wit = window.iterator( prom )
            while mark!=undefined:
                value = mark
                await aio.sleep(0)
                mark = next( wit , undefined )
            return value
        platform.jsprom = jsprom

        apply_patches()

    del apply_patches
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

if os.path.isfile('/data/data/usersite.py'):
    execfile('/data/data/usersite.py')

import aio.recycle
# ============================================================
# DO NOT ADD ANYTHING FROM HERE OR APP RECYCLING WILL TRASH IT





#
