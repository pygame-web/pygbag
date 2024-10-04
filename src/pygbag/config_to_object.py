# config-to-object 1.0.3 License: MIT License (MIT)
# Original Author: Yannik Keller
# https://pypi.org/project/config-to-object/
# https://github.com/yannikkellerde/config_to_object


from typing import NamedTuple
import sys
from ast import literal_eval
from collections import OrderedDict, namedtuple
import configparser
import os

def is_named_tuple_instance(x):
    t = type(x)
    b = t.__bases__
    if len(b) != 1 or b[0] != tuple: return False
    f = getattr(t, '_fields', None)
    if not isinstance(f, tuple): return False
    return all(type(n)==str for n in f)


def _do_recur(config:NamedTuple,force_name=None):
    if force_name is None:
        name = type(config).__name__
    else:
        name = force_name
    dic = config._asdict()
    classes = []
    myclass_lines = [f"class {name}(NamedTuple):"]
    for key,value in dic.items():
        if is_named_tuple_instance(value):
            classes.append(_do_recur(value))
            myclass_lines.append(f"    {key}:{type(value).__name__}")
        else:
            if type(value) in (list,tuple):
                tname = type(value).__name__
                tlist = [type(x) for x in value]
                if len(value)>0 and tlist.count(tlist[0]) == len(tlist):
                    myclass_lines.append(f"    {key}:{tname.capitalize()}[{type(value[0]).__name__}]")
                else:
                    myclass_lines.append(f"    {key}:{tname}")
            else:
                myclass_lines.append(f"    {key}:{type(value).__name__}")
    return "\n\n".join(classes+["\n".join(myclass_lines)])


def create_config_type_file(config:NamedTuple,fname:str,obj_name=None):
    lines = ["# Automatically generated type hinting file for a .ini file",
             "# Generated with config-to-object https://pypi.org/project/config-to-object/1.0.0/",
             '# Run "ini_typefile your_config.ini type_file.py" to create a new type file',
             "",
             "from typing import NamedTuple, List, Tuple",
             ""]

    to_write = "\n".join(lines+[_do_recur(config,obj_name)])
    with open(fname,"w") as f:
        f.write(to_write)

def multidict_to_namedtuple(dic:dict,name:str) -> NamedTuple:
    for key in dic:
        if type(dic[key]) == dict or type(dic[key]) == OrderedDict:
            dic[key] = multidict_to_namedtuple(dic[key],key)
    return namedtuple(name,dic.keys())(*dic.values())

def load_config(filename:str,comment_prefix=";",encoding=None) -> NamedTuple:
    if type(filename) != str:
        raise ValueError("Expected filename to be of type str. Found {} instead".format(type(filename)))
    if not os.path.isfile(filename):
        raise ValueError("Could not find file "+filename)
    config_obj = configparser.ConfigParser(inline_comment_prefixes=comment_prefix)
    config_obj.read(filename,encoding=encoding)
    config_dict = config_obj._sections
    for key in config_dict:
        for key2 in config_dict[key]:
            try:
                config_dict[key][key2] = literal_eval(config_dict[key][key2])
            except:
                pass
    return multidict_to_namedtuple(config_dict,"Config")

def command_line_config():
    if len(sys.argv) < 3:
        raise ValueError("Usage: ini_typefile ConfigFilename OutputFilename")
    create_config_type_file(load_config(sys.argv[1]),sys.argv[2])
