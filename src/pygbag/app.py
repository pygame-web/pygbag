import asyncio
import sys

# rmtree msg on win32
import warnings

import os
import argparse


from pathlib import Path
import hashlib

# import urllib
import shutil
from datetime import datetime

from .__init__ import VERSION
from .example_config import EXAMPLE_CONFIG

if "--no_ssl_check" in sys.argv:
    import ssl

    # ssl local server testing.
    ssl._create_default_https_context = ssl._create_unverified_context
    # os.environ["REQUESTS_CA_BUNDLE"]="/etc/ssl/certs/ca-bundle.crt"
    sys.argv.remove("--no_ssl_check")

import pygbag

from . import pack
from . import web
from .config_types import Config
# TODO: use another parser for the check
#from .support.cross.aio.pep0723 import read_dependency_block_723


from .config_to_object import load_config


devmode = "--dev" in sys.argv

DEFAULT_SCRIPT = "main.py"
DEFAULT_CONSOLE = 25
DEFAULT_LINES = 50
DEFAULT_COLUMNS = 132
DEFAULT_PYBUILD = "3.12"

CACHE_ROOT = Path("build")
CACHE_PATH = CACHE_ROOT / "web-cache"
CACHE_VERSION = CACHE_ROOT / "version.txt"
CACHE_APP = CACHE_ROOT / "web"

cdn_dot = VERSION.split(".")
cdn_dot.pop()
cdn_version = ".".join(cdn_dot)
del cdn_dot

AUTO_REBUILD = True


if devmode:
    sys.argv.remove("--dev")
    DEFAULT_PORT = 8666
    DEFAULT_CDN = f"http://localhost:8000/pygbag/0.0/"
    DEFAULT_TMPL = "static/wip.tmpl"
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
    # use latest git build
    if cdn_version == "0.0":
        DEFAULT_CDN = f"https://pygame-web.github.io/pygbag/{cdn_version}/"
    else:
        DEFAULT_CDN = f"https://pygame-web.github.io/archives/{cdn_version}/"
    DEFAULT_PORT = 8000
    DEFAULT_TMPL = "default.tmpl"

DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720

def warn(msg):
    print(f"WARNING! {msg}")


