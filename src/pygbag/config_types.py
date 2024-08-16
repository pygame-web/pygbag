# Automatically generated type hinting file for a .ini file
# Generated with config-to-object https://pypi.org/project/config-to-object/1.0.0/
# Run "ini_typefile your_config.ini type_file.py" to create a new type file

from typing import NamedTuple, List, Tuple

class DEPENDENCIES(NamedTuple):
    ignoredirs:List[str]
    ignorefiles:List[str]

class Config(NamedTuple):
    DEPENDENCIES:DEPENDENCIES