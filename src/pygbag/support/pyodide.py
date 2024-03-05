import os
os.environ['PYODIDE'] = "1"

import sys

import platform
sys.modules['js'] = platform
import js


class ffi:
    def create_proxy(self, fn):
        print(fn)
        return fn

ffi=ffi()

class m_pyodide:
    ffi=ffi

sys.modules["pyodide"] = m_pyodide()
del m_pyodide
import pyodide

class m_canvas:
    def getCanvas3D(self, name='canvas',width=1024,height=1024):
        canvas = platform.document.getElementById(name)
        canvas.width = width
        canvas.height = height
        return canvas

class m_pyodide_js:
    canvas = m_canvas()
    _module = platform.window

sys.modules["pyodide_js"] = m_pyodide_js()
del m_canvas
del m_pyodide_js
import pyodide_js


# fix pygbag bridge
def jseval(code:str):
    return platform.window.eval(code)

platform.eval = jseval
