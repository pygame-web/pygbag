import asyncio
import sys
import os
import argparse


from pathlib import Path
import hashlib
import urllib
import shutil
from datetime import datetime

from .__init__ import __version__

from . import pack
from . import web


# FIXME: remove that when 0.1
devmode = os.path.isfile("dev")
if devmode:
    DEFAULT_PORT = 8666
    DEFAULT_CDN = f"http://localhost:8000/"
    DEFAULT_TMPL = "static/default.tmpl"
    print(
        f"""

*************************************
    DEV MODE

    {DEFAULT_CDN=}
    {DEFAULT_PORT=}
    {DEFAULT_TMPL=}
*************************************
"""
    )

else:
    DEFAULT_CDN = "https://pygame-web.github.io/pygbag/"
    DEFAULT_PORT = 8000
    DEFAULT_TMPL = "default.tmpl"

DEFAULT_SCRIPT = "main.py"


def main():
    asyncio.run(main_run(Path(sys.argv[-1]).resolve()))


async def main_run(patharg, cdn=DEFAULT_CDN):
    global DEFAULT_PORT, DEFAULT_SCRIPT

    if patharg.is_file():
        DEFAULT_SCRIPT = patharg.name
        app_folder = patharg.parent
    else:
        app_folder = patharg.resolve()

    reqs = []

    if sys.version_info < (3, 8):
        # zip deflate  compression level 3.7
        # https://docs.python.org/3.11/library/shutil.html#shutil.copytree dirs_exist_ok = 3.8
        reqs.append("pygbag requires CPython version >= 3.8")

    if not app_folder.is_dir() or patharg.as_posix().endswith("/pygbag/__main__.py"):
        reqs.append(
            "ERROR: Last argument must be app top level directory, or the main python script"
        )

    if len(reqs):
        while len(reqs):
            print(reqs.pop())
        sys.exit(1)

    app_folder.joinpath("build").mkdir(exist_ok=True)

    build_dir = app_folder.joinpath("build/web")
    build_dir.mkdir(exist_ok=True)

    cache_dir = app_folder.joinpath("build/web-cache")

    if devmode and cache_dir.is_dir():
        print("DEVMODE: clearing cache")
        if shutil.rmtree.avoids_symlink_attacks:
            shutil.rmtree(cache_dir.as_posix())
        else:
            print("can't clear cache : rmtree is not safe")

    cache_dir.mkdir(exist_ok=True)

    version = "0.0.0"

    sys.argv.pop()

    parser = argparse.ArgumentParser()

    print(
        "\nServing python files from [%s]\n\nwith no security/performance in mind, i'm just a test tool : don't rely on me"
        % build_dir
    )

    parser.add_argument(
        "--bind",
        default="localhost",
        metavar="ADDRESS",
        help="Specify alternate bind address " "[default: localhost]",
    )
    parser.add_argument(
        "--directory",
        default=build_dir.as_posix(),
        help="Specify alternative directory " "[default:%s]" % build_dir,
    )

    parser.add_argument(
        "--app_name",
        default=app_folder.name,
        help="Specify user facing name of application" "[default:%s]" % app_folder.name,
    )

    parser.add_argument(
        "--cache", default=cache_dir.as_posix(), help="md5 based url cache directory"
    )

    parser.add_argument(
        "--package",
        default=f"web.pygame.{app_folder.name}-{int(datetime.timestamp(datetime.now()))}",
        help="package name, better make it unique",
    )

    parser.add_argument(
        "--version", default=version, help="package name, please make it unique"
    )

    parser.add_argument(
        "--build", action="store_true", help="build only, do not run test server"
    )

    parser.add_argument(
        "--archive", action="store_true", help="make build/web.zip archive for itch.io"
    )

    parser.add_argument(
        "--main",
        default=DEFAULT_SCRIPT,
        help="Specify main script" "[default:%s]" % DEFAULT_SCRIPT,
    )

    parser.add_argument(
        "--icon", default="favicon.png", help="package name, please make it unique"
    )

    parser.add_argument(
        "--cdn",
        default=cdn,
        help="web site to cache locally [default:%s]" % cdn,
    )

    parser.add_argument("--template", default=DEFAULT_TMPL, help="index.html template")

    parser.add_argument(
        "--ssl", default=False, help="enable ssl with server.pem and key.pem"
    )

    parser.add_argument(
        "--port",
        action="store",
        default=DEFAULT_PORT,
        type=int,
        nargs="?",
        help="Specify alternate port [default: 8000]",
    )

    args = parser.parse_args()

    app_name = app_folder.name

    archfile = build_dir.joinpath(f"{app_name}.apk")

    if archfile.is_file():
        archfile.unlink()

    print(
        f"""

SUMMARY
________________________

# the app folder
app_folder={app_folder}

# artefacts directoty
build_dir={build_dir}

# the window title and icon name
app_name={app_name}

# package name, better make it unique
package={args.package}

# icon 96x96 for dekstop 16x16 for web
icon={args.icon}

# js/wasm provider
cdn={args.cdn}

now packing application ....

"""
    )

    await pack.archive(f"{app_name}.apk", app_folder, build_dir)

    CC = {
        "cdn": args.cdn,
        "proxy": f"http://{args.bind}:{args.port}/",
        "xtermjs": "1",
        "archive": app_name,
        "autorun": "0",
        "authors": "pgw",
        "icon": args.icon,
        "title": "cookiecutter.title",
        "directory": app_name,
        "spdx": "cookiecutter.spdx",
        "version": __version__,
    }

    def cache_file(remote_url, suffix):
        nonlocal cache_dir
        cache = hashlib.md5(remote_url.encode()).hexdigest()
        cached = cache_dir.joinpath(cache + "." + suffix)
        return cached

    # get local or online template in order
    # _______________________________________

    template_file = Path(args.template)

    if template_file.is_file():
        print(
            f"""
        building from local template {args.template}
        result files will be in {build_dir}
"""
        )
    else:
        tmpl_url = f"{args.cdn}{args.template}"
        tmpl = cache_file(tmpl_url, "tmpl")
        if tmpl.is_file():
            print(
                f"""
    building from local cached template {args.cdn}{args.template}
    cached at {tmpl}
    result files will be in {build_dir}
"""
            )
            template_file = tmpl
        else:
            print(
                f"""
    caching template {args.cdn}{args.template}
    cached locally at {tmpl}
    result files will be in {build_dir}
"""
            )

            try:
                template_file, headers = web.get(tmpl_url, tmpl)
            except Exception as e:
                print(e)
                print(f"CDN {args.cdn} is not responding : not running test server")
                args.build = True

    if app_folder.joinpath("static").is_dir():
        print(
            f"""
        copying static files to webroot {build_dir}
"""
        )
        # dirs_exist_ok = 3.8
        shutil.copytree(app_folder.joinpath("static"), build_dir, dirs_exist_ok=True)

    # get local or online favicon in order
    # _______________________________________
    icon_file = Path(args.icon)
    if not icon_file.is_file():
        icon_url = f"{args.cdn}{args.icon}"
        icon_file = cache_file(icon_url, "png")

        if icon_file.is_file():
            print(
                f"""
    using icon from local cached file {icon_url}
    cached at {icon_file}"""
            )

        else:
            try:
                icon_file, headers = web.get(icon_url, icon_file)
                print(
                    f"""
        caching icon {icon_url}
        cached locallly at {icon_file}
        """
                )
            except Exception as e:
                sys.print_exception(e)
                print(f"{icon_url} caching error :", e)

    if icon_file.is_file():
        shutil.copyfile(icon_file, build_dir.joinpath("favicon.png"))
    else:
        print(f"error: cannot find {icon_file=}")

    if template_file.is_file():
        with template_file.open("r", encoding="utf-8") as source:
            with open(
                build_dir.joinpath("index.html").resolve(), "w", encoding="utf-8"
            ) as target:
                # while ( line := source.readline():
                while True:
                    line = source.readline()
                    if not line:
                        break
                    for k, v in CC.items():
                        line = line.replace("{{cookiecutter." + k + "}}", v)

                    target.write(line)

        # files should be all ready now
        # except on CDN error on first test, but you did test do you ?
        if args.archive:
            print(
                f"""
    only building a web archive suitable for itch.io
    archive file will be :
    {build_dir}.zip
"""
            )

            await pack.web_archive(f"{app_name}.apk", build_dir)
            return

        elif not args.build:
            if 1:
                ESC("(0")
                CSI("104;93m")
                print("l--------------k")
                print("x      علي     x")
                print("m--------------j")
                CSI("0m")
                ESC("(B")

                CSI("2;10r")

                from . import testserver

                testserver.run_code_server(args, CC)
            else:
                import uasyncio
        else:
            print(
                f"""
    build only requested, not running testserver, files ready here :

build_dir = {build_dir}

            """
            )
    else:
        print(args.template, "is not a valid template")
