# https://peps.python.org/pep-0722/ – Dependency specification for single-file scripts
# https://peps.python.org/pep-0508/ – Dependency specification for Python Software Packages


import re
import tokenize

import installer
import pyparsing
from packaging.requirements import Requirement


DEPENDENCY_BLOCK_MARKER = r"(?i)^#\s+script\s+dependencies:\s*$"

def read_dependency_block(filename):
    # Use the tokenize module to handle any encoding declaration.
    with tokenize.open(filename) as f:
        # Skip lines until we reach a dependency block (OR EOF).
        for line in f:
            if re.match(DEPENDENCY_BLOCK_MARKER, line):
                break
        # Read dependency lines until we hit a line that doesn't
        # start with #, or we are at EOF.
        for line in f:
            if not line.startswith("#"):
                break
            # Remove comments. An inline comment is introduced by
            # a hash, which must be preceded and followed by a
            # space.
            line = line[1:].split(" # ", maxsplit=1)[0]
            line = line.strip()
            # Ignore empty lines
            if not line:
                continue
            # Try to convert to a requirement. This will raise
            # an error if the line is not a PEP 508 requirement
            yield Requirement(line)


async def check_list(filename):
    print()
    print('-'*11,"required packages",'-'*10)
    for req in read_dependency_block(filename):
        dep = str(req)

        print(dep)
    print('-'*40)
    print()