def get_parser(
    build_dir: str | None, 
    app_folder: str | None, 
    cache_dir: str | None, 
    cdn: str | None
) -> argparse.ArgumentParser:
    """
    Returns the parser used for the pygbag command line.

    Requires arguments be all strings, representing successfully formed
    arguments, or all None, representing missing arguments for the purposes of 
    calling simply `pygbag --help` from the command line.

    pygbag first processes args with `set_args`, failing if the app folder or 
    other metadata could not be found. Then, it calls `main_run`. This means if
    we create our parser in `main_run`, we will fail even if we just run
    `pygbag --help`. Thus, we should call `get_parser(None, None, None, None)`
    in `set_args` when `--help` is in the command line arguments, and parse it
    to print out help data and then exit.
    """
    assert (
        all(param is None for param in [build_dir, app_folder, cache_dir, cdn]) 
        or all(type(param) is str for param in [build_dir, app_folder, cache_dir, cdn])
    )

    parser = argparse.ArgumentParser()

    print(
        "\nServing python files from [%s]\n\nwith no security/performance in mind, i'm just a test tool : don't rely on me"
        % build_dir
    )

    parser.add_argument(
        "--bind",
        default="localhost",
        metavar="ADDRESS",
        help="Specify alternate bind address [default: localhost]",
    )

    parser.add_argument(
        "--PYBUILD",
        default=DEFAULT_PYBUILD,
        help="Specify python version [default:%s]" % DEFAULT_PYBUILD,
    )

    parser.add_argument(
        "--width",
        default=DEFAULT_WIDTH,
        help="framebuffer width [default:%d]" % DEFAULT_WIDTH,
    )

    parser.add_argument(
        "--height",
        default=DEFAULT_HEIGHT,
        help=f"framebuffer width [default:{DEFAULT_HEIGHT}]",
    )

    parser.add_argument(
        "--COLUMNS",
        default=DEFAULT_COLUMNS,
        help=f"terminal columns [default:{DEFAULT_COLUMNS}]",
    )

    parser.add_argument(
        "--LINES",
        default=DEFAULT_LINES,
        help=f"terminal lines [default:{DEFAULT_LINES}]",
    )

    parser.add_argument(
        "--CONSOLE",
        default=DEFAULT_CONSOLE,
        help=f"console lines ( adds up to terminal lines ) [default:{DEFAULT_CONSOLE}]",
    )

    parser.add_argument(
        "--app_name",
        default=app_folder.name,
        help="Specify user facing name of application [default:%s]" % app_folder.name,
    )

    parser.add_argument(
        "--ume_block",
        default=1,
        help="Specify wait for user media engagement before running [default:%s]" % 1,
    )

    parser.add_argument(
        "--can_close",
        default=0,
        help="Specify if window will ask confirmation for closing [default:%s]" % 0,
    )

    parser.add_argument("--cache", default=cache_dir.as_posix(), help="md5 based url cache directory")

    parser.add_argument(
        "--package",
        default=f"web.pygame.{app_folder.name}-{int(datetime.timestamp(datetime.now()))}",
        help="package name, better make it unique",
    )

    parser.add_argument("--title", default="", help="App nice looking name")

    parser.add_argument(
        "--version",
        default=VERSION,
        help="override prebuilt version path [default:%s]" % VERSION,
    )

    parser.add_argument("--build", action="store_true", help="build only, do not run test server")

    parser.add_argument(
        "--html",
        action="store_true",
        help="build as html with embedded assets (pygame-script)",
    )

    parser.add_argument("--no_opt", action="store_true", help="turn off assets optimizer")

    parser.add_argument("--archive", action="store_true", help="make build/web.zip archive for itch.io")

    #    parser.add_argument(
    #        "--main",
    #        default=DEFAULT_SCRIPT,
    #        help="Specify main script" "[default:%s]" % DEFAULT_SCRIPT,
    #    )

    parser.add_argument(
        "--icon",
        default="favicon.png",
        help="icon png file 32x32 min should be favicon.png",
    )

    parser.add_argument(
        "--cdn",
        default=cdn,
        help="web site to cache locally [default:%s]" % cdn,
    )

    parser.add_argument("--ini", default=False, action="store_true", help="Initialize an example pygbag.ini config file")

    parser.add_argument(
        "--template",
        default=DEFAULT_TMPL,
        help="index.html template [default:%s]" % DEFAULT_TMPL,
    )

    parser.add_argument("--ssl", default=False, help="enable ssl with server.pem and key.pem")

    parser.add_argument(
        "--port",
        action="store",
        default=DEFAULT_PORT,
        type=int,
        nargs="?",
        help="Specify alternate port [default: 8000]",
    )

    parser.add_argument(
        "--disable-sound-format-error",
        action="store_true",
        default=False,
        help="audio files with a common unsupported format found in the assets won't raise an exception",
    )


def set_args(program):
    global DEFAULT_SCRIPT
    import sys
    from pathlib import Path

    required = []

    patharg = Path(program).resolve()
    if patharg.is_file():
        mainscript = patharg.name
        app_folder = patharg.parent
    else:
        app_folder = patharg.resolve()
        mainscript = DEFAULT_SCRIPT

    # print("84: prepending to sys.path", str(app_folder) )
    # sys.path.insert(0, str(app_folder))

    if patharg.suffix == "pyw":
        required.append("79: Error, no .pyw allowed use .py for python script")

    script_path = app_folder / mainscript

    if not script_path.is_file():
        required.append(f"83: Error, no main.py {script_path} found in folder")

    if not app_folder.is_dir() or patharg.as_posix().endswith("/pygbag/__main__.py"):
        required.append("89: Error, Last argument must be a valid app top level directory, or the main.py python script")

    if sys.version_info < (3, 8):
        # zip deflate compression level 3.7
        # https://docs.python.org/3.11/library/shutil.html#shutil.copytree dirs_exist_ok = 3.8
        required.append("84: Error, pygbag requires CPython version >= 3.8")

    if len(required) != 0 and ("-h" in sys.argv or "--help" in sys.argv):
        # if we have outstanding requirements, but we only requested help 
        # documentation, forward what we have to parser.parse_args(), which
        # should print help documentation and exit
        get_parser(None, None, None, None).parse_args()
        assert False # the above line should exit after printing help

    if len(required):
        while len(required):
            print(required.pop())
        print("89: missing requirement(s)")
        sys.exit(89)

    return app_folder, mainscript


