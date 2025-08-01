#
# https://peps.python.org/pep-0722/ – Dependency specification for single-file scripts
# https://peps.python.org/pep-0723
# https://peps.python.org/pep-0508/ – Dependency specification for Python Software Packages
# https://setuptools.pypa.io/en/latest/userguide/ext_modules.html
#

import sys
import os
from pathlib import Path
import glob

import re

import tomllib

import json

import importlib
import installer
import pyparsing
from packaging.requirements import Requirement

from aio.filelike import fopen

import platform
import platform_wasm.todo

from zipfile import ZipFile

# TODO: maybe control wheel cache with $XDG_CACHE_HOME/pip


# store installed wheel somewhere
env = Path(os.getcwd()) / "build" / "env"
env.mkdir(parents=True, exist_ok=True)

# we want host to load wasm packages too
# so make pure/bin folder first for imports

if env.as_posix() not in sys.path:
    sys.path.insert(0, env.as_posix())

sconf = __import__("sysconfig").get_paths()
sconf["purelib"] = sconf["platlib"] = env.as_posix()

if sconf["platlib"] not in sys.path:
    sys.path.append(sconf["platlib"])

PATCHLIST = []

# fast skip list
HISTORY = ["pyodide", "pytest", "pytest-ruff", "ruff", "tarfile"]

hint_failed = []


class Config:
    READ_723 = True
    BLOCK_RE_723 = r"(?m)^# /// (?P<type>[a-zA-Z0-9-]+)$\s(?P<content>(^#(| .*)$\s)+)^# ///$"
    PKG_BASE_DEFAULT = "https://pygame-web.github.io/archives/repo/"
    PKG_INDEXES = []
    REPO_INDEX = "index.json"
    REPO_DATA = "repodata.json"
    repos = []
    pkg_repolist = []
    dev_mode = ".-X.dev." in ".".join([""] + sys.orig_argv + [""])

    Requires_Dist = []
    Requires_Processing = []
    Requires_Failures = []

    mapping = {
        "pygame": "pygame.base",
        "pygame_ce": "pygame.base",
        "pygame_static": "pygame.base",
        "python_i18n": "i18n",
        "pillow": "PIL",
        "pyglm": "glm",
        "opencv_python": "cv2",
        "pysdl3": "sdl3",
    }

def read_dependency_block_723(code):
    global HISTORY, hint_failed
    # Skip lines until we reach a dependency block (OR EOF).
    has_block = False

    content = []
    for line in code.split("\n"):
        if not has_block:
            if line.strip() in ["# /// pyproject", "# /// script"]:
                has_block = True
            continue

        if not line.startswith("#"):
            break

        if line.strip() == "# ///":
            break

        content.append(line[2:])
    struct = tomllib.loads("\n".join(content))

    print(json.dumps(struct, sort_keys=True, indent=4))
    if struct.get("project", None):
        struct = struct.get("project", {"dependencies": []})
    deps = struct.get("dependencies", [])
    for dep in deps:
        yield dep


def install(pkg_file, sconf=None):
    global HISTORY
    from installer import install
    from installer.destinations import SchemeDictionaryDestination
    from installer.sources import WheelFile
    if pkg_file in HISTORY:
        print(f"# 144: install: {pkg_file} already installed or skipped")
        return

    # Handler for installation directories and writing into them.
    destination = SchemeDictionaryDestination(
        sconf or __import_("sysconfig").get_paths(),
        interpreter=sys.executable,
        script_kind="posix",
    )

    try:
        with WheelFile.open(pkg_file) as source:
            install(
                source=source,
                destination=destination,
                # Additional metadata that is generated by the installation tool.
                additional_metadata={
                    "INSTALLER": b"pygbag",
                },
            )
        if pkg_file not in HISTORY:
            HISTORY.append(pkg_file)
            importlib.invalidate_caches()
        print(f"# 166: {pkg_file} installed")
    except FileExistsError as ex:
        print(f"# 160: {pkg_file} already installed (or partially)", ex)
    except Exception as ex:
        pdb(f"# 170: cannot install {pkg_file}")
        sys.print_exception(ex)


#    see cpythonrc
#            if not len(Config.repos):
#                for cdn in (Config.PKG_INDEXES or PyConfig.pkg_indexes):
#                    async with platform.fopen(Path(cdn) / Config.REPO_DATA) as source:
#                        Config.repos.append(json.loads(source.read()))
#
#                DBG("1203: FIXME (this is pyodide maintened stuff, use PEP723 asap) referenced packages :", len(cls.repos[0]["packages"]))


