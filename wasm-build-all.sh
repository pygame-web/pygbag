#!/bin/bash
reset

export CI=${CI:-false}

export WORKSPACE=${GITHUB_WORKSPACE:-$(pwd)}

export BUILDS=${BUILDS:-3.12 3.11}

export STATIC=${STATIC:-true}

. scripts/vendoring.sh

chmod +x *sh scripts/*.sh packages.d/*/*sh

for PYBUILD in $BUILDS
do
    export PYBUILD

    if [ -f vendor/vendor.sh ]
    then
        echo "  vendor build"
        if ${ABI3:-false}
        then
        echo "  vendor build (abi3) $PYBUILD"
            if echo $PYBUILD|grep -v -q 3.12$
            then
                echo "abi3 vendor build only, skipping $PYBUILD"
                exit 0
            fi
        fi
    fi

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

if echo "$@"|grep PKPY
then
    ./scripts/build-pkpy.sh
fi



if echo "$@"|grep WAPY
then
    ./scripts/build-wapy2.sh
fi




#


