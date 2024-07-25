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
/.venv
/.tox
/.DS_Store
/dist
/build
/venv
/ignore
/static
/ATTIC
""".strip().split(
    "\n"
)

SKIP_EXT = ["lnk", "pyc", "pyx", "pyd", "pyi", "exe", "bak", "log", "blend", "DS_Store"]


def filter(walked):
    global dbg, IGNORE, SKIP_EXT
    for folder, filenames in walked:
        blocking = False

        for block in IGNORE:
            if not block:
                continue
            if folder.match(block):
                if dbg:
                    print("REJ 1", folder)
                blocking = True
                break

            fx = folder.as_posix()

            if fx.startswith(f"{block}/"):
                if dbg:
                    print("REJ 2", folder)
                blocking = True
                break

        if blocking:
            continue

        for filename in filenames:
            if filename in [".gitignore"]:
                if dbg:
                    print("REJ 3", folder, filename)
                continue

            ext = filename.rsplit(".", 1)[-1].lower()
            if ext in SKIP_EXT:
                if dbg:
                    print("REJ 4", folder, filename)
                continue

            yield Path(folder), Path(folder).joinpath(filename)
