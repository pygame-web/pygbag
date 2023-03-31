import sys
import os
import asyncio
import platform
import json
import warnings
import shutil

from pathlib import Path
from urllib.parse import urlencode

preload_list = []
preloaded = []


def FS(tree, silent=False, debug=True):
    global preload_list

    target = [""]
    path = [""]

    base_url = ""
    base_path = ""

    last = 0
    trail = False

    def make_src_dst(base_url, path, target):
        global preload_list
        nonlocal debug
        dst = target.copy()
        dst.extend(path[1:])

        preload_list.append([base_url + "/".join(path), "/".join(dst)])
        if debug:
            print(preload_list[-1], "write", current, last)

    for l in map(str.rstrip, tree.split("\n")):
        # skip blanks
        if not l:
            continue

        # skip root of tree, use current url as base_url
        if l == ".":
            preload_list.append(["", "."])
            continue

        if l.find(" ~") > 0:
            # reset source
            path = [""]

            base_path, trail = map(str.strip, l.split("~", 1))

            # set destination
            target = [trail]
            if debug:
                print(base_path, target)
            continue

        if l.startswith("http"):
            # found a base url
            base_url = l
            if base_url.find("/github.com/") > 0:
                base_url = base_url.replace("/github.com/", "/raw.githubusercontent.com/", 1)

            if base_url.find("/tree/") > 0:
                base_url = base_url.replace("/tree/", "/", 1)

            base_url = base_url.rstrip("/") + "/"

            if not silent:
                print("HTMLFS:", base_url, base_path, "=>", target)

            preload_list.append([base_url, "."])
            continue

        pos, elem = l.rsplit(" ", 1)
        current = (1 + len(pos)) // 4

        if not silent:
            print(l[4:])

        if current <= last:
            make_src_dst(base_path, path, target)
            while len(path) > current:
                path.pop()
        else:
            trail = True

        if debug:
            print(f"{pos=} {elem=} {current=} {path=} {last=}")
        if len(path) < current + 1:
            path.append(elem)
        path[current] = elem
        last = current

    if trail:
        make_src_dst(base_path, path, target)
    print("-" * 80)
    for x in preload_list:
        print(x)
    print("-" * 80)
    return preload_list


async def preload(chroot=None, chdir=True, silent=True, debug=False, standalone=False):
    global preload_list, preloaded

    # if not using FS, do not change directory
    if not len(preload_list):
        return

    cwd = Path.cwd()

    # if using FS, always go to tempdir
    if chroot is None:
        chroot = __import__("tempfile").gettempdir()

    target = Path(chroot)

    base_url = ""
    fileset = []

    while len(preload_list):
        url, strfilename = preload_list.pop(0)
        filename = target / strfilename

        if strfilename == ".":
            base_url = url
            if debug:
                print("{base_url=} set")
            continue

        if debug:
            print(f"{base_url=}{url=} => {filename=}")

        if not filename.is_file():
            filename.parent.mkdir(parents=True, exist_ok=True)
            if sys.platform in ("emscripten", "wasi"):
                async with platform.fopen(url, "rb") as source:
                    with open(filename, "wb") as destination:
                        destination.write(source.read())
            else:
                localfile = Path(cwd.as_posix() + "/" + url)
                if localfile.is_file():
                    if debug:
                        print(f"GET {localfile=} {chroot=} {filename=}")
                    shutil.copy(localfile, filename)
                else:
                    warnings.warn(f"{localfile=} not found")

        fileset.append(filename)

        if not silent:
            print("FS:", filename)

    preloaded.extend(fileset)

    if chdir:
        os.chdir(chroot)

    if standalone:
        return fileset

    await asyncio.sleep(0)
    return preloaded.copy()


class RequestHandler:
    """
    WASM compatible request handler
    auto-detects emscripten environment and sends requests using JavaScript Fetch API
    """

    GET = "GET"
    POST = "POST"
    _js_code = ""
    _init = False

    def __init__(self):
        self.is_emscripten = sys.platform == "emscripten"
        if not self._init:
            self.init()
        self.debug = True
        self.result = None
        if not self.is_emscripten:
            try:
                import requests

                self.requests = requests
            except ImportError:
                pass

    def init(self):
        if self.is_emscripten:
            self._js_code = """
window.Fetch = {}

// generator functions for async fetch API
// script is meant to be run at runtime in an emscripten environment

// Fetch API allows data to be posted along with a POST request
window.Fetch.POST = function * POST (url, data)
{
    // post info about the request
    console.log("POST: " + url + "\nData: " + data);
    // add headers for POST accept: application/json
    var request = new Request(url, {headers: {'Accept': 'application/json','Content-Type': 'application/json'},
        method: 'POST', 
        body: JSON.stringify(data)});
    var content = 'undefined';
    fetch(request)
   .then(resp => resp.text())
   .then((resp) => {
        console.log(resp);
        content = resp;
   })
   .catch(err => {
         // handle errors
         console.log("An Error Occurred:")
         console.log(err);
    });

    while(content == 'undefined'){
        yield content;
    }
}

// Only URL to be passed
// when called from python code, use urllib.parse.urlencode to get the query string
window.Fetch.GET = function * GET (url)
{
    console.log("GET: " + url);
    var request = new Request(url, { method: 'GET' })
    var content = 'undefined';
    fetch(request)
   .then(resp => resp.text())
   .then((resp) => {
        console.log(resp);
        content = resp;
   })
   .catch(err => {
         // handle errors
         console.log("An Error Occurred:");
         console.log(err);
    });

    while(content == 'undefined'){
        // generator
        yield content;
    }
}
            """
            try:
                platform.window.eval(self._js_code)
            except AttributeError:
                self.is_emscripten = False

    @staticmethod
    def read_file(file):
        # synchronous reading of file intended for evaluating on initialization
        # use async functions during runtime
        with open(file, "r") as f:
            data = f.read()
        return data

    @staticmethod
    def print(*args, default=True):
        try:
            for i in args:
                platform.window.console.log(i)
        except AttributeError:
            pass
        except Exception as e:
            return e
        if default:
            print(*args)

    async def get(self, url, params=None, doseq=False):
        # await asyncio.sleep(5)
        if params is None:
            params = {}
        if self.is_emscripten:
            query_string = urlencode(params, doseq=doseq)
            await asyncio.sleep(0)
            content = await platform.jsiter(platform.window.Fetch.GET(url + "?" + query_string))
            if self.debug:
                self.print(content)
            self.result = content
        else:
            self.result = self.requests.get(url, params).text
        return self.result

    # def get(self, url, params=None, doseq=False):
    #     return await self._get(url, params, doseq)

    async def post(self, url, data=None):
        if data is None:
            data = {}
        if self.is_emscripten:
            await asyncio.sleep(0)
            content = await platform.jsiter(platform.window.Fetch.POST(url, json.dumps(data)))
            if self.debug:
                self.print(content)
            self.result = content
        else:
            self.result = self.requests.post(url, data).text
        return self.result

    # def post(self, url, data=None):
    #     return await self._post(url, data)
