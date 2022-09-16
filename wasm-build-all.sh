#!/bin/bash
reset

export CI=${CI:-false}


BUILDS=${BUILDS:-3.12 3.11 3.10}



. scripts/vendoring.sh



chmod +x *sh scripts/*.sh packages.d/*/*sh

for PYBUILD in $BUILDS
do
    export PYBUILD
    if ./scripts/build-pkg.sh
    then
        echo done
    else
        exit 24
    fi
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


