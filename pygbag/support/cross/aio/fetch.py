import sys
from urllib.parse import urlencode
import asyncio
import platform
import json

preload = []
preloaded = []


def FS(tree, base=".", silent=True, debug=False):
    global preload
    path = [base]
    base_url = ""
    last = 0
    trail = False
    for l in map(str.rstrip, tree.split("\n")):
        if not l:
            continue
        if l == ".":
            continue
        if l.startswith("http"):
            # found a base url
            base_url = l
            if base_url.find("/github.com/") > 0:
                base_url = base_url.replace("/github.com/", "/raw.githubusercontent.com/", 1)

            if base_url.find("/tree/") > 0:
                base_url = base_url.replace("/tree/", "/", 1)

            base_url = base_url.rstrip("/") + "/"
            continue

        pos, elem = l.rsplit(" ", 1)
        current = (1 + len(pos)) // 4
        if not silent:
            print(l[4:])
        if current <= last:
            preload.append([base_url + "/".join(path), "/".join(path)])
            if debug:
                print(preload[-1], "write", current, last)
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
        preload.append([base_url + "/".join(path), "/".join(path)])


async def preload_fetch(silent=True, debug=False, standalone=False):
    global preload, preloaded
    from pathlib import Path

    base_url = ""
    fileset = []

    while len(preload):
        url, strfilename = preload.pop(0)
        if strfilename == ".":
            base_url = url
            continue
        if base_url:
            url = base_url + "/" + url

        filename = Path(strfilename)
        if debug:
            print(f"{url} => {Path.cwd() / filename}")

        if not filename.is_file():
            filename.parent.mkdir(parents=True, exist_ok=True)
            async with platform.fopen(url, "rb") as source:
                with open(filename, "wb") as target:
                    target.write(source.read())

        fileset.append(filename)

        if not silent:
            print("FS:", filename)

    preloaded.extend(fileset)
    if standalone:
        return fileset
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
    var request = new Request(url, {method: 'POST', body: JSON.stringify(data)})
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
