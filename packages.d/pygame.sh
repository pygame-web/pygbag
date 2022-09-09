#!/bin/bash

export SDKROOT=${SDKROOT:-/opt/python-wasm-sdk}
export CONFIG=${CONFIG:-$SDKROOT/config}


. ${CONFIG}

echo "

    * building pygame for ${CIVER}, PYBUILD=$PYBUILD => CPython${PYMAJOR}.${PYMINOR}
            PYBUILD=$PYBUILD
            EMFLAVOUR=$EMFLAVOUR
            SDKROOT=$SDKROOT
            SYS_PYTHON=${SYS_PYTHON}

"


if [ -f dev ]
then
    DEV=true
else
    if echo $GITHUB_WORKSPACE|grep wip
    then
        DEV=true
    else
        DEV=${DEV:-false}
    fi

    # update cython
    CYTHON=$($SYS_PYTHON -m cython -V 2>&1)
    if echo $CYTHON| grep -q 3.0.0a11$
    then
        echo "  * not upgrading cython $CYTHON"
    else
        echo "  * upgrading cython $CYTHON to 3.0.0a11+"
        $SYS_PYTHON -m pip install --user --upgrade git+https://github.com/cython/cython.git
    fi
fi

mkdir -p src
pushd $(pwd)/src

if true
then
    echo "
    * using pygame-wasm WIP repo
    "
    PG_BRANCH="pygame-wasm"
    PG_GIT="https://github.com/pmp-p/pygame-wasm.git"
else
    echo "
    * using main pygame repo
    "
    PG_BRANCH="main"
    PG_GIT="https://github.com/pygame/pygame.git"
fi


if [ -d pygame-wasm ]
then
    pushd $(pwd)/pygame-wasm
    git restore .
    git pull
    rm -rf build Setup
else
    git clone --no-tags --depth 1 --single-branch --branch $PG_BRANCH $PG_GIT pygame-wasm
    pushd $(pwd)/pygame-wasm
fi


touch $(find | grep pxd$)
if $SYS_PYTHON setup.py cython_only
then
    # do not link -lSDL2 some emmc versions will think .so will use EM_ASM
    SDL_IMAGE="-s USE_SDL=2 -lfreetype -lwebp"

    export CFLAGS="-DHAVE_STDARG_PROTOTYPES -DBUILD_STATIC -DSDL_NO_COMPAT $SDL_IMAGE"

    export EMCC_CFLAGS="-I$PREFIX/include/SDL2 -I${SDKROOT}/emsdk/upstream/emscripten/cache/sysroot/include/freetype2 -ferror-limit=1 -fpic -Wno-unused-command-line-argument -Wno-unreachable-code-fallthrough"

    export CC=emcc

    [ -d build ] && rm -r build
    [ -f Setup ] && rm Setup
    [ -f ${SDKROOT}/prebuilt/emsdk/libpygame${PYBUILD}.a ] && rm ${SDKROOT}/prebuilt/emsdk/libpygame${PYBUILD}.a

    if $SDKROOT/python3-wasm setup.py -config -auto -sdl2
    then
        $SDKROOT/python3-wasm setup.py build -j1 || echo "encountered some build errors"

        OBJS=$(find build/temp.wasm32-*/|grep o$)



        $SDKROOT/emsdk/upstream/emscripten/emar rcs ${SDKROOT}/prebuilt/emsdk/libpygame${PYBUILD}.a $OBJS
        for obj in $OBJS
        do
            echo $obj
        done

        # to install python part (unpatched)
        cp -r src_py/. ${PKGDIR:-${SDKROOT}/prebuilt/emsdk/${PYBUILD}/site-packages/pygame/}


    else
        echo "ERROR: pygame configuration failed"
        exit 109
    fi

else
    echo "cythonize failed"
    exit 114
fi

popd
popd









