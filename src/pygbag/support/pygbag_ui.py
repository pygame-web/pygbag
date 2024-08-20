import asyncio
import sys


out = sys.__stdout__.write

import os

# for Rich color output
os.environ["FORCE_COLOR"] = "1"
damages = {}
evpos = {}
clog = []


import select
import os

try:
    from _xterm_parser.events import MouseEvent, Key
except:
    print("using readline event parser")

buffer_console = []

# import shutil
import os

import readline


class TTY:
    stdin = 0
    closed = False

    COLUMNS, _ = os.get_terminal_size()
    LINES = 25

    try:
        CONSOLE = platform.get_console_size()
    except:
        CONSOLE = 32 - LINES

    echo = True
    console = True

    prompts = []

    # TODO: multi line editor
    rl_complete = []
    rl_instances = []
    rl_instances.append(readline.readline())
    rl_instances[-1].reset()
    rl_pointer = len(rl_instances) - 1

    readline_buffer = []

    line = ""

    # cursor pos
    L = 1
    C = 1

    raw = b""

    event_type = ""
    last_event_type = "load"

    event_data = ""
    last_event_data = "window"

    last_state = False

    def __init__(*self):
        raise Exception("not for instancing")

    # @classmethod
    def get_readline():
        self = TTY
        return self.rl_instances[self.rl_pointer]

    # @classmethod
    def prompt():
        self = TTY
        if self.raw:
            rl = self.get_readline()
            rl.process_bstr(TTY.raw)
            self.raw = b""
            print(f"\r>>> {rl.string}\x1b[K\r\x1b[{4+rl.caret}C", end="")
            if rl.string and (rl.string[-1] == "\n"):
                print(end="\r")
                self.rl_complete.append(rl.string.rstrip("\r\n"))
                rl.reset()
                self.prompts.append(1)

    def do_prompt(force=False):
        self = TTY
        if len(self.prompts) or force:
            self.prompts.clear()
            print("\r>>> ", end=sys.__eot__)
            self.flush()

    # @classmethod
    def set_raw(state):
        self = TTY
        import platform
        import termios, tty

        if state:
            stdin = sys.stdin.fileno()
            self.stdin = stdin

            ESC("7")

            self.attrs_before = termios.tcgetattr(stdin)
            attrs_raw = termios.tcgetattr(stdin)
            attrs_raw[tty.LFLAG] &= ~(termios.ECHO | termios.ICANON | termios.IEXTEN | termios.ISIG)
            attrs_raw[tty.IFLAG] &= ~(termios.IXON | termios.IXOFF | termios.ICRNL | termios.INLCR | termios.IGNCR)
            attrs_raw[tty.CC][termios.VMIN] = 1

            # keyb
            termios.tcsetattr(stdin, termios.TCSANOW, attrs_raw)

            # mouse
            CSI("?1000h", "?1003h", "?1015h", "?1006h")

            try:
                # platform.window.set_raw_mode(1)
                ...
            except:
                ...
        else:
            try:
                platform.window.set_raw_mode(0)
            except:
                ...

            CSI("?1000l", "?1003l", "?1015l", "?1006l")

            try:
                termios.tcsetattr(self.stdin, termios.TCSANOW, self.attrs_before)
            except:
                ...

            # get back full scrolling
            CSI("999;999r")
            # restore cur+attr
            ESC("8")

    if sys.platform in ("emscripten", "wasi") and not aio.cross.simulator:
        flush = __import__("embed").flush
    else:
        flush = sys.__stdout__.flush

    # @classmethod
    def handler_console_input(ev):
        self = TTY
        global clog
        if ev.is_printable:
            if self.echo:
                print(ev.character, end="")
                sys.__stdout__.flush()
            buffer_console.append(ev.character)

        elif ev.name == "enter":
            # stdin console injection. bypass embed.readline() see pythonrc.py
            print(end="\r\n")
            aio.toplevel.handler.instance.buffer.append("".join(buffer_console))
            TTY.prompts.append(1)
            buffer_console.clear()

        elif ev.name == "ctrl_d":
            # aio.exit_now(0)
            self.closed = True
        elif ev.name == "ctrl_l":
            clear(LINES=-1, prompt=">-> ")
        else:
            # clog.append(repr(list(ev.__rich_repr__())))
            ...

    # @classmethod
    def handler_readline_input(ev):
        self = TTY
        global clog

        # virtual gamepad handler

        if not TTY.console:
            if ev.name in ("space"):
                import pygame

                uev = pygame.event.Event(pygame.USEREVENT + 2)
                pygame.event.post(uev)
                return False
            if ev.name in ("left", "right", "up", "down"):
                if ev.name == "left":
                    return vpad.emit(vpad.X, -1.0)

                if ev.name == "right":
                    return vpad.emit(vpad.X, 1.0)

                if ev.name == "up":
                    return vpad.emit(vpad.Z, 1.0)

                if ev.name == "down":
                    return vpad.emit(vpad.Z, -1.0)

        # await input() handler
        if ev.is_printable:
            self.readline_buffer.append(ev.character)
            return False

        # validate input()

        if ev.name == "enter":
            self.last_list = self.line
            self.line = "".join(self.readline_buffer)
            self.readline_buffer.clear()
            return True
        else:
            # clog.append(repr(list(ev.__rich_repr__())))
            ...
        return False

    # @classmethod
    def handler_events(ev):
        self = TTY
        global evpos

        for ez in range(ev.y - 1, ev.y + 2):
            if evpos.get(ez, None):
                for k in evpos[ez]:
                    if not len(evpos[ez][k]):
                        continue
                    # clog.append( repr( evpos[ez][k] ) )
                    for slot in evpos[ez][k]:
                        xl, xr, tag = slot
                        if (xl < ev.x) and (ev.x < xr):
                            if ev.button:
                                self.event_type = "click"
                            else:
                                self.event_type = "hover"
                            self.event_data = tag
                            return

    # @classmethod
    def input():
        self = TTY
        global clog, parser, buffer_console
        rl_complete = False
        if self.event_type:
            self.last_event_type = self.event_type

        if self.event_data:
            self.last_event_data = self.event_data

        self.event_type = ""
        self.event_data = ""
        self.state_changed = False

        self.raw = ""

        if select.select([self.stdin], [], [], 0)[0]:
            try:
                payload = os.read(self.stdin, 1024)
                if payload:
                    if not parser:
                        self.raw = payload
                        return self.raw.decode()

                    for event in parser.feed(payload.decode("utf-8")):
                        if isinstance(event, MouseEvent):
                            self.L = event.y
                            self.C = event.x
                            TTY.console = event.y > TTY.LINES
                            if self.last_state != TTY.console:
                                self.last_state = TTY.console
                                self.state_changed = True
                            # only last event will stay.
                            self.handler_events(event)

                        elif isinstance(event, Key):
                            if TTY.console:
                                # self.handler_console_input(event)
                                self.raw = payload
                            else:
                                rl_complete = self.handler_readline_input(event)
                                # clog.append( repr(list(event.__rich_repr__())) )
            except OSError:
                ...

        if rl_complete:
            return self.line
        return ""


