#!/bin/bash
reset

export LC_ALL=C
export SDKROOT=${SDKROOT:-/opt/python-wasm-sdk}

if $CI
then
    echo "pass (apt)"
else
    sudo apt install -y bash git curl lz4 pv
fi

BUILDS=${BUILDS:-3.12 3.11 3.10}

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
    . ${CONFIG}

    echo "
    * building loader for CPython${PYMAJOR}.${PYMINOR} $PYBUILD
    "

    ./scripts/build-loader.sh
done












#