async def async_repos():
    abitag = f"cp{sys.version_info.major}{sys.version_info.minor}"
    apitag = __import__("sysconfig").get_config_var("HOST_GNU_TYPE")
    apitag = apitag.replace("-", "_")

    # user can override "PYPI" index
    if os.environ.get("PYGPI", ""):
        Config.PKG_INDEXES = [os.environ.get("PYGPI")]

    # default to "official" cdn
    if not len(Config.PKG_INDEXES):
        Config.PKG_INDEXES = [Config.PKG_BASE_DEFAULT]

    print("200: async_repos", Config.PKG_INDEXES)

    for repo in Config.PKG_INDEXES:
        idx = f"{repo}index-0.9.2-{abitag}.json"
        try:
            async with fopen(idx, "r", encoding="UTF-8") as index:
                try:
                    data = index.read()
                    if isinstance(data, bytes):
                        data = data.decode()
                    data = data.replace("<abi>", abitag)
                    data = data.replace("<api>", apitag)
                    repo = json.loads(data)
                except:
                    pdb(f"213: {idx=}: malformed json index {data}")
                    continue
                if repo not in Config.pkg_repolist:
                    Config.pkg_repolist.append(repo)
        except FileNotFoundError:
            print("\n" * 4)
            print("!" * 75)
            print("Sorry, there is no pygbag package repository for your python version")
            print("!" * 75, "\n" * 4)
            #raise SystemExit

    if not aio.cross.simulator:
        rewritecdn = ""
        import platform

        if os.environ.get("PYGPI", ""):
            rewritecdn = os.environ.get("PYGPI")
        elif platform.window.location.href.startswith("http://localhost:8"):
            rewritecdn = "http://localhost:8000/archives/repo/"

        if rewritecdn:
            print(f"# 231: {rewritecdn=}")
            for idx, repo in enumerate(Config.pkg_repolist):
                repo["-CDN-"] = rewritecdn

def processing(dep):
    if dep in HISTORY:
        return True
    if dep in Config.Requires_Processing:
        return True
    if dep in Config.Requires_Failures:
        return True
    return False


async def install_pkg(sysconf, wheel_url, wheel_pkg):
    target_filename = f"/tmp/{wheel_pkg}"
    async with fopen(wheel_url, "rb") as pkg:
        with open(target_filename, "wb") as target:
            target.write(pkg.read())
        pkg.seek(0)
        with ZipFile(pkg) as archive:
            for name in archive.namelist():
                if name.endswith(".dist-info/METADATA"):
                    for line in archive.open(name).read().decode().splitlines():
                        if line.startswith('Requires-Dist: '):
                            if line.find('; extra ')>0:
                                continue
                            req = Requirement(line[15:])
                            if req.extras:
                                continue
                            if processing(req.name):
                                continue
                            if not req.name in Config.Requires_Dist:
                                Config.Requires_Dist.insert(0,req.name)
    while len(Config.Requires_Dist):
        elem = None
        for elem in Config.Requires_Dist:
            if not processing(elem):
                break
        else:
            break
        Config.Requires_Processing.append(elem)
        print(f"# 265: {elem=}")
        if not await pip_install(elem, sysconf):
            print(f"install: {wheel_pkg} is missing {elem}")
        else:
            try:
                Config.Requires_Processing.remove(elem)
            except:
                pass
            try:
                Config.Requires_Dist.remove(elem)
            except:
                pass

    install(target_filename, sysconf)


def do_patches():
    global PATCHLIST
    # apply any patches
    while len(PATCHLIST):
        dep = PATCHLIST.pop(0)
        print(f"254: patching {dep}")
        try:
            import platform

            platform.patches.pop(dep)()
        except Exception as e:
            sys.print_exception(e)


# FIXME: HISTORY and invalidate caches
async def pip_install(pkg, sysconf={}):
    global sconf
    if pkg in Config.Requires_Failures:
        return

    #print("282: searching", pkg)

    if not sysconf:
        sysconf = sconf

    wheel_url = ""

    # hack for WASM wheel repo
    remap = pkg.lower().replace('-','_')
    if remap in Config.mapping:
        pkg = Config.mapping[remap]
        print(f"294: {remap} package renamed to {pkg}")

    if pkg in HISTORY:
        print(f"# 322: pip_install: {pkg} already installed")
        return

    if pkg in platform.patches:
        if not pkg in PATCHLIST:
            PATCHLIST.append(pkg)

    for repo in Config.pkg_repolist:
        if pkg in repo:
            wheel_url = f"{repo['-CDN-']}{repo[pkg]}#"
            break
    else:
        # try to get a pure python wheel from pypi
        try:
            async with fopen(f"https://pypi.org/simple/{pkg}/") as html:
                if html:
                    for line in html.readlines():
                        if line.find("href=") > 0:
                            if line.find("py3-none-any.whl") > 0:
                                wheel_url = line.split('"', 2)[1]
                else:
                    print("308: ERROR: cannot find package :", pkg)
        except FileNotFoundError:
            print("285: ERROR: cannot find package :", pkg)
            return

        except:
            print("320: ERROR: cannot find package :", pkg)
            return

    if wheel_url:
        try:
            wheel_pkg, wheel_hash = wheel_url.rsplit("/", 1)[-1].split("#", 1)
            if pkg not in HISTORY:
                HISTORY.append(pkg)
            await install_pkg(sysconf, wheel_url, wheel_pkg)
            return True
        except Exception as e:
            print("324: INVALID", pkg, "from", wheel_url, e)
            #sys.print_exception(e)
    else:
        print(f"309: no provider found for {pkg}")

    if not pkg in Config.Requires_Failures:
        Config.Requires_Failures.append(pkg)


