import embed
import builtins


#=========================== os ===============================

# import os
# split/rsplit fix from c++
# os.environ {} is filled from c++

def os_read(fd, sz):
    return embed.os_read()
os.read = os_read
del os_read


def os_get_terminal_size(fd=0):
    cols = os.environ.get("COLUMNS", 80)
    lines = os.environ.get("LINES", 25)
    try:
        res = (
            int(cols),
            int(lines),
        )
    except:
        res = (
            80,
            25,
        )
    return os.terminal_size(res)

os.terminal_size = tuple
os.get_terminal_size = os_get_terminal_size
del os_get_terminal_size


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



#=========================== sys ===============================

import sys
sys.path = []
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

import embed
def embed_flush():
    sys.__stdout__.write(sys.__eot__)
embed.flush = embed_flush
del embed_flush



def ESC(*argv):
    for arg in argv:
        sys.__stdout__.write(chr(0x1B))
        sys.__stdout__.write(arg)
    sys.__stdout__.write(sys.__eot__)

def CSI(*argv):
    for arg in argv:
        ESC(f"[{arg}")

builtins.ESC = ESC
builtins.CSI = CSI



def new_module(name, code):
    if len(code)<40:
        with open(code,'r') as source:
            code=source.read()
    else:
        code = code.replace('\\\n','')
    embed._new_module(name, code)
    return __import__(name)


embed.new_module = new_module
del new_module


def compile(source, filename, mode, flags=0, dont_inherit=False, optimize=-1, _feature_version=-1):
    return source
builtins.compile = compile
del compile






#=========================== io ===============================

import io
class StringIO:
    counter = 0
    def __init__(self, initial_value='', newline='\n'):
        self.__class__.counter = 1+ self.__class__.counter
        file = f"/tmp/io_{str(self.__class__.counter).zfill(5)}.tmp"
        mode='w+'
        closefd=True
        opener=None
        self.fio = open(file,mode)

    def seek(self, p):
        self.fio.seek(p)
        #self.fio.rewind()

    def write(self, s):
        self.fio.write(s)

    def read(self): #, size=-1):
        return self.fio.read()

    def close(self):
        self.fio.close()

io.StringIO = StringIO
del StringIO

#=======================  platform ==================================



embed.new_module("platform", '''
#__UPY__ = False
#__CPY__ = False
CONSOLE = 25


import embed
stdin_select = embed.stdin_select

import os

def get_console_size(fd=0):
    global CONSOLE
    console = os.environ.get("CONSOLE", CONSOLE)
    try:
        return int(console)
    except:
        return int(CONSOLE)

import json
import embed



class ProxyType(object):

    def __init__(self, parent, *callpath, **env):
        self.__name = callpath[0]
        self.__parent = parent
        self.__callpath = callpath
        self.__return = None
        self.__value = None

        #print(f"Registered proxy : {parent}.{'.'.join(callpath)}")
        VM.callerid[id(self)] = self


    def __call__(self, *arguments, **options):
        # print("__call__",self.__callpath, arguments, options)

        VM.serial = VM.serial + 1
        callid = f"C{VM.serial}"

        fn = ".".join(self.__callpath)
        stack: list = [callid, self.__callpath]

        if len(arguments):
            stack.extend(arguments)
        if options:
            stack.append(options)
        args = tuple(stack[2:])
        embed.jseval(f"{fn}{args}")

    def __setattr(self, self_id, attr, line):
        #print(self,"__setattr", self_id, attr, line, self.__value)
        VM.serial = VM.serial + 1
        callid = f"C{VM.serial}"
        path = ".".join(self.__callpath)
        jsdata = json.dumps(self.__value)
        jscmd = f"{path}.{attr}=JSON.parse(`{jsdata}`)"
#        if self.__callpath[0] == 'document':
#            print("__setattr", self.__callpath, attr, line, jsdata)
#            print(jscmd)
        embed.jseval(jscmd)

    def __str__(self):
        if len(self.__callpath):
            descr = ".".join(self.__callpath)
            if len(self.__callpath) > 1:
                descr = str(embed.jseval(f"{descr}"))
        else:
            descr = f"[Object {descr}]"
        return descr

    def __repr__(self):
        return f"[ProxyType {self.__parent}.{'.'.join(self.__callpath)}]"

#    if not __PKPY__:

#        def __all(self, *argv, **env):
#            VM.serial += 1
#            return self.__call__(f"C{VM.serial}", self.__lastc, *argv, **env)

#        def __getattr__(self, attr):
#            if not len(self.__callpath):
#                VM.serial = VM.serial + 1
#                self.__callpath.append(f"C{VM.serial}")
#                self.__callpath.append(self.__dlref)
#            self.__callpath.append(attr)
#            return self

VM.ProxyType = ProxyType


window = ProxyType("Window", "window")
document = ProxyType("Window", "document")


try:
    import readline
except:
    print("readline module not found")

################################################################################
''')

import platform



