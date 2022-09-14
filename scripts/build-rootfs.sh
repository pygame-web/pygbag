#!/bin/bash

export SDKROOT=${SDKROOT:-/opt/python-wasm-sdk}

. ${CONFIG:-$SDKROOT/config}



mkdir -p build

FS=build/fs


echo "
    * packing minimal stdlib for
        PYTHON=$HPY
        FS=$FS
"



$HPY -v <<END 2>&1 | tee log |grep py$ > $FS
from __future__ import annotations
import sys

M1='os, json, builtins, shutil, zipimport, time, trace, traceback, '
M2='asyncio, inspect, _thread, importlib, ctypes, tomllib'
for mod in (M1+M2).split(', '):
    try:
        __import__(mod)
    except:
        pass
try:
    sys.stdout.reconfigure(encoding='utf-16')
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass


# for dom event subscriptions and js interface
import webbrowser
import platform

# intaller "cp437"
import compileall, csv, configparser, zlib

# micropip
import importlib.metadata

# pgex
import typing
try:
    from typing import tuple
except:
    pass

# for wget to overload urlretrieve
import urllib.request

# nodezator
from logging.handlers import RotatingFileHandler
from colorsys  import rgb_to_hls, hls_to_rgb
import xml.dom.minidom
from xml.dom import expatbuilder
import pydoc

# rich
import zlib

# pygame_gui
import html.parser
import importlib.readers

#pymunk tests
import unittest, locale

#pymunk4
import imp, platform

#pymunk6
import numbers, random

#pgzero
import hashlib, queue, pkgutil

#numpy
import pathlib

# cffi
import copy

#curses
import curses

#pytmx
import gzip
import zlib
from xml.etree import ElementTree
import distutils.spawn

# for FS
import tempfile




#pygame_gui
import importlib.resources

if 0:
    import cffi
    from cffi import FFI
    ffi = FFI()
END

echo "=============================="
$HPY -u -B <<END
import sys, os
stdlp=""
with open("build/stdlib.list","w") as tarlist:
    sysconf = "_sysconfigdata__linux_$(arch)-linux-gnu.py"
    with open("$FS") as fs:
        for l in fs.readlines():
            #print( l.strip() )
            if l.find('/')<0:
                continue
            _,trail = l.strip().split('/',1)
            stdlp, name = trail.rsplit('usr/lib/',1)

            #print (stdlp, name)
            #if name.find('asyncio/unix_events.py')>0:
            #    continue

            if name.find('/site-packages/setuptools/')>0:
                continue

            if name.find('/site-packages/pkg_resources/_vendor/')>0:
                continue

            if name.endswith(sysconf):
                name = name.replace(sysconf,"_sysconfigdata__emscripten_wasm32-emscripten.py")

            name = name.replace('asyncio/selector_','asyncio/wasm_')
            print(name, file=tarlist )
        else:
            stdlp = stdlp.replace('$(arch)','emsdk')
            #print(stdlp)
            tarcmd=f"tar --directory=/{stdlp}usr/lib --files-from=build/stdlib.list -cf build/stdl.tar"
            print(tarcmd)
os.system(tarcmd)
END


echo "=============================="
grep -v ^import log |grep -v ^#
echo "=============================="
mkdir -p build/stdlib-rootfs
tar xvf build/stdl.tar -C build/stdlib-rootfs | wc -l
rm build/stdl.tar
du -hs build/stdlib-rootfs/python${PYBUILD}


