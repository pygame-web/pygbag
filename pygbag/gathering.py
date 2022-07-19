from os import walk
from pathlib import Path

class Error(Exception):
    pass


def gather(root:Path,*kw):
    if root.is_file():
        if root.name == "main.py":
            raise Error("project must be a folder or an archive")


    for current, dirnames, filenames in walk(root):
        print(current, len(dirnames), len(filenames))
        yield
