#!pythonrc.py

import os, sys, json, builtins

# to be able to access aio.cross.simulator
import aio
import aio.cross


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

        with __import__("tokenize").open(filename) as f:
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
            __main__dict["__file__"] = filename
            try:
                code = compile("".join(__prepro), filename, "exec")
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
        if aio.cross.simulator:
            ROOT = os.getcwd()
            HOME = os.getcwd()
        else:
            ROOT = f"/data/data/{sys.argv[0]}"
            HOME = f"/data/data/{sys.argv[0]}/assets"

        @classmethod
        def cat(cls, *argv):
            for fn in argv:
                with open(fn, "r") as out:
                    print(out.read())

        @classmethod
        def ls(cls, *argv):
            if not len(argv):
                argv = ["."]
            for arg in argv:
                for out in os.listdir(arg):
                    print(out)

        @classmethod
        def clear(cls, *argv,**kw):
            import pygame
            screen = pygame.display.set_mode()
            screen.fill( (0, 0, 0) )
            pygame.display.update()

        @classmethod
        def display(cls,*argv,**kw):
            import pygame
            if not len(argv):
                surf = _
            else:
                if argv[-1].lower().endswith('bmp'):
                    surf = pygame.image.load_basic( argv[-1] )
                else:
                    surf = pygame.image.load( argv[-1] )

            screen = pygame.display.set_mode()
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
        def pwd(cls, *argv):
            print(os.getcwd())

        @classmethod
        def cd(cls, *argv):
            if len(argv):
                os.chdir(argv[-1])
            else:
                os.chdir(cls.HOME)
            print("[ ", os.getcwd(), " ]")

        @classmethod
        def exec(cls, cmd, *argv, **env):
            global pgzrun
            # TODO extract env from __main__ snapshot
            if cmd.endswith(".py"):
                if pgzrun:
                    print("a program is already running, using 'stop' cmd before retrying")
                    cls.stop()
                    pgzrun = None
                    aio.defer(cls.exec,(cmd,*argv),env, 500)

                else:
                    execfile(cmd)
                return True
            return False

        @classmethod
        def strace(cls, *argv, **env):
            import aio.trace

            sys.settrace(aio.trace.calls)
            return _process_args(argv, env)

        @classmethod
        def stop(cls, *argv, **env):
            global pgzrun
            aio.exit = True
            # pgzrun will reset to None next exec
            if not pgzrun:
                # pgzrun does its own cleanup call
                aio.defer(aio.recycle.cleanup, (), {}, 500)
                aio.defer(embed.prompt, (), {}, 800)

    def _process_args(argv, env):
        catch = True
        for cmd in argv:
            cmd = cmd.strip()
            if cmd.find(" ") > 0:
                cmd, args = cmd.split(" ", 1)
                args = args.split(" ")
            else:
                args = ()

            if hasattr(shell, cmd):
                try:
                    getattr(shell, cmd)(*args)
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
    aio.cross.simulator = (
        __EMSCRIPTEN__ or __wasi__ or __WASM__
    ).PyConfig_InitPythonConfig(PyConfig)
# except NameError:
except Exception as e:
    sys.print_exception(e)
    #   TODO: get a pyconfig from C here
    #    <vstinner> pmp-p: JSON au C : connais les API secrète
    # _PyConfig_FromDict(), _PyInterpreterState_SetConfig() et _testinternalcapi.set_config()?
    #    <vstinner> pmp-p: j'utilise du JSON pour les tests unitaires sur PyConfig dans test_embed

    PyConfig = {}
    print(" - running in simulator - ")
    aio.cross.simulator = True

# make simulations same each time, easier to debug
import random
random.seed(1)

# ======================================================

# import pygame
pgzrun = None

if __WASM__ and __EMSCRIPTEN__ and __EMSCRIPTEN__.is_browser:
    from __EMSCRIPTEN__ import window,document

    async def jsp(prom):
        mark = None
        value = undefined
        wit = window.iterator( prom )
        while mark!=undefined:
            value = mark
            await aio.sleep(0)
            mark = next( wit , undefined )
        return value
else:
    pdb("TODO: js sim")


import aio.recycle
# ============================================================
# DO NOT ADD ANYTHING FROM HERE OR APP RECYCLING WILL TRASH IT



#