PYGAME = 0


async def parse_code(code, env):
    global PATCHLIST, PYGAME, HISTORY, hint_failed

    maybe_missing = []

    import platform

    if Config.READ_723:
        for req in read_dependency_block_723(code):
            pkg = str(req)
            if (env / pkg).is_dir():
                print("found in env :", pkg)
                continue
            elif pkg and pkg[0]=='!':
                skip = pkg[1:]
                if not skip in HISTORY:
                    HISTORY.append(skip)
                if not skip in hint_failed:
                    hint_failed.append(skip)
                if skip in platform.patches:
                    if not skip in PATCHLIST:
                        PATCHLIST.append(skip)
                continue
            elif pkg not in maybe_missing:
                # do not change case ( eg PIL )
                maybe_missing.append(pkg.lower().replace("-", "_"))

    still_missing = []

    for dep in maybe_missing:
        if dep in platform.patches:
            PATCHLIST.append(dep)

        # special case of pygame code in pygbag site-packages
        if dep == "pygame.base" and not PYGAME:
            PYGAME = 1
            still_missing.append(dep)
            continue

        if not importlib.util.find_spec(dep) and dep not in still_missing:
            still_missing.append(dep)
        else:
            print("found in path :", dep)

    return still_missing


# parse_code does the patching
# this is not called by pythonrc
async def check_list(code=None, filename=None):
    global PATCHLIST, async_repos, env, sconf
    print()
    print("-" * 11, "computing required packages", "-" * 10)

    # pythonrc is calling aio.pep0723.parse_code not check_list
    # so do patching here
    patchlevel = platform_wasm.todo.patch()
    if patchlevel:
        print("392: parse_code() patches loaded :", list(patchlevel.keys()))
        platform_wasm.todo.patch = lambda: None
        # and only do that once and for all.
        await async_repos()
        del async_repos

    # mandatory
    importlib.invalidate_caches()

    if code is None:
        code = open(filename, "r").read()

    still_missing = await parse_code(code, env)

    # is there something to do ?
    if len(still_missing):
        importlib.invalidate_caches()

        # TODO: check for possible upgrade of env/* pkg

        maybe_missing = still_missing
        still_missing = []

        for pkg in maybe_missing:
            hit = ""
            for repo in Config.pkg_repolist:
                wheel_pkg = repo.get(pkg, "")
                if wheel_pkg:
                    wheel_url = repo["-CDN-"] + "/" + wheel_pkg
                    wheel_pkg = wheel_url.rsplit("/", 1)[-1]
                    await install_pkg(sconf, wheel_url, wheel_pkg)
                    hit = pkg

            if len(hit):
                print("found on pygbag repo and installed to env :", hit)
                if hit not in HISTORY:
                    HISTORY.append(hit)
            else:
                still_missing.append(pkg)

        for pkg in still_missing:
            di = f"{(env / pkg).as_posix()}-*.dist-info"
            gg = glob.glob(di)
            if gg:
                print("found in env :", gg[0].rsplit("/", 1)[-1])
                continue

            pkg_final = pkg.replace("-", "_")
            if (env / pkg_final).is_dir():
                print("found in env :", pkg)
                continue
            await pip_install(pkg_final, sconf)

    # wasm compilation
    if not aio.cross.simulator:
        import platform
        import asyncio

        print(f'# 439: Scanning {sconf["platlib"]} for WebAssembly library')
        platform.explore(sconf["platlib"], verbose=True)
        for compilation in range(1 + embed.preloading()):

            await asyncio.sleep(0)
            if embed.preloading() <= 0:
                break
        else:
            print("# 442: ERROR: remaining wasm {embed.preloading()}")
        await asyncio.sleep(0)

    do_patches()

    print("-" * 40)
    print()

    return still_missing


# aio.pep0723
