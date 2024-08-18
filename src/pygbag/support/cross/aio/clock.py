import sys
import time
import asyncio
import os


class tui:
    # use direct access, it is absolute addressing on raw terminal.
    if 0:
        out = sys.__stdout__.write
    else:

        def out(self, *argv, **kw): ...

    try:
        LINES = int(os.environ.get("LINES", 200))
    except:
        LINES = 200

    # save cursor
    def __enter__(self):
        self.out("\x1b7", "\x1b[?25l")
        return self

    # restore cursor
    def __exit__(self, *tb):
        self.out("\x1b8", "\x1b[?25h")

    # TODO: limit buffer to LINES
    def __call__(self, *a, **kw):
        try:
            l = ctx()["io"][0]
            if len(l) > self.LINES:
                return
            l.append([kw.get("z", 1), kw.get("x", 1), " ".join(a)])
        except:
            ...

        # self.out("\x1b[{};{}H{}".format(, " ".join(a)))


def step(x=70, y=0, z=2):
    import time

    def box(t, x, y, z):
        lines = t.split("\n")
        fill = "─" * len(t)
        if z > 1:
            print("┌%s┐" % fill, x=x, z=z - 1)
        for t in lines:
            print("│%s│" % t, x=x, z=z)
            z += 1
        print("└%s┘\n" % fill, x=x, z=z)

    with tui() as print:
        # draw a clock
        t = "%02d:%02d:%02d ☢ 99%% " % time.localtime()[3:6]
        box(t, x=x, y=y, z=z)


async def clock(x=70, y=0, z=2):
    # run as a daemon
    while True:  # not asyncio.exit:
        step(x, y, z)
        await asyncio.sleep(1)
        sys.stdout.flush()


def start(x=70, y=0, z=2):
    asyncio.create_task(clock(x, y, z))
