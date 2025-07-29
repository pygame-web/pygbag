import os

os.environ["PYODIDE"] = "1"

import sys

import platform

sys.modules["js"] = platform.window.globalThis
import js


def jsa(*argv):
    return platform.window.JSON.parse(json.dumps(argv))

def jso(**kw):
    return platform.window.JSON.parse(json.dumps(kw))

class ffi:
    def create_proxy(self, fn):
        print(fn)
        return fn

    def JsArray(self, *it):
        return jsa(*it)
    def JsException(self, *argv, **kw):
        pass
    def JsProxy(self, *argv, **kw):
        pass

    def to_js(self, *argv, **kw):
        pass


ffi = ffi()


class m_pyodide:
    ffi = ffi


sys.modules["pyodide"] = m_pyodide()
sys.modules["pyodide.ffi"] = sys.modules["pyodide"].ffi
del m_pyodide
import pyodide


class m_canvas:
    def getCanvas3D(self, name="canvas", width=0, height=0):
        canvas = platform.document.getElementById(name)
        try:
            width = width or canvas.width
            height = height or canvas.height
            # print(f"canvas size was previously set to : {width=} x {height=}")
        except:
            pass
        canvas.width = width or 1024
        canvas.height = height or 1024
        return canvas


class m_pyodide_js:
    canvas = m_canvas()
    _module = platform.window


sys.modules["pyodide_js"] = m_pyodide_js()
del m_canvas
del m_pyodide_js
import pyodide_js


# fix pygbag bridge
def jseval(code: str):
    return platform.window.eval(code)


platform.eval = jseval