def cache_check(app_folder, devmode=False):
    global CACHE_PATH, CACHE_APP, VERSION

    version_file = app_folder / CACHE_VERSION

    clear_cache = False

    # always clear the cache in devmode, because cache source is local and changes a lot
    if devmode:
        print("103: DEVMODE: clearing cache")
        clear_cache = True
    elif version_file.is_file():
        try:
            with open(version_file, "r") as file:
                cache_ver = file.read()
                if cache_ver != VERSION:
                    print(f"115: cache {cache_ver} mismatch, want {VERSION}, cleaning ...")
                    clear_cache = True
        except:
            # something's wrong in cache structure, try clean it up
            clear_cache = True
    else:
        clear_cache = True

    cache_root = app_folder.joinpath(CACHE_ROOT)
    cache_dir = app_folder / CACHE_PATH
    build_dir = app_folder / CACHE_APP

    def make_cache_dirs():
        nonlocal cache_root, cache_dir

        cache_root.mkdir(exist_ok=True)
        build_dir.mkdir(exist_ok=True)
        cache_dir.mkdir(exist_ok=True)

    if clear_cache:
        win32 = sys.platform == "win32"
        if cache_dir.is_dir():
            if shutil.rmtree.avoids_symlink_attacks or win32:
                if win32:
                    warnings.warn("clear cache : rmtree is not safe on that system (win32)")
                shutil.rmtree(cache_dir.as_posix())
            else:
                print(
                    "171: cannot clear cache : rmtree is not safe on that system",
                    file=sys.stderr,
                )
                print(
                    "175: Please remove build folder manually",
                    file=sys.stderr,
                )
                raise SystemExit(115)

        # rebuild
        make_cache_dirs()

        with open(version_file, "w") as file:
            file.write(VERSION)

    return build_dir, cache_dir


