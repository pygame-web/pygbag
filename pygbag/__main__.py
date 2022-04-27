print(" *pygbag*")
import sys
from . import pack

from pathlib import Path

archname = Path(sys.argv[-1]).name
print(f"""
archname={archname}
""")

pack.archive(f"{archname}.apk")
