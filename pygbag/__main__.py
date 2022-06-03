import sys
from .__init__ import __version__

print(f" *pygbag {__version__}*")

from pathlib import Path
from .app import main, main_run

if __name__ == "__main__":
    main_run(Path(sys.argv[-1]).resolve())