async def main_run(app_folder, mainscript, cdn=DEFAULT_CDN):
    global DEFAULT_PORT, DEFAULT_SCRIPT, APP_CACHE, required

    # Checks for existance of PEP 723 header on main.py https://peps.python.org/pep-0723/
    main_file = Path(app_folder, mainscript)
    with open(main_file, "r") as f:
        src_code = f.read()

    # TODO: match import list and pep block content
    if 0:
        has_pep723 = False
        deps = {"pygame-ce"}
        for dep in read_dependency_block_723(src_code):
            has_pep723 = True
            if dep == "pygame-ce":
                pass
            elif dep == "pygame":
                warnings.warn("Pygbag uses pygame-ce for running on web. If you're using pygame, you should probably upgrade to pygame-ce, it is backwards compatible so your code will still work. If you're using pygame-ce already, specify 'pygame-ce' instead of 'pygame'.")
            else:
                deps.add(dep)
        if not has_pep723:
            warnings.warn("Couldn't find PEP 723 Header. See this: https://pygame-web.github.io/wiki/pygbag/#complex-packages")

    DEFAULT_SCRIPT = mainscript or DEFAULT_SCRIPT

    build_dir, cache_dir = cache_check(app_folder, devmode)

    sys.argv.pop()

    if "--git" in sys.argv:
        sys.argv.remove("--git")

    parser = get_parser(build_dir, app_folder, cache_dir, cdn)

    args = parser.parse_args()

    # when in browser IDE everything should be done in allowed folder

    # force build directory in sourcefolder
    args.directory = build_dir.as_posix()

    # force cache directory to be inside build folder
    args.cache = cache_dir.as_posix()

    app_name = app_folder.name.lower().replace(" ", ".")

    archfile = build_dir.joinpath(f"{app_name}.apk")

    if archfile.is_file():
        archfile.unlink()

    print(
        f"""

SUMMARY
________________________

# the app folder
app_folder={app_folder}

# artefacts directory
build_dir={build_dir}

# cache directory
cache={cache_dir}

# the window title and icon name
app_name={app_name}

# package name, better make it unique
package={args.package}

# icons:  96x96 for desktop, 16x16 for web
icon={args.icon}

# js/wasm provider
cdn={args.cdn}

now packing application ....

"""
    )

    CC = {
        "cdn": args.cdn,
        "proxy": f"http://{args.bind}:{args.port}/",
        "xtermjs": "1",
        "width": args.width,
        "height": args.height,
        "ume_block": args.ume_block,
        "can_close": args.can_close,
        "archive": app_name,
        "autorun": "0",
        "authors": "pgw",
        "icon": args.icon,
        "title": (args.title or app_name),
        "directory": app_name,
        "spdx": "cookiecutter.spdx",
        "version": VERSION,
        "PYBUILD": args.PYBUILD,
        "COLUMNS": args.COLUMNS,
        "LINES": args.LINES,
        "CONSOLE": args.CONSOLE,
        "INI": args.ini,
    }

    if args.ini:
        if not os.path.exists("pygbag.ini"):
            with open("pygbag.ini", "w") as f:
                f.write(EXAMPLE_CONFIG)
        else:
            print("ERROR: You already have an pygbag.ini file. Please delete it before attempting to init a fresh config.")
            raise SystemExit

    if os.path.exists("pygbag.ini"):
        config: Config = load_config("pygbag.ini")
        ignore_files = config.DEPENDENCIES.ignorefiles
        ignore_dirs = config.DEPENDENCIES.ignoredirs
    else:
        print("WARNING: No pygbag.ini found! See: https://pygame-web.github.io/wiki/pygbag-configuration")
        ignore_files = []
        ignore_dirs = []

    for ignore_arr in [ignore_files, ignore_dirs]:
        for ignored in ignore_arr:
            if ignored.strip().find(" ") != -1:  # has space in folder/file name
                print(f"|{ignored}|")
                print("ERROR! You cannot use folder/files with spaces in it.")
                raise SystemExit  # maybe use a custom pygbag exception

    pygbag.config = CC

    print(f"Ignored dirs: {ignore_dirs}")
    print(f"Ignored files: {ignore_files}")

    await pack.archive(f"{app_name}.apk", app_folder, ignore_dirs, ignore_files, build_dir)

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
        cached locally at {icon_file}
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
            with open(build_dir.joinpath("index.html").resolve(), "w", encoding="utf-8") as target:
                # while ( line := source.readline()):
                while True:
                    line = source.readline()
                    if not line:
                        break
                    for k, v in CC.items():
                        line = line.replace("{{cookiecutter." + k + "}}", str(v))

                    target.write(line)

        # files should be all ready and tested now
        # except on CDN error on first test, but you did test didn't you ?
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
            from . import testserver

            testserver.run_code_server(args, CC)

        else:
            print(
                f"""
    build only requested, not running testserver, files ready here :

build_dir = {build_dir}

"""
            )
    else:
        print(args.template, "is not a valid template")


def main():
    app_folder, mainscript = set_args(sys.argv[-1])

    # sim does not use cache.
    if "--sim" in sys.argv:
        print(f"To use simulator launch with : {sys.executable} -m pygbag {' '.join(sys.argv[1:])}")
        return 1
    else:
        asyncio.run(main_run(app_folder, mainscript))
    return 0
