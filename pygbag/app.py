import sys
import os
import argparse

from pathlib import Path
import hashlib
import urllib
import shutil


from . import pack


def main(cdn="https://pmp-p.github.io/pygbag/"):
    assets_folder = Path(sys.argv[-1]).resolve()

    reqs = []

    if sys.version_info < (3, 8):
        # zip deflate  compression level 3.7
        # https://docs.python.org/3.11/library/shutil.html#shutil.copytree dirs_exist_ok = 3.8
        reqs.append("pygbag requires CPython version >= 3.8")

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

    archfile = build_dir.joinpath(f"{archname}.apk")
    if archfile.is_file():
        archfile.unlink()

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
        "--cache", default=cache_dir.as_posix(), help="md5 based url cache directory"
    )

    parser.add_argument(
        "--cdn",
        default=cdn,
        help="web site to cache locally [default:%s]" % cdn,
    )

    parser.add_argument(
        "--template", default="default.tmpl", help="index.html template"
    )

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
        "cdn": args.cdn,
        "proxy": f"http://{args.bind}:{args.port}/",
        "xtermjs": "1",
        "archive": archname,
        "autorun": "0",
    }

    def cache_file(remote_url, suffix):
        nonlocal cache_dir
        cache = hashlib.md5(remote_url.encode()).hexdigest()
        cached = cache_dir.joinpath(cache + "." + suffix)
        return cached

    template_file = Path(args.template)
    if template_file.is_file():
        print(
            f"""
        building from local template {args.template}
        result files will be in {build_dir}
"""
        )
    else:
        tmpl_url = f"{cdn}{args.template}"
        tmpl = cache_file(tmpl_url, "tmpl")
        if tmpl.is_file():
            print(
                f"""
    building from local cached template {cdn}{args.template}
    cached at {tmpl}
    result files will be in {build_dir}
"""
            )
            template_file = tmpl
        else:
            print(
                f"""
    caching template {cdn}{args.template}
    cached locally at {tmpl}
    result files will be in {build_dir}
"""
            )

            template_file, headers = urllib.request.urlretrieve( tmpl_url, tmpl )
            template_file = Path(template_file)

    if assets_folder.joinpath('static').is_dir():
        print(f"""
        copying static files to webroot {build_dir}
""")
        # dirs_exist_ok = 3.8
        shutil.copytree( assets_folder.joinpath('static'), build_dir, dirs_exist_ok=True)

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
        testserver.run_code_server(args, CC)
    else:
        print(args.template, "is not a valid template")
