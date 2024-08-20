import sys
import os
import aio

# https://bugs.python.org/issue34616
# https://github.com/ipython/ipython/blob/320d21bf56804541b27deb488871e488eb96929f/IPython/core/interactiveshell.py#L121-L150

import asyncio
import ast
import types
import inspect

if not __UPY__:
    try:
        from . import repl
    except:
        repl = None

    import code

    class AsyncInteractiveConsole(code.InteractiveConsole):
        instance = None
        console = None
        # TODO: use PyConfig interactive flag
        muted = True

        def __init__(self, locals, **kw):
            super().__init__(locals)
            self.compile.compiler.flags |= ast.PyCF_ALLOW_TOP_LEVEL_AWAIT
            self.line = ""
            self.buffer = []
            self.one_liner = True
            self.opts = kw
            self.shell = self.opts.get("shell", None)

            if self.shell is None:

                class shell:
                    coro = []
                    is_interactive = None

                    @classmethod
                    def parse_sync(shell, line, **env):
                        print("NoOp shell", line)

                self.shell = shell

            self.rv = None

            try:
                sys.ps1
            except AttributeError:
                sys.ps1 = ">A> "

            try:
                sys.ps2
            except AttributeError:
                sys.ps2 = "--- "

        def runsource(self, source, filename="<stdin>", symbol="single"):
            if len(self.buffer) > 1:
                symbol = "exec"

            try:
                code = self.compile(source, filename, symbol)
            except SyntaxError:
                if self.one_liner:
                    if self.shell.parse_sync(self.line):
                        return
                self.showsyntaxerror(filename)
                return False

            except (OverflowError, ValueError):
                # Case 1
                self.showsyntaxerror(filename)
                return False

            if code is None:
                # Case 2
                return True

            # Case 3
            self.runcode(code)
            return False

        def runcode(self, code):
            if repl:
                repl.set_ps1()
            self.rv = undefined

            bc = types.FunctionType(code, self.locals)
            try:
                self.rv = bc()
            except SystemExit:
                aio.exit_now(0)

            except KeyboardInterrupt as ex:
                print(ex, file=sys.__stderr__)
                raise

            except ModuleNotFoundError as ex:
                want = str(ex).split("'")[1]
                print("189 : FIXME sync->async->sync import bytecode retry in non interactive")
                print(f'await aio.pep0723.pip_install("{want}");import {want}')

                async def import_now():
                    nonlocal want
                    await aio.pep0723.pip_install(want)
                    vars(__import__("__main__"))[want] = __import__(want)

                self.shell.coro.append(import_now())

            except BaseException as ex:
                if self.one_liner:
                    shell = self.opts.get("shell", None)
                    if shell:
                        # coro maybe be filled by shell exec
                        if shell.parse_sync(self.line):
                            return
                sys.print_exception(ex, limit=-1)

            finally:
                self.one_liner = True

        def banner(self):
            if self.muted:
                return
            cprt = 'Type "help", "copyright", "credits" or "license" for more information.'

            self.write("\nPython %s on %s\n%s\n" % (sys.version, sys.platform, cprt))

        def prompt(self, prompt=None):
            if not self.__class__.muted and self.shell.is_interactive:
                import platform

                # that is the browser one
                # platform.prompt(prompt or sys.ps1)
                if repl:
                    repl.prompt()

        async def input_console(self, prompt=">I> "):
            if len(self.buffer):
                return self.buffer.pop(0)

            # if program wants I/O do not empty buffers
            if self.shell.is_interactive:
                if repl and not aio.cross.simulator:
                    maybe = repl.readline()
                elif aio.async_input:
                    maybe = await aio.async_input()
                else:
                    maybe = ""

                if len(maybe):
                    return maybe
            return None

        # can be used to mix console and app
        async def interact_step(self, prompt=None):
            if aio.exit:
                return

            if prompt is None:
                prompt = sys.ps1

            try:
                try:
                    self.line = await self.input_console(prompt)
                    if self.line is None:
                        return

                except EOFError:
                    self.write("\n")
                    return
                else:
                    if self.push(self.line):
                        if self.one_liner:
                            prompt = sys.ps2
                            if repl:
                                repl.set_ps2()
                            print("Sorry, multi line input editing is not supported", file=sys.stderr)
                            self.one_liner = False
                            self.resetbuffer()
                        else:
                            return
                    else:
                        prompt = sys.ps1

            except KeyboardInterrupt:
                self.write("\nKeyboardInterrupt\n")
                self.resetbuffer()
                self.one_liner = True

            if aio.exit:
                return

            try:
                # if async prepare is required
                while len(self.shell.coro):
                    self.rv = await self.shell.coro.pop(0)

                # if self.rv not in [undefined, None, False, True]:
                if inspect.isawaitable(self.rv):
                    await self.rv
            except RuntimeError as re:
                if str(re).endswith("awaited coroutine"):
                    ...
                else:
                    sys.print_exception(ex)

            except Exception as ex:
                print(type(self.rv), self.rv)
                sys.print_exception(ex)

            self.prompt()

        async def interact(self):
            # in repl+raw mode we don't want that loop to read input
            import sys
            from platform import window

            while not aio.exit:
                await asyncio.sleep(0)
                if window.RAW_MODE:
                    continue
                await self.interact_step(sys.ps1)
            aio.exit_now(0)

        @classmethod
        def make_instance(cls, shell, ns="__main__"):
            cls.instance = cls(
                vars(__import__(ns)),
                shell=shell,
            )
            import platform

            platform.shell = shell
            shell.runner = cls.instance
            del AsyncInteractiveConsole.make_instance

        @classmethod
        def start_console(cls, shell, ns="__main__"):
            """will only start a console, not async import system"""
            if cls.instance is None:
                cls.make_instance(shell, ns)

            if cls.console is None:
                asyncio.create_task(cls.instance.interact())
                cls.console = cls.instance

        @classmethod
        async def start_toplevel(cls, shell, console=True, ns="__main__"):
            """start async import system with optionnal async console"""
            if cls.instance is None:
                cls.make_instance(shell, ns)
                # await cls.instance.async_repos()

            if console:
                cls.start_console(shell, ns=ns)

else:
    # TODO upy event driven async repl

    class AsyncInteractiveConsole: ...
