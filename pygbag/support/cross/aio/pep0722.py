# https://peps.python.org/pep-0722/ – Dependency specification for single-file scripts
# https://peps.python.org/pep-0508/ – Dependency specification for Python Software Packages

import sys
import os
from pathlib import Path

import re
import tokenize

import json

import importlib
import installer
import pyparsing
from packaging.requirements import Requirement



class Config:
    DEPENDENCY_BLOCK_MARKER = r"(?i)^#\s+script\s+dependencies:\s*$"
    PKG_INDEXES = []
    REPO_INDEX = "repodata.json"
    repos = []

def read_dependency_block(filename):
    # Use the tokenize module to handle any encoding declaration.
    with tokenize.open(filename) as f:
        # Skip lines until we reach a dependency block (OR EOF).
        for line in f:
            if re.match(Config.DEPENDENCY_BLOCK_MARKER, line):
                break
        # Read dependency lines until we hit a line that doesn't
        # start with #, or we are at EOF.
        for line in f:
            if not line.startswith("#"):
                break
            # Remove comments. An inline comment is introduced by
            # a hash, which must be preceded and followed by a
            # space.
            line = line[1:].split(" # ", maxsplit=1)[0]
            line = line.strip()
            # Ignore empty lines
            if not line:
                continue
            # Try to convert to a requirement. This will raise
            # an error if the line is not a PEP 508 requirement
            yield Requirement(line)


async def async_imports_init():
    from aio.filelike import fopen
    global PKG_INDEXES
    for cdn in Config.PKG_INDEXES:
        print("init cdn :", Config.PKG_INDEXES)
        async with fopen(Path(cdn) / Config.REPO_INDEX) as source:
            Config.repos.append(json.loads(source.read()))

    # print(json.dumps(cls.repos[0]["packages"], sort_keys=True, indent=4))

    pdb("referenced packages :", len(Config.repos[0]["packages"]))

    #if not len(PyConfig.pkg_repolist):
    #    await cls.async_repos()



HISTORY = []

def install(pkg_file, sconf=None):
    global HISTORY
    from installer import install
    from installer.destinations import SchemeDictionaryDestination
    from installer.sources import WheelFile

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
            HISTORY.append(pkg_file)
    except FileExistsError:
        print(f"38: {pkg_file} already installed")
    except Exception as ex:
        pdb(f"82: cannot install {pkg_file}")
        sys.print_exception(ex)


async def check_list(filename):
    global PKG_INDEXES
    from aio.filelike import fopen

    print()
    print('-'*11,"required packages",'-'*10)
    maybe_missing = []

    for req in read_dependency_block(filename):
        dep = str(req)

        print(dep,':', end='')
        if importlib.util.find_spec(dep):
            print('found')
        else:
            print("?")
            if dep not in maybe_missing:
                maybe_missing.append(dep)

    print('-'*40)
    print()

    # nothing to do
    if not len(maybe_missing):
        return

    # TODO: prio over pypi
    if not len(Config.PKG_INDEXES):
        await async_imports_init()


    print("="*40)

    sconf = __import__("sysconfig").get_paths()

    for k,v in sconf.items():
        print(k,v)

    env = Path(os.getcwd()) / "env"
    env.mkdir(exist_ok=True)
    sys.path.append(env)
    sconf["purelib"] = sconf["platlib"] = env.as_posix()

    importlib.invalidate_caches()

    for pkg in maybe_missing:
        print("searching",pkg)
        wheel_url = ''
        async with fopen(f"https://pypi.org/simple/{pkg}/") as html:
            for line in html.readlines():
                if line.find('href=')>0:
                    if line.find('-py3-none-any.whl')>0:
                        wheel_url = line.split('"',2)[1]
        wheel_pkg,wheel_hash = wheel_url.rsplit('/',1)[-1].split('#',1)

        print(wheel_pkg, wheel_url)

        target_filename = f'/tmp/{wheel_pkg}'
        async with fopen(wheel_url,"rb") as pkg:
            with open(target_filename,'wb') as target:
                target.write(pkg.read())
        install(target_filename, sconf)


    print("="*40)