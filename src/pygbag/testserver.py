#!/usr/bin/env python
import sys
import os

import mimetypes

mimetypes.init()
if ".wasm" not in mimetypes.types_map:
    print(
        "WARNING: wasm mimetype unsupported on that system, trying to correct",
        file=sys.stderr,
    )
    mimetypes.types_map[".wasm"] = "application/wasm"


from functools import partial
from http.server import *
from http import HTTPStatus
import email.utils
import datetime
import urllib

# import html
import argparse
import io


import urllib.request
import hashlib
from pathlib import Path


# on first load be verbose
VERB = True

CACHE = None

# does not support {x=}
# try:
#    from future_fstrings import fstring_decode
# except:
fstring_decode = False


try:
    from . import app

    if app.AUTO_REBUILD:
        from . import pack

        AUTO_REBUILD = pack.stream_pack_replay
except:
    AUTO_REBUILD = False


class CodeHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("access-control-allow-origin", "*")
        self.send_header("cross-origin-resource-policy:", "cross-origin")
        self.send_header("cross-origin-opener-policy", "cross-origin")

        # allow local threads ( and hardware ones with xxx.localhost subdomains )
        self.send_header("origin-agent-cluster", "?1")

        # not valid for Atomics
        # self.send_header("cross-origin-embedder-policy", "unsafe-none")

        # not -always- valid for Atomics (firefox)
        # self.send_header("cross-origin-embedder-policy", "credentialless")

        # Access-Control-Allow-Private-Network
        self.send_header("cross-origin-embedder-policy", "require-corp")

        super().end_headers()

    def do_GET(self):
        f = self.send_head()
        if f:
            try:
                self.copyfile(f, self.wfile)
            finally:
                f.close()

    def do_HEAD(self):
        f = self.send_head()
        if f:
            f.close()

    def send_head(self):
        global VERB, CDN, PROXY, BCDN, BPROXY, AUTO_REBUILD
        path = self.translate_path(self.path)
        if VERB:
            print(
                f"""

{self.path=} {path=}
"""
            )

        f = None
        if os.path.isdir(path):
            parts = urllib.parse.urlsplit(self.path)
            if not parts.path.endswith("/"):
                # redirect browser - doing basically what apache does
                self.send_response(HTTPStatus.MOVED_PERMANENTLY)
                new_parts = (parts[0], parts[1], parts[2] + "/", parts[3], parts[4])
                new_url = urllib.parse.urlunsplit(new_parts)
                self.send_header("Location", new_url)
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)

        ctype = self.guess_type(path)

        if path.endswith("/"):
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None

        f = None

        # .map don't exist and apk is local and could be generated on the fly
        invalid = path.endswith(".map") or path.endswith(".apk")

        if invalid and path.endswith(".map"):
            print(f"MAP? : {path}")

        if not os.path.isfile(path) and not invalid:
            remote_url = CDN + self.path
            cache = hashlib.md5(remote_url.encode()).hexdigest()
            d_cache = CACHE.joinpath(cache + ".data")
            h_cache = CACHE.joinpath(cache + ".head")
            if not h_cache.is_file():
                if VERB:
                    print("CACHING:", remote_url, "->", d_cache)
                try:
                    lf, headers = urllib.request.urlretrieve(remote_url, d_cache)
                    h_cache.write_text(str(headers))
                except:
                    print("ERROR 404:", remote_url)

            if d_cache.is_file():
                if VERB:
                    print("CACHED:", remote_url, "from", d_cache)
                self.send_response(HTTPStatus.OK)
                f = d_cache.open("rb")
                with h_cache.open() as fh:
                    while True:
                        l = fh.readline()
                        if l.find(": ") > 0:
                            k, v = l.strip().split(": ", 1)
                            k = k.lower()
                            if k in [
                                "content-length",
                                "access-control-allow-origin",
                                "cross-origin-embedder-policy",
                                "cross-origin-resource-policy",
                                "cross-origin-opener-policy",
                            ]:
                                continue
                            self.send_header(k, v)
                        else:
                            break
                    # we have a cache so not first time, be less verbose
                    VERB = False
            cached = True
        else:
            cached = False

        if path.endswith(".apk"):
            if AUTO_REBUILD:
                print()
                AUTO_REBUILD()
                print()
            else:
                print(f"{AUTO_REBUILD=} {path}")

        if f is None:
            try:
                f = open(path, "rb")
            except OSError:
                pass

        if f is None:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None

        try:
            fs = os.fstat(f.fileno())

            # Use browser cache if possible
            if not cached:
                if "If-Modified-Since" in self.headers and "If-None-Match" not in self.headers:
                    # compare If-Modified-Since and time of last file modification
                    try:
                        ims = email.utils.parsedate_to_datetime(self.headers["If-Modified-Since"])
                    except (TypeError, IndexError, OverflowError, ValueError):
                        # ignore ill-formed values
                        pass
                    else:
                        if ims.tzinfo is None:
                            # obsolete format with no timezone, cf.
                            # https://tools.ietf.org/html/rfc7231#section-7.1.1.1
                            ims = ims.replace(tzinfo=datetime.timezone.utc)
                        if ims.tzinfo is datetime.timezone.utc:
                            # compare to UTC datetime of last modification
                            last_modif = datetime.datetime.fromtimestamp(fs.st_mtime, datetime.timezone.utc)
                            # remove microseconds, like in If-Modified-Since
                            last_modif = last_modif.replace(microsecond=0)

                            if last_modif <= ims:
                                self.send_response(HTTPStatus.NOT_MODIFIED)
                                self.end_headers()
                                f.close()
                                return None

                self.send_response(HTTPStatus.OK)

                self.send_header("Content-type", ctype)

            file_size = fs[6]

            if path.endswith(".py"):
                if VERB:
                    print(" --> do_GET(%s)" % path)
                if fstring_decode:
                    content, _ = fstring_decode(f.read())
                    content = content.encode("UTF-8")
                else:
                    content = f.read()

                file_size = len(content)
                f = io.BytesIO(content)

            elif path.endswith(".json"):
                if VERB:
                    print()
                    print(self.path)
                    print()

            elif path.endswith(".html"):
                if VERB:
                    print("REPLACING", path, CDN, PROXY)
                content = f.read()

                # redirect known CDN to relative path
                # FIXME: py*-scripts
                #                content = content.replace(
                #                    b"https://pygame-web.github.io", b"http://localhost:8000"
                #                )

                # redirect user CDN to localhost
                content = content.replace(BCDN, BPROXY)

                file_size = len(content)
                f = io.BytesIO(content)

            self.send_header("content-length", str(file_size))

            if not cached:
                self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))

            self.end_headers()

            return f
        except:
            f.close()
            raise