def goto_xy(x, y):
    CSI(f"{y};{x}H")


# cleareos ED0          Clear screen from cursor down          ^[[J
# cleareos ED0          Clear screen from cursor down          ^[[0J
# clearbos ED1          Clear screen from cursor up            ^[[1J
# clearscreen ED2       Clear entire screen                    ^[[2J


def clear(LINES=0, CONSOLE=0, prompt=""):
    global damages

    TTY.LINES = max(TTY.LINES, LINES)

    TTY.CONSOLE = max(TTY.CONSOLE, CONSOLE)

    if CONSOLE > 0:
        # damage whole zone
        for x in damages:
            damages[x] = 0
            if x > TTY.LINES:
                break

        goto_xy(1, TTY.LINES + 1)
        CSI("0J", "1J", f"{TTY.LINES+1};{TTY.LINES+TTY.CONSOLE}r", f"{TTY.LINES+TTY.CONSOLE-1};1H{prompt}")

    elif CONSOLE < 0:
        goto_xy(1, TTY.LINES + 1)
        CSI(f"0J", f"{TTY.LINES+1};1H{prompt}")
    else:
        # damage whole screen
        for x in damages:
            damages[x] = 0
        # clear all events
        evpos.clear()
        CSI("2J")


import sys

try:
    import re

    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
