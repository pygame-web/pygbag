import sys
import io

if not __UPY__:
    import socket

    socket.setdefaulttimeout(0.0)
else:
    print("7: usocket implementation required")


import os  # unlink


import aio
import platform

temporary = []


async def aio_sock_open(sock, host, port):
    while True:
        try:
            sock.connect(
                (
                    host,
                    port,
                )
            )
        except BlockingIOError:
            await aio.sleep(0)
        except OSError as e:
            # 30 emsdk, 106 linux
            if e.errno in (30, 106):
                return sock
            sys.print_exception(e)


def fix_url(maybe_url):
    url = str(maybe_url)
    if url.startswith("http://"):
        pass
    elif url.startswith("https://"):
        pass
    elif url.startswith("https:/"):
        url = "https:/" + url[6:]
    elif url.startswith("http:/"):
        url = "http:/" + url[5:]
    return url


def mktemp(suffix=""):
    global temporary
    tmpname = f"/tmp/tmp-{aio.ticks}-{len(temporary)}{suffix}"
    temporary.append(tmpname)
    return tmpname


class fopen:
    if __WASM__ and hasattr(platform, "ffi"):
        flags = platform.ffi(
            {
                "redirect": "follow",
                "credentials": "omit",
            }
        )
    else:
        print("69: platform has no object serializer")
        flags = {}

    def __init__(self, maybe_url, mode="r", flags=None, encoding="UTF-8", errors=None, newline=None, closefd=True, opener=None):
        self.url = fix_url(maybe_url)
        self.mode = mode
        flags = flags or self.__class__.flags
        print(f'76: fopen: fetching "{self.url}"')

        self.tmpfile = None

    async def __aexit__(self, *exc):
        if self.tmpfile:
            self.filelike.close()
            try:
                os.unlink(self.tmpfile)
            except FileNotFoundError as e:
                print("78: Async I/O error : file not found", self.url)
        del self.filelike, self.url, self.mode, self.tmpfile

    if __WASM__:

        async def __aenter__(self):
            import platform

            self.tmpfile = shell.mktemp()
            cf = platform.window.cross_file(self.url, self.tmpfile, self.flags)
            try:
                content = await platform.jsiter(cf)
            except Exception as e:
                print("91:", e)

            if "b" in self.mode:
                self.filelike = open(content, "rb")
            else:
                self.filelike = open(content, "r", encoding="utf-8")

            self.filelike.path = content

            def rename_to(target):
                # will be closed
                self.filelike.close()
                os.rename(self.tmpfile, target)
                self.tmpfile = None
                del self.filelike
                return target

            self.filelike.rename_to = rename_to
            return self.filelike

    else:

        async def __aenter__(self):
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(self.url) as response:
                    if response.status != 200:
                        raise FileNotFoundError(self.url)

                    # For large files use response.content.read(chunk_size) instead.
                    if "b" in self.mode:
                        self.filelike = io.BytesIO(await response.read())
                    else:
                        self.filelike = io.StringIO((await response.read()).decode())

            return self.filelike


class sopen:
    def __init__(self, url, mode, tmout):  # =6):
        self.host, port = url.rsplit(":", 1)
        self.port = int(port)
        if __WASM__ and __import__("platform").is_browser:
            if not url.startswith("ws"):
                pdb(f"switching to {self.port}+20000 as websocket")
                self.port += 20000

        self.sock = socket.socket()
        # self.sock.setblocking(0)

    # overload socket ?

    def fileno(self):
        return self.sock.fileno()

    def send(self, *argv, **kw):
        self.sock.send(*argv, **kw)

    def recv(self, *argv):
        return self.sock.recv(*argv)

    # ============== specific ===========================

    async def __aenter__(self):
        # use async
        await aio_sock_open(self.sock, self.host, self.port)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        aio.protect.append(self)
        aio.defer(self.sock.close, (), {})
        del self.port, self.host, self.sock

    def read(self, size=-1):
        return self.recv(0)

    def write(self, data):
        if isinstance(data, str):
            return self.sock.send(data.encode())
        return self.sock.send(data)

    def print(self, *argv, **kw):
        # use EOL
        # kw.setdefault("end","\r\n")
        kw["file"] = io.StringIO(newline="\r\n")
        print(*argv, **kw)
        self.write(kw["file"].getvalue())

    def __enter__(url, mode, tmout):
        # use softrt (wapy)
        return aio.await_for(self.__aenter__())

    def __exit__(self, exc_type, exc, tb):
        # self.sock.close()
        pass
