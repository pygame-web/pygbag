print(" *pygbag*")
import sys
from . import pack

from pathlib import Path
import os



assets_folder = Path(sys.argv[-1]).resolve()

reqs=[]

if sys.version_info < (3, 7):
    reqs.append("require CPython version >= 3.7")

if not assets_folder.is_dir():
    reqs.append("ERROR: Last argument must be app top level directory")

if len(reqs):
    while len(reqs):
        print(reqs.pop())
    sys.exit(1)


build_dir = assets_folder.joinpath("build/web")
build_dir.mkdir(exist_ok=True)

archname = assets_folder.name

print(f"""
assets_folder={assets_folder}
build_dir={build_dir}
archname={archname}
""")

pack.archive(f"{archname}.apk", assets_folder, build_dir)


sys.argv.pop()
sys.argv.append( '--directory' )
sys.argv.append( build_dir.as_posix() )
from . import testserver