except:

    class ansi_escape:
        def sub(self, sb, line):
            return line

    ansi_escape = ansi_escape()


bname_last = 0
anchor_last = 0


# https://stackoverflow.com/questions/14693701/how-can-i-remove-the-ansi-escape-sequences-from-a-string-in-python
try:
    from _xterm_parser import XTermParser

    def more_data() -> bool:
        return False

    parser = XTermParser(more_data)
    PKPY = False
except:
    PKPY = True
    parser = False


def filter_in(data):
    global parser
    for event in parser.feed(data):
        clog.append(repr(event))


def filter_out(row, x, y, z):
    global clog, ansi_escape, bname_last, anchor_last
    ev = evpos[y][hash(row)]

    if row.find(":>") >= 0:
        if PKPY:
            flt = re.sub(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])", "", row)
        else:
            flt = ansi_escape.sub("", row)

        len_flt = len(flt)
        while flt.find(":>") > 0:
            anchor, trail = flt.split(":>", 1)
            anchor, bname = anchor.split("<:", 1)
            if len(ev):
                posx = ev[-1][1] + anchor_last + bname_last + len(anchor)
                ev[-1][1] = posx
            else:
                posx = x

            if trail.find("<:") < 0:
                xl = x + len_flt - len(bname) - len(trail) - 4
                xr = x + len_flt - 1
                ev.append([xl, xr, bname])
                # clog.append(f"<{len(anchor)=}:{bname=} {ev=}>")
                break

            anchor_last = len(anchor)
            bname_last = len(bname) + 4

            # clog.append(f"<{len(anchor)=}:{bname=} {ev=}>")

            ev.append([posx - 1, posx, bname])
            flt = trail

        # FIXME: assuming same size buttons
        # just dividing len_flt by number of buttons

        zone = len_flt // len(ev)
        for i, pos in enumerate(ev):
            pos[0] = x + i * zone
            pos[1] = x + (i + 1) * zone - 1

    return row.replace("<:", "[ ").replace(":>", " ]")


# DECSTBM—Set Top and Bottom Margins
# https://vt100.net/docs/vt510-rm/DECSTBM.html

# DECSLRM—Set Left and Right Margins
# This control function sets the left and right margins to define the scrolling region. DECSLRM only works when vertical split screen mode (DECLRMM) is set.
# https://vt100.net/docs/vt510-rm/DECSLRM.html


class Tui:
    # use direct access, it is absolute addressing on raw terminal.
    out = out
    decvssm = False

    # save cursor
    def __enter__(self):
        # ESC("7","[?25l","[?69h")
        #        self.out("\x1b7\x1b[?25l\x1b[?69h")
        self.out("\x1b7")
        #        self.out("\x1b7\x1b[?25l")
        return self

    # restore cursor
    def __exit__(self, *tb):
        # ESC("[?69l","8","[?25h")
        #        self.out("\x1b[?69l\x1b8\x1b[?25h")
        self.out("\x1b8")
        #        self.out("\x1b8\x1b[?25h")
        pass

    def __call__(self, *a, **kw):
        global bname_last, anchor_last

        x = kw.get("x", 1)
        y = kw.get("y", 1)

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
            hr_old = damages.get(y, 0)
            hr = hash(row)
            if hr != hr_old:
                damages[y] = hr
                if filter:
                    # destroy event list ref by the old line
                    evpos.setdefault(y, {}).pop(hr_old, None)
                    evpos[y][hr] = []
                    row = filter(row, x, y, 0)

                self.out("\x1b[{};{}H{}".format(y, x, row))

            y += 1


