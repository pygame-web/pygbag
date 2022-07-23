import asyncio
import sys
from .__init__ import __version__

print(f" *pygbag {__version__}*")

from pathlib import Path
from .app import main_run

if __name__ == "__main__":
    asyncio.run(main_run(Path(sys.argv[-1]).resolve()))
