print("pkpyrc")
import sys
import embed
import builtins
import embed
import os
# split/rsplit fix from c++
# os.environ {} is filled from c++

class shell:
    HOME = "/data/data/org.python/assets"
    def ls(path="."):
        for elem in os.listdir(path):
            yield elem

    def cd(path="~"):
        if path=="~":
            os.chdir(shell.HOME)
        else:
            os.chdir(path)

shell.cd()


if 0:
    __next__ = next
    def next(it, default=0xdeadbeef):
        itrv = __next__(it)
        if itrv == StopIteration:
            if default == 0xdeadbeef:
                raise itrv
            return default
        return itrv

    __import__('builtins').next = next



import sys
sys.modules = []
sys.orig_argv = []
sys.argv = []
sys.__eot__ = chr(4)+chr(10)
sys.__stdout__ = sys.stdout
sys.__stderr__ = sys.stderr

def print_exception(*argv, **kw):
    import traceback
    traceback.print_exc()

sys.print_exception = print_exception
del print_exception


def ESC(*argv):
    for arg in argv:
        sys.__stdout__.write(chr(0x1B))
        sys.__stdout__.write(arg)
    sys.__stdout__.write(sys.__eot__)

def CSI(*argv):
    for arg in argv:
        ESC(f"[{arg}")


CSI("2J","f")
with open("pkpy.six","r") as source:
    print(source.read())
print(f"Python {sys.version} PocketPy::pykpocket edition on Emscripten", '.'.join(map(str, sys._emscripten_info)))


def new_module(name, code):
    if len(code)<80:
        with open(code,'r') as source:
            code=source.read()

    embed._new_module(name, code)
    return __import__(name)


embed.new_module = new_module
del new_module


def compile(source, filename, mode, flags=0, dont_inherit=False, optimize=-1, _feature_version=-1):
    return source
builtins.compile = compile
del compile


embed.new_module("asyncio", '''
self = __import__(__name__)
tasks : list = []
loop : object = None

def create_task(task):
    self.tasks.append(task)

def get_event_loop():
    if self.loop is None:
        self.loop = self
    return self.loop

get_running_loop = get_event_loop

def is_closed():
    return len(self.tasks)==0

if 0:
    def iterloop():
        frame : int = 0
        while tasks:
            for task in self.tasks:
                if next(task) is StopIteration:
                    self.tasks.remove(task)
                frame += 1
                yield frame

    def step():
        for task in self.tasks:
            itrv = next(task, 0xfeedc0de)
            if itrv == 0xfeedc0de:
                self.tasks.remove(task)
else:
    frame : int = 0

    def step():
        global frame
        for task in self.tasks:
            if next(task) is StopIteration:
                self.tasks.remove(task)
        frame += 1


def run(task, block=None):
    tasks.append(task)

    if block is None:
        try:
            sys._emscripten_info
        except:
            block = True

    if not block:
        return
    while tasks:
        step()


''')

import asyncio



def shelltry(*cmd):
    if hasattr(shell, cmd[0] ):
        rv = getattr(shell, cmd[0])(*cmd[1:])
        if rv is not None:
            for line in rv:
                print(line)
        return False
    return True





def main():
    line = "\n"
    while line not in ["exit()","quit()"]:
        if line:
            line = line.rstrip()
            fail = False
            if line:
                try:
                    _=eval(line)
                    if _ is not None:
                        print(_)
                except NameError:
                    fail = shelltry(*line.split(" "))
                except SyntaxError:
                    try:
                        exec(line, globals())
                    except SyntaxError:
                        fail = shelltry(*line.split(" "))
                    except:
                        sys.print_exception()
                if fail:
                    sys.print_exception()
                print()
            print('>>> ',end=sys.__eot__)
        yield 0
        line = embed.readline()
    print("bye")


asyncio.get_running_loop().create_task(main())


pkpyrc = 1

