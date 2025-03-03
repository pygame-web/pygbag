from pathlib import Path

dbg = False

# q:what to do with the extreme case $HOME/main.py ?
# or folders > 512MiB total
# a: maybe break on too many files around the yield


IGNORE = """
/.mypy_cache
/.ssh
/.local
/.config
/.git
/.github
/.vscode
/.idea
/.DS_Store
/dist
/build
/venv
/ignore
/static
/ATTIC
""".splitlines()
# "gltf", "glb",
SKIP_EXT = ["lnk", "pyc", "pyx", "pyd", "pyi", "exe", "bak", "log", "blend", "blend1", "DS_Store"]


def filter(walked, ignore_dirs, ignore_files):
    global dbg, IGNORE, SKIP_EXT, IGNORE_FILES
    IGNORE.extend(ignore_dirs)

    IGNORE_FILES = ignore_files

    for folder, filenames in walked:
        blocking = False

        fx = Path(folder).as_posix()

        # ignore .* folders
        if fx.startswith("."):
            continue

        for block in IGNORE:
            if not block:
                continue

            if folder.match(block):
                if dbg:
                    print("REJ 1", folder)
                blocking = True
                break

            if fx.startswith(f"{block}/"):
                if dbg:
                    print("REJ 2", folder)
                blocking = True
                break

        if blocking:
            continue

        for filename in filenames:
            fnx = Path(filename).as_posix()

            # ignore .* files
            if fnx.startswith("."):
                continue

            if fnx in [".gitignore"]:
                if dbg:
                    print("REJ 3", folder, filename)
                continue

            if fnx in IGNORE_FILES:
                continue

            ext = fnx.rsplit(".", 1)[-1].lower()
            if ext in SKIP_EXT:
                if dbg:
                    print("REJ 4", folder, filename)
                continue

            yield Path(folder), Path(folder).joinpath(filename)