def code_server(
    HandlerClass,
    ServerClass=ThreadingHTTPServer,
    protocol="HTTP/1.0",
    port=8000,
    bind="localhost",
    ssl=False,
):
    """
    This runs an HTTP server on port 8000 (or the port argument).
    """

    server_address = (bind, port)

    HandlerClass.protocol_version = protocol

    with ServerClass(server_address, HandlerClass) as httpd:
        sa = httpd.socket.getsockname()

        if ssl:
            try:
                httpd.socket = modssl.wrap_socket(
                    httpd.socket,
                    keyfile="key.pem",
                    certfile="server.pem",
                    server_side=True,
                )
            except Exception as e:
                print("can't start ssl", e)
                print("maybe 'openssl req -new -x509 -keyout key.pem -out server.pem -days 3650 -nodes'")
                ssl = False

        if ssl:
            serve_message = "Serving HTTPS on {host} port {port} (https://{host}:{port}/) ..."
        else:
            serve_message = "Serving HTTP on {host} port {port} (http://{bind}:{port}/) ..."

        print(serve_message.format(host=sa[0], port=sa[1], bind=bind))

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received, exiting.")
            sys.exit(0)


if not ".wasm" in CodeHandler.extensions_map:
    print(
        "WARNING: wasm mimetype unsupported on that system, trying to correct",
        file=sys.stderr,
    )
    CodeHandler.extensions_map[".wasm"] = "application/wasm"


def run_code_server(args, cc):
    global CACHE, CDN, PROXY, BCDN, BPROXY
    CACHE = Path(args.cache)
    CDN = "/".join(args.cdn.split("/")[0:3])
    PROXY = cc["proxy"]

    BCDN = CDN.encode("utf-8")
    BPROXY = PROXY.encode("utf-8")

    ssl = args.ssl
    if ssl:
        try:
            import ssl as modssl

            ssl = True
        except:
            print("Faulty ssl support")
            ssl = False
    else:
        print("Not using SSL")
    handler_class = partial(CodeHandler, directory=args.directory)
    code_server(HandlerClass=handler_class, port=args.port, bind=args.bind, ssl=ssl)
