from pathlib import Path

dbg = True


def filter(walked):
    global dbg
    for folder, filenames in walked:
        blocking = False

        for block in ["/.git", "/.github", "/build", "/venv"]:
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
            if ext in ["pyc", "pyx", "pyd", "pyi", "exe", "log"]:
                if dbg:
                    print("REJ 4", folder, filename)
                continue

            yield Path(folder), Path(folder).joinpath(filename)
