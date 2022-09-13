#!/bin/bash
reset
export PACKAGES=${PACKAGES:-pygame}
export SDK_VERSION=${SDK_VERSION:-3.1.19.1}
export CYTHON=${CYTHON:-Cython-3.0.0a11-py2.py3-none-any.whl}
BUILDS=${BUILDS:-3.12 3.11 3.10}

export CI=${CI:-false}
export LC_ALL=C
export SDKROOT=${SDKROOT:-/opt/python-wasm-sdk}
export SYS_PYTHON=${SYS_PYTHON:-$(which python3)}
echo "
====================================================
    Building pygbag loader
    ________________________________________
    statically built modules: $PACKAGES
    with SDK $SDK_VERSION
    python versions : $BUILDS
    Cython release: $CYTHON
    CI=$CI
====================================================
"



chmod +x *sh scripts/*.sh packages.d/*sh

for PYBUILD in $BUILDS
do
    export PYBUILD
    ./scripts/build-pkg.sh
done


echo "
    * building Loaders
"

echo TODO date +"%Y.%m"

for PYBUILD in $BUILDS
do
    export PYBUILD
    . ${CONFIG:-$SDKROOT/config}

    echo "
    * building loader for CPython${PYMAJOR}.${PYMINOR} $PYBUILD
    "

    ./scripts/build-loader.sh
done












#


