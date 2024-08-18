import sys

if sys.platform not in ("emscripten", "wasi") or aio.cross.simulator:
    sleep_delay = 0
else:
    sleep_delay = 0.0155


from pygbag_ui import Tui, TTY, clear

import pygbag_ui as ui
import pygbag_ux as ux

# ux.dim(1280 // 2 , 720 // 2)


class console:
    @classmethod
    def log(self, *argv, **kw):
        import io

        sio = io.StringIO()
        kw["file"] = sio
        print(*argv, **kw)
        ui.clog.append(sio.read())

    @classmethod
    def get(self):
        import platform

        try:
            platform.window.pyconsole.hidden = False
            platform.window.document.body.style.background = "#000000"
        except:
            ...

        import os

        _, LINES = os.get_terminal_size()
        CONSOLE = platform.get_console_size()

        # split the display
        if sys.platform not in ("emscripten", "wasi") or aio.cross.simulator:
            LINES = LINES - CONSOLE

        TTY.set_raw(1)

        platform.shell.is_interactive = False
        platform.shell.interactive(True)
        aio.toplevel.handler.muted = False

        clear(LINES, CONSOLE - 1)  # , '>C> ')
        return self


__ALL__ = [ui, ux]
