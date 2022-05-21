import sys, os
import zipfile
from pathlib import Path

COUNTER = 0
TRUNCATE = 0
ASSETS = []
HAS_STATIC = False
HAS_MAIN = False


def pack_files(zf, pushpopd, newpath):
    global COUNTER, TRUNCATE, ASSETS, HAS_STATIC, HAS_MAIN

    if str(newpath).find("/.git") >= 0:
        return

    os.chdir(newpath)

    for dirname, dirnames, filenames in os.walk(newpath):

        # do not put git subfolders
        if dirname.find("/.git") >= 0:
            continue

        if dirname.endswith("/build"):
            continue

        if dirname.endswith("/static"):
            HAS_STATIC = True
            continue

        try:
            os.chdir(dirname)
            print(f"now in .{dirname[TRUNCATE:] or '/'}")
        except:
            print("Invalid Folder :", pushpopd, newpath)

        for f in filenames:
            # do not pack ourself
            if f.endswith(".apk"):
                continue

            if f.endswith(".gitignore"):
                continue

            if not os.path.isfile(f):
                continue

            if f.endswith("/main.py"):
                HAS_MAIN = True

            # ext = f.rsplit(".", 1)[-1].lower()

            src = os.path.join(os.getcwd(), f)
            src = f"assets{src[TRUNCATE:]}"

            if not src in ASSETS:
                zf.write(f, src)
                # print(src)
                ASSETS.append(src)

                COUNTER += 1

        for subdir in dirnames:
            # do not archive static web files
            if subdir == "static":
                HAS_STATIC = True
                continue

            if subdir == "build":
                continue

            if subdir != ".git":
                pack_files(zf, os.getcwd(), subdir)

    os.chdir(pushpopd)


def archive(apkname, target_folder, build_dir=None):
    global COUNTER, TRUNCATE, ASSETS, HAS_MAIN, HAS_STATIC
    TRUNCATE = len(target_folder.as_posix())
    if build_dir:
        apkname = build_dir.joinpath(apkname).as_posix()

    try:
        with zipfile.ZipFile(
            apkname, mode="x", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as zf:
            pack_files(zf, Path.cwd(), target_folder)
    except TypeError:
        # 3.6 does not support compresslevel
        with zipfile.ZipFile(apkname, mode="x", compression=zipfile.ZIP_DEFLATED) as zf:
            pack_files(zf, Path.cwd(), target_folder)
    print(COUNTER)

    if not (HAS_MAIN or HAS_STATIC):
        print("Warning : this apk has no startup file (main.py or static )")
