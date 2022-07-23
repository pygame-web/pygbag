import sys, os
import zipfile
from pathlib import Path

from .gathering import gather
from .filtering import filter
from .optimizing import optimize

"""
pngquant -f --ext -pygbag.png --quality 40 $(find|grep png$)

for wav in $(find |grep wav$)
do
    ffmpeg -i $wav $wav.ogg
done

for mp3 in $(find |grep mp3$)
do
    ffmpeg -i $mp3 $mp3.ogg
done

Scour is an SVG optimizer/cleaner written in Python
https://github.com/scour-project/scour


"""

COUNTER = 0
TRUNCATE = 0
ASSETS = []
HAS_STATIC = False
HAS_MAIN = False
LEVEL = -1
PNGOPT = []
WAVOPT = []
MP3OPT = []


def pack_files(zf, parent, zfolders, newpath):
    global COUNTER, TRUNCATE, ASSETS, HAS_STATIC, HAS_MAIN, LEVEL
    global PNGOPT, WAVOPT, MP3OPT
    try:
        LEVEL += 1
        os.chdir(newpath)

        for current, dirnames, filenames in os.walk(newpath):
            p_dirname = Path(current)
            dispname = Path(current[TRUNCATE:] or "/").as_posix()
            print(
                f"now in .{dispname} [lvl={LEVEL} dirs={len(dirnames)} files={len(filenames)}]"
            )

            for subdir in dirnames:

                # do not put git subfolders
                if subdir.startswith(".git"):
                    continue

                # do not put python build/cache folders
                if subdir in ["build", "__pycache__"]:
                    continue

                # do not archive static web files at toplevel
                # do not recurse in venv ( pycharm ? )
                if LEVEL == 0:
                    if subdir == "static":
                        HAS_STATIC = True
                        continue

                    if subdir == "venv":
                        print(
                            """
    ===================================================================
        Not packing venv. if non stdlib pure python modules were used
        they should be in game folder not venv install ( for now ).
    ===================================================================
"""
                        )
                        continue

                # recurse
                zfolders.append(subdir)
                pack_files(
                    zf, p_dirname, zfolders, p_dirname.joinpath(subdir).as_posix()
                )

            for f in filenames:
                # do not pack ourself
                if f.endswith(".apk"):
                    continue

                # skip pngquant optimized cache files
                if f.endswith("-pygbag.png"):
                    continue

                # skip wav/mp3 converted to ogg optimized cache files
                if f.endswith(".wav"):
                    if Path(f"{f}.ogg").is_file():
                        WAVOPT.append(f)
                        continue
                    else:
                        print(
                            """
    ===============================================================
        using .wav format in assets for web publication
        has a serious performance/size hit, prefer .ogg format
    ===============================================================
"""
                        )

                if f.endswith(".mp3"):
                    if Path(f"{f}.ogg").is_file():
                        MP3OPT.append(f)
                        continue
                    else:
                        print(
                            """
    ===============================================================
        using .mp3 format in assets for web publication
        has a serious compatibility problem amongst browsers
        prefer .ogg format
    ===============================================================
"""
                        )

                if f.endswith(".gitignore"):
                    continue

                if Path(f).is_symlink():
                    print("sym", f)

                if not os.path.isfile(f):
                    continue

                if LEVEL == 0 and f == "main.py":
                    HAS_MAIN = True

                # folders to skip __pycache__
                # extensions to skip : pyc pyx pyd pyi
                if not f.count("."):
                    print(
                        f"""
    ==================================================================
    {f} has no extension
    ==================================================================
                    """
                    )
                    zpath = list(zfolders)
                    zpath.append(f)
                    src = "/".join(zpath)
                    name = f
                    ext = ""
                else:

                    name, ext = f.rsplit(".", 1)
                    ext = ext.lower()

                    if ext in ["pyc", "pyx", "pyd", "pyi", "exe", "log"]:
                        continue

                zpath = list(zfolders)
                zpath.append(f)
                src = "/".join(zpath)

                if ext == "png":
                    maybe = f"{name}-pygbag.png"
                    if Path(maybe).is_file():
                        PNGOPT.append(f)
                        f = maybe

                if not src in ASSETS:
                    # print( zpath , f )
                    zf.write(f, src)
                    ASSETS.append(src)
                    COUNTER += 1

            break

    finally:
        os.chdir(parent)
        zfolders.pop()
        LEVEL -= 1


async def archive(apkname, target_folder, build_dir=None):
    global COUNTER, TRUNCATE, ASSETS, HAS_MAIN, HAS_STATIC
    TRUNCATE = len(target_folder.as_posix())
    if build_dir:
        apkname = build_dir.joinpath(apkname).as_posix()

    walked = []
    for folder, filenames in gather(target_folder):
        walked.append([folder, filenames])
        sched_yield()

    filtered = []
    last = ""
    for infolder, fullpath in filter(walked):
        if last != infolder:
            print(f"Now in {infolder}")
            last = infolder

        # print(" " * 4, fullpath)
        filtered.append(fullpath)
        sched_yield()

    packlist = []
    for filename in optimize(filtered):
        packlist.append(filename)
        sched_yield()

    try:
        with zipfile.ZipFile(
            apkname, mode="x", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as zf:
            pack_files(zf, Path.cwd(), ["assets"], target_folder)
    except TypeError:
        # 3.6 does not support compresslevel
        with zipfile.ZipFile(apkname, mode="x", compression=zipfile.ZIP_DEFLATED) as zf:
            pack_files(zf, Path.cwd(), ["assets"], target_folder)
    print(COUNTER)

    if not (HAS_MAIN or HAS_STATIC):
        print("Warning : this apk has no startup file (main.py or static )")

    if len(PNGOPT):
        print(f"INFO: {len(PNGOPT)} png format files were optimized for packing")

    if len(WAVOPT):
        print(f"INFO: {len(WAVOPT)} wav format files were swapped for packing")

    if len(MP3OPT):
        print(f"INFO: {len(MP3OPT)} mp3 format files were swapped for packing")


async def web_archive(apkname, build_dir):
    archfile = build_dir.with_name("web.zip")
    if archfile.is_file():
        archfile.unlink()

    with zipfile.ZipFile(archfile, mode="x", compression=zipfile.ZIP_STORED) as zf:
        for f in ("index.html", "favicon.png", apkname):
            zf.write(build_dir.joinpath(f), f)
