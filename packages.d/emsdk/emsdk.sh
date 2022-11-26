#!/bin/bash

export SDKROOT=${SDKROOT:-/opt/python-wasm-sdk}
export CONFIG=${CONFIG:-$SDKROOT/config}



. ${CONFIG}



echo "

    * building ${pkg} helper for ${CIVER}, PYBUILD=$PYBUILD => CPython${PYMAJOR}.${PYMINOR}
            PYBUILD=$PYBUILD
            EMFLAVOUR=$EMFLAVOUR
            SDKROOT=$SDKROOT
            SYS_PYTHON=${SYS_PYTHON}

" 1>&2

touch build/void.c

. ${SDKROOT}/emsdk/emsdk_env.sh

emcc -c -o build/void.o build/void.c

$SDKROOT/emsdk/upstream/emscripten/emar rcs\
 ${SDKROOT}/prebuilt/emsdk/lib${pkg}${PYBUILD}.a build/void.o


