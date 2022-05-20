print(" *pygbag*")

import sys
import os
import argparse

from . import pack

from pathlib import Path


assets_folder = Path(sys.argv[-1]).resolve()

reqs = []

if sys.version_info < (3, 7):
    reqs.append("require CPython version >= 3.7")

if not assets_folder.is_dir():
    reqs.append("ERROR: Last argument must be app top level directory")

if len(reqs):
    while len(reqs):
        print(reqs.pop())
    sys.exit(1)

assets_folder.joinpath("build").mkdir(exist_ok=True)

build_dir = assets_folder.joinpath("build/web")
build_dir.mkdir(exist_ok=True)

cache_dir = assets_folder.joinpath("build/web-cache")
cache_dir.mkdir(exist_ok=True)


archname = assets_folder.name

print(
    f"""
assets_folder={assets_folder}
build_dir={build_dir}
archname={archname}
"""
)

pack.archive(f"{archname}.apk", assets_folder, build_dir)

sys.argv.pop()

parser = argparse.ArgumentParser()

print(
    "\nServing python files from [%s]\n\nwith no security/performance in mind, i'm just a test tool : don't rely on me"
    % build_dir
)

parser.add_argument(
    "--bind",
    "-b",
    default="",
    metavar="ADDRESS",
    help="Specify alternate bind address " "[default: all interfaces]",
)
parser.add_argument(
    "--directory",
    "-d",
    default=build_dir.as_posix(),
    help="Specify alternative directory " "[default:%s]" % build_dir,
)

parser.add_argument(
    "--cache", default=cache_dir.as_posix(), help="md5 based url cache directory"
)

parser.add_argument(
    "--site", default="https://pmp-p.github.io/pygbag/", help="web site to shadow"
)

parser.add_argument("--template", default="default.tmpl", help="index.html template")

parser.add_argument(
    "--ssl", default=False, help="enable ssl with server.pem and key.pem"
)

parser.add_argument(
    "--port",
    action="store",
    default=8000,
    type=int,
    nargs="?",
    help="Specify alternate port [default: 8000]",
)

args = parser.parse_args()


from . import testserver

CC = {
    "base": f"http://localhost:{args.port}/",
}


if Path(args.template).is_file():
    with open(args.template, "rU") as source:
        with open(build_dir.joinpath("index.html").resolve(), "w") as target:
            # while ( line := source.readline():
            while True:
                line = source.readline()
                if not line:
                    break
                for k, v in CC.items():
                    line = line.replace("{{cookiecutter." + k + "}}", v)

                target.write(line + "\n")


testserver.run_code_server(args)