# https://www.panda3d.org/reference/cxx/coordinateSystem_8h_source.html
# renderman CS_yup_left,  // Y-Up, Left-handed
# https://www.evl.uic.edu/ralph/508S98/coordinates.html


#
## slots = 'x y z t width depth height event'
## slots = slots.split(' ')
#
# X = const(0)
# Y = const(1)
# Z = const(2)
#
## T = const(3)
## W = const(4)
## D = const(5)
## H = const(6)
## E = const(7)
#
#
# class NodePath:
#    root = None
#    count = 0
#
#    def __init__(self, parent, node, pos=None, **kw):
#        if parent:
#            assert isinstance(parent, NodePath)
#        # FIXME: self.parent = weakref.ref(parent) <= no weakref yet in micropython
#        self.parent = parent
#        self.node = node
#        self.pos = pos or [0, 0, 0]
#        #self.name = kw.pop("name", "n_{0:03d}".format(NodePath.count, 3))
#        self.name = kw.pop("name", "n_{0}".format(str(NodePath.count).zfill(3)))
#        self.dirty = False
#        self.children = []
#        NodePath.count += 1
#
#        if parent:  # and self.root!=parent:
#            if not self in parent.children:
#                parent.children.append(self)
#
#
# def npos(n):
#    if isinstance(n, NodePath):
#        return n.pos
#    return n
#
#
# def get_x(n):
#    return npos(n)[X]
#
# def get_y(n):
#    return npos(n)[Y]
#
# def get_z(n):
#    return npos(n)[Z]
#
#
# def set_any(np, v, slot):
#    global rd
#    v = int(v)
#    ov = npos(np)[slot]
#    npos(np)[slot] = v
#    if isinstance(np, NodePath) and v != ov:
#        render.dirty = np.dirty = True
#
#
# def set_x(n, v):
#    set_any(n, v, X)
#
# def set_y(n, v):
#    set_any(n, v, Y)
#
# def set_z(n, v):
#    set_any(n, v, Z)
#
#
# def set_text(np, t):
#    t = str(t)
#    ot = np.node.text
#    if ot != t:
#        np.node.text = t
#        render.dirty = np.dirty = True


# class Node:
#    def __init__(self, text=None, **kw):
#        self.text = text
#        self.set_filter(lambda x: x)
#        self.clip = False
#
#    def set_filter(self, flt):
#        self.flt = flt
#
#    def filter(self, np):
#        return self.flt(self.text)
#
#
# class render(NodePath):
#    DX = const(1)
#    DZ = const(40)
#
#    IX = const(1)
#    IZ = const(-1)
#
#    # wr0 = '\x1b%d\x1b[?25%s'
#    # wr = sys.stdout.write
#    @classmethod
#    def wr(cls, data):
#        print(data, end="")
#
#    def __init__(self):
#        self.__class__.root = self
#        self.dirty = False
#        NodePath.__init__(self, None, self)
#
#    def __enter__(self):
#        # self.wr(self.wr0 % ( 7 , 'l' ) )
#        self.wr("\x1b7\x1b[?25l")
#        return self
#
#    def __exit__(self, *tb):
#        # self.wr( self.wr0 % ( 8, 'h' ) )
#        self.wr("\x1b8\x1b[?25h")
#
#    @classmethod
#    def draw_child(cls, parent, np, lvl):
#        pos = npos(np)
#        x = cls.DX + (cls.IX * pos[0])
#        z = cls.DZ + (cls.IZ * pos[2])
#        cls.wr(f"\x1b[{z};{x}H[ {np.name}: {np.node.text} ]  ")
#
#
# render = render()


# async def taskMgr(t=1.0 / 24):
#    import asyncio
#
#    global render
#    while True:
#        if render.dirty:
#            with render:
#                for child in render.children:
#                    render.draw_child(render, child, 0)
#            render.dirty = False
#            # flush_io() #DLE_ETX is sent for emscripten
#        await asyncio.sleep(0)
