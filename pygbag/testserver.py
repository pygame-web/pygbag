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
#import html
import argparse
import io


try:
    from future_fstrings import fstring_decode
except:
    fstring_decode = False



class CodeHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
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
        path = self.translate_path(self.path)
        f = None
        if os.path.isdir(path):
            parts = urllib.parse.urlsplit(self.path)
            if not parts.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(HTTPStatus.MOVED_PERMANENTLY)
                new_parts = (parts[0], parts[1], parts[2] + '/',
                             parts[3], parts[4])
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

        try:
            f = open(path, 'rb')
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None

        try:
            fs = os.fstat(f.fileno())
            # Use browser cache if possible
            if ("If-Modified-Since" in self.headers
                    and "If-None-Match" not in self.headers):
                # compare If-Modified-Since and time of last file modification
                try:
                    ims = email.utils.parsedate_to_datetime(
                        self.headers["If-Modified-Since"])
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
                        last_modif = datetime.datetime.fromtimestamp(
                            fs.st_mtime, datetime.timezone.utc)
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
            if path.endswith('.py'):
                print(" --> do_GET(%s)" % path)
                if fstring_decode:
                    content, _ = fstring_decode(f.read())
                    content = content.encode('UTF-8')
                else:
                    content = f.read()

                file_size = len(content)
                f = io.BytesIO(content)

            self.send_header("Content-Length", str(file_size))
            self.send_header("Last-Modified",
                self.date_time_string(fs.st_mtime))
            self.end_headers()
            return f
        except:
            f.close()
            raise




def code_server(HandlerClass, ServerClass=ThreadingHTTPServer, protocol="HTTP/1.0", port=8000, bind="", ssl=False):
    """
    This runs an HTTP server on port 8000 (or the port argument).
    """

    server_address = (bind, port)

    HandlerClass.protocol_version = protocol

    with ServerClass(server_address, HandlerClass) as httpd:
        sa = httpd.socket.getsockname()

        if ssl:
            try:
                httpd.socket = modssl.wrap_socket (httpd.socket, keyfile='key.pem', certfile='server.pem', server_side=True)
            except Exception as e:
                print("can't start ssl",e)
                print("maybe 'openssl req -new -x509 -keyout key.pem -out server.pem -days 3650 -nodes'")
                ssl=False

        if ssl:
            serve_message = "Serving HTTPS on {host} port {port} (https://{host}:{port}/) ..."
        else:
            serve_message = "Serving HTTP on {host} port {port} (http://{host}:{port}/) ..."
        print(serve_message.format(host=sa[0], port=sa[1]))
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received, exiting.")
            sys.exit(0)


parser = argparse.ArgumentParser()

ROOT = os.path.dirname(os.path.dirname(os.path.dirname((__file__))))


print("\nServing python files from [%s]\n\nwith no security/performance in mind, i'm just a test tool : don't rely on me" % ROOT)

parser.add_argument(
    "--bind", "-b", default="", metavar="ADDRESS", help="Specify alternate bind address " "[default: all interfaces]"
)
parser.add_argument("--directory", "-d", default=ROOT, help="Specify alternative directory " "[default:%s]" % ROOT)

parser.add_argument("--ssl",default=False,help="enable ssl with server.pem and key.pem")

parser.add_argument("--port", action="store", default=8000, type=int, nargs="?", help="Specify alternate port [default: 8000]")

args = parser.parse_args()

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

if not ".wasm" in CodeHandler.extensions_map:
    print("WARNING: wasm mimetype unsupported on that system, trying to correct", file=sys.stderr)
    CodeHandler.extensions_map[".wasm"] = "application/wasm"

code_server(HandlerClass=handler_class, port=args.port, bind=args.bind, ssl=ssl)
