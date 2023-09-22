#!/bin/bash

export SDKROOT=${SDKROOT:-/opt/python-wasm-sdk}
export CONFIG=${CONFIG:-$SDKROOT/config}


. ${CONFIG}

echo "

    * building HPy for ${CIVER}, PYBUILD=$PYBUILD => CPython${PYMAJOR}.${PYMINOR}
            PYBUILD=$PYBUILD
            EMFLAVOUR=$EMFLAVOUR
            SDKROOT=$SDKROOT
            SYS_PYTHON=${SYS_PYTHON}

" 1>&2

if pushd /opt/python-wasm-sdk/build/cpython-wasm
then
    OBJS="build/temp.emscripten-wasm32-3.11/opt/python-wasm-sdk/src/Python-3.11.5/Modules/_ctypes/_ctypes.o \
 build/temp.emscripten-wasm32-3.11/opt/python-wasm-sdk/src/Python-3.11.5/Modules/_ctypes/callbacks.o \
 build/temp.emscripten-wasm32-3.11/opt/python-wasm-sdk/src/Python-3.11.5/Modules/_ctypes/callproc.o \
 build/temp.emscripten-wasm32-3.11/opt/python-wasm-sdk/src/Python-3.11.5/Modules/_ctypes/cfield.o \
 build/temp.emscripten-wasm32-3.11/opt/python-wasm-sdk/src/Python-3.11.5/Modules/_ctypes/stgdict.o"

    $SDKROOT/emsdk/upstream/emscripten/emar rcs ${SDKROOT}/prebuilt/emsdk/lib_ctypes${PYBUILD}.a $OBJS
fi