embed.new_module("asyncio", '''
self = __import__(__name__)

from time import time as time_time

perf_index = None
enter = time_time()
spent = 0.00001
leave = enter + spent


load_avg = "0.000"
load_min = "0.000"
load_max = "0.000"

started = False
paused = False
exit = False
steps = []
oneshots = []
ticks = 0
protect = []
last_state = None
tasks = []
is_async_ctx = False
no_exit = True


class cross:
    simulator = False


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
                if iter_next(task) is StopIteration:
                    self.tasks.remove(task)
                frame += 1
                yield frame

else:
    frame : int = 0 #390540

    def step():
        global frame
        for task in self.tasks:
            if iter_next(task) is StopIteration:
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

builtins.aio = asyncio


aio.prepro = embed.new_module("aio.prepro", '''
import builtins
defines = {}

def defined(plat):
    try:
        return eval(plat) or True
    except:
        return False


def define(tag, value):
    global defines, DEBUG
    if DEBUG:
        import inspect

        lf = inspect.currentframe().f_back
        fn = inspect.getframeinfo(lf).filename.rsplit("/assets/", 1)[-1]
        ln = lf.f_lineno
        info = f"{fn}:{ln}"
        defines.setdefault(tag, info)
    else:
        info = "?:?"

    redef = defined(tag)
    if redef:
        if redef is value:
            pdb(f"INFO: {tag} redefined from {defines.get(tag)} at {info}")
            pass
        else:
            pdb(f"""WARNING: {tag} was already defined
    previous {defines.get(tag)} value {redef}
    new {info} value {value}

"""
            )

    setattr(builtins, tag, value)


builtins.define = define
builtins.defined = defined
''')



embed.new_module("select", '''
import platform

def select(rlist, wlist, xlist, timeout=None):
    # stdin
    if not isinstance(rlist, set):
        if rlist[0] == 0:
            return [platform.stdin_select()]



###############################################################################
''')

import select


def shelltry(*cmd):
    if hasattr(shell, cmd[0] ):
        rv = getattr(shell, cmd[0])(*cmd[1:])
        if rv is not None:
            for line in rv:
                print(line)
        return False
    return True



out = sys.__stdout__.write
damages = {}
bname_last = 0
anchor_last = 0

class Tui:
    # use direct access, it is absolute addressing on raw terminal.
#    out = out
    decvssm = False

    # save cursor
    def __enter__(self):
        # ESC("7","[?25l","[?69h")
        #        self.out("\x1b7\x1b[?25l\x1b[?69h")
        out("\x1b7")
        #        self.out("\x1b7\x1b[?25l")
        return self

    # restore cursor
    def __exit__(self, *tb):
        # ESC("[?69l","8","[?25h")
        #        self.out("\x1b[?69l\x1b8\x1b[?25h")
        out("\x1b8")
        out(sys.__eot__)
        #        self.out("\x1b8\x1b[?25h")
        pass

    def __call__(self, *a, **kw):
        global bname_last, anchor_last

        x :int = kw.get("x", 1)
        z :int = kw.get("z", 1)

        #   most term do not deal properly with vt400
        #            if decvssm:
        #                CSI(f"{x};{999}s")
        #                CSI(f"{z};{x}H\r")

        if not isinstance(a[0], str):
            import rich, io

            sio = io.StringIO()
            rich.print(*a, file=sio)
            sio.seek(0)
            block = sio.read()
        else:
            block = " ".join(a)

        # so position line by line
        filter = kw.get("filter", None)

        bname_last = 0
        anchor_last = 0

        for row in block.split("\n"):
            hr_old = damages.get(z, 0)
            hr = hash(row)
            if hr != hr_old:
                damages[z] = hr
                if filter:
                    # destroy event list ref by the old line
                    evpos.setdefault(z, {}).pop(hr_old, None)
                    evpos[z][hr] = []
                    row = filter(row, x, 0, z)

                #Tui.out("\x1b[{};{}H{}".format(z, x, row))
                sys.__stdout__.write(f"\x1b[{z};{x}H{row}")

            z += 1




from platform import window, document


document.body.style.background = "#555555"
window.document.body.style.background = "#000000"


from pygbag_ui import TTY, clear, goto_xy

def main():
    line = "\n"
    tui = Tui()



    _, LINES = os.get_terminal_size()
    CONSOLE = platform.get_console_size()

    CSI("2J","f")
    clear(LINES, CONSOLE)
    with open("pkpy.six","r") as source:
        print(source.read())


    print(f"Python {sys.version} PocketPy::pykpocket edition on Emscripten", '.'.join(map(str, sys._emscripten_info)))

    from platform import window, document

    window.set_raw_mode(1)

    raw : int = 0

    goto_xy(1, TTY.LINES + TTY.CONSOLE )

    TTY.do_prompt(force=True)


    while line not in ["exit()","quit()"]:

        if not line:
            if select.select([TTY.stdin], [], [], 0)[0]:
                TTY.raw = os.read(TTY.stdin, 1024)
            TTY.prompt()

            # result from readline line by line
            if TTY.rl_complete:
                line = TTY.rl_complete.pop(0)

        if not asyncio.frame % 60:
            document.title = f"Frame={asyncio.frame}"

        with tui as out:
            fsm=None
            out( f"""{TTY.COLUMNS}x({TTY.LINES}+{TTY.CONSOLE}):{TTY.console}\
 fsm={fsm and fsm.state} C={TTY.C} L={TTY.L}\
 min/avg/max:{aio.load_min} {aio.load_avg} {aio.load_max}\
  ⏏︎ ■ ▶\
 {TTY.last_event_type}({TTY.last_event_data})  Frame={asyncio.frame}\
                      """, x=1, z=TTY.LINES)

        # line is either
        # - embed.readline (input/external readline)
        # - console (raw tty/py readline emulation)

        if line:
            line = line.rstrip()
            fail = False
            if line:
                try:
                    _=eval(line)
                    if _ is not None:
#                        if instance(_, platform.ProxyType):
#                            print(repr(_))
#                        else:
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
            TTY.do_prompt()
        yield 0
        line = embed.readline()
        raw = embed.stdin_select()

    print("bye")



asyncio.get_running_loop().create_task(main())


pkpyrc = 1

