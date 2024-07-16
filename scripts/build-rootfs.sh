#!/bin/bash

. scripts/vendoring.sh

. ${CONFIG:-$SDKROOT/config}


mkdir -p build

FS=build/fs


echo "
    * packing minimal stdlib for
        PYTHON=$HPY
        FS=$FS
        PYTHONPYCACHEPREFIX=$PYTHONPYCACHEPREFIX
"

if echo $PYTHONPYCACHEPREFIX |grep -q $SDKROOT
then
    echo    "
    * cleaning up compiled pyc if any in $PYTHONPYCACHEPREFIX/./$SDKROOT/
"
    rm -rf $PYTHONPYCACHEPREFIX/./$SDKROOT/
fi


$HPY -B -v <<END 2>&1 | tee log |grep py$ > $FS
from __future__ import annotations
import sys

M1='os, json, builtins, shutil, zipimport, time, trace, traceback, '
M2='asyncio, inspect, _thread, importlib, ctypes, tomllib, pathlib'
for mod in (M1+M2).split(', '):
    try:
        __import__(mod)
    except:
        pass
try:
    # installer
    sys.stdout.reconfigure(encoding='cp437')
    # bokeh
    sys.stdout.reconfigure(encoding='unicode-escape')
    sys.stdout.reconfigure(encoding='utf-16')
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

import sysconfig
sysconfig.get_paths()

import multiprocessing.connection

# sockets ????
import asyncio.selector_events

import multiprocessing

# mypy
import typing
# ? _extensions

# for dom event subscriptions and js interface
import webbrowser
import platform

# for pyodide runPython emulation
from textwrap import dedent

# FIXME: because _sqlite3 is builtins anyway ?
import sqlite3

# for pygame-script FS
import tempfile

# for console
import code

# for wget to overload urlretrieve
import urllib.request

# installer "cp437"
import compileall, csv, configparser
from email.policy import compat32

#telemetrix
import concurrent.futures.thread

# micropip
import importlib.metadata

# pygame_gui
import html.parser
import importlib.readers

#pymunk+tests
import unittest, locale
import platform
import numbers, random

#pgzero
import hashlib, queue, pkgutil

#pytmx
import gzip
import zlib
from xml.etree import ElementTree
import distutils.spawn

#matplotlib
import uuid

# psycopg
import zoneinfo

# pandas
import tarfile

#arcade
import ctypes.util

#pygame_gui
import importlib.resources

#curses
try:
    import curses
except:
    print('_curses not built')

#rich
import getpass
import fractions

#nurses_2
import tty

# cffi
import copy

# datetime
import datetime
import _strptime

# numpy
import secrets

# HPy
import plistlib
from pkg_resources import resource_filename

# netpbm
from mimetypes import guess_type
from pprint import pprint

# pgex
import typing
try:
    from typing import tuple
except:
    pass

# nodezator
from logging.handlers import RotatingFileHandler
from colorsys  import rgb_to_hls, hls_to_rgb
import xml.dom.minidom
from xml.dom import expatbuilder
import pydoc

# Box2D
import optparse

# bokeh
import hmac

#ursina, not in 3.13
# import imghdr

# pep722
import pyparsing
import packaging.requirements
#import installer

try:
    import imp
except:
    # python 3.12 !
    pass

if 0:
    import cffi
    from cffi import FFI
    ffi = FFI()
END

echo "-----------------------------------------------------------"
$HPY -u -I -B <<END
import sys, os
stdlp=""

if os.environ.get('PYBUILD','')=='3.13':
    SCD="_sysconfigdata_t"
else:
    SCD="_sysconfigdata_"

with open("build/stdlib.list","w") as tarlist:

    sysconf = f"{SCD}_linux_$(arch)-linux-gnu.py"
    with open("$FS") as fs:
        for l in fs.readlines():
            #print( l.strip() )
            if l.find('/')<0:
                continue

            _,trail = l.strip().split('/',1)

            try:
                stdlp, name = trail.rsplit('usr/lib/',1)
            except Exception as x:
                print(f"ERROR {l=}", x, file=sys.stderr)
                print(sys.path, file=sys.stderr)
                continue


            #print (stdlp, name)
            #if name.find('asyncio/unix_events.py')>0:
            #    continue

            if name.find('/site-packages/setuptools/')>0:
                continue

            if name.find('/site-packages/pkg_resources/_vendor/')>0:
                continue

            if name.endswith(sysconf):
                name = name.replace(sysconf,"_sysconfigdata__emscripten_wasm32-emscripten.py")

            if name.find('asyncio/selector_')>=0:
                #print(name, file=tarlist )
                name = name.replace('asyncio/selector_','asyncio/wasm_')
            print(name, file=tarlist )
        else:
            stdlp = stdlp.replace('$(arch)','emsdk')
            print(stdlp)
            tarcmd=f"tar --directory=/{stdlp}usr/lib --files-from=build/stdlib.list -cf build/stdl.tar"
            print(tarcmd)
os.system(tarcmd)
END

echo "*******************************************"
grep -v ^import log |grep -v ^#
echo "*******************************************"
mkdir -p build/stdlib-rootfs
tar xvf build/stdl.tar -C build/stdlib-rootfs | wc -l
rm build/stdl.tar
du -hs build/stdlib-rootfs/python${PYBUILD}


