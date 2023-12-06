import sys

if sys.platform not in ('emscripten','wasi') or aio.cross.simulator:
    sleep_delay = 0
else:
    sleep_delay = 0.0155



from pygbag_ui import Tui, TTY
import pygbag_ui as ui
from pygbag_ux import *

ux_dim(1280 // 2 , 720 // 2)


class vpad:
    X = 0
    Z = 1
    Y = 2
    evx = []
    evy = []
    evz = []
    axis = [evx, evz, evy]

    LZ = 0.5

    @classmethod
    def get_axis(self, n):
        if len(self.axis[n]):
            return self.axis[n].pop(0)
        return 0.0

    @classmethod
    def emit(self, axis, value):
        import pygame
        self.axis[axis].append(float(value))
        ev = pygame.event.Event(pygame.JOYAXISMOTION)
        pygame.event.post(ev)
        return False




def console():
    import platform
    try:
        platform.window.pyconsole.hidden = False
        platform.window.document.body.style.background = "#000000";
    except:
        ...

    import os
    _, LINES = os.get_terminal_size()
    CONSOLE = os.get_console_size()

    # split the display
    if sys.platform not in ('emscripten','wasi') or aio.cross.simulator:
        LINES = LINES - CONSOLE

    ui.TTY.set_raw(1)
    import select,os,platform

    platform.shell.is_interactive = False
    platform.shell.interactive(True)
    aio.toplevel.handler.muted = False

    ui.clear(LINES, CONSOLE, '>>> ')


