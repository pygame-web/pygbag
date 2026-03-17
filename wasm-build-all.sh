#!/bin/bash
reset

cp -vf /opt/python-wasm-sdk/emsdk/upstream/emscripten/cache/sysroot/lib/wasm32-emscripten/pic/libSDL2_mixer-ogg.a /opt/python-wasm-sdk/emsdk/upstream/emscripten/cache/sysroot/lib/wasm32-emscripten/pic/libSDL2_mixer_ogg.a

export CI=${CI:-false}

export WORKSPACE=${GITHUB_WORKSPACE:-$(pwd)}

export BUILDS=${BUILDS:-3.12 3.13 3.14}

export STATIC=${STATIC:-true}

export PYGBAG_PKG=${PYGBAG_VER:-0.9.4}

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
    * building ${PYGBAG_PKG} loader for CPython${PYMAJOR}.${PYMINOR} $PYBUILD
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





if [ -d ../cdn ]
then
echo "

_____________________________________________________________________
  setting up cdn with ${PYGBAG_PKG}/cpython${PYMAJOR}${PYMINOR}
  in $(realpath ../cdn)
  and mappings for pkg, abi3 + cp???
_____________________________________________________________________

"
    mkdir -p ../cdn/${PYGBAG_PKG}/cpython${PYMAJOR}${PYMINOR}
    rm -f ../cdn/${PYGBAG_PKG}/cpython${PYMAJOR}${PYMINOR}/main.*

    cp -v ./src/pygbag/support/cpythonrc.py static/pythons.js static/favicon.png ../cdn/${PYGBAG_PKG}/

    cp -fv build/web/archives/0.0/cpython${PYMAJOR}${PYMINOR}/main.* ../cdn/${PYGBAG_PKG}/cpython${PYMAJOR}${PYMINOR}/

    #mv -v external/pygame-wasm/dist/*whl

    mv -v external/*/dist/*-abi3-wasm32_bi_emscripten.whl ../cdn/abi3/
    mv -v external/*/dist/*cp3*-wasm32_bi_emscripten.whl ../cdn/cp${PYMAJOR}${PYMINOR}-${PYGBAG_PKG}/

    # use pygbag module from source, not any already installed.
    export PYTHONPATH=$(pwd)/src

    pushd ../cdn
        ${SDKROOT}/devices/$(arch)/usr/bin/python${PYBUILD} ./buildmap.py
    popd

    du -hs /data/git/cdn/${PYGBAG_PKG}/*
fi

