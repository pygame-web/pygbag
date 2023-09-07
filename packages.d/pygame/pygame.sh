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

" 1>&2



if [ -f /pp ]
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
    TEST_CYTHON=$($HPY -m cython -V 2>&1)
    if echo $TEST_CYTHON| grep -q 3.0.0$
    then
        echo "  * not upgrading cython $TEST_CYTHON
" 1>&2
    else
        echo "  * upgrading cython $TEST_CYTHON to 3.0.0
"  1>&2
        #$SYS_PYTHON -m pip install --user --upgrade git+https://github.com/cython/cython.git
        CYTHON=${CYTHON:-Cython-3.0.0-py2.py3-none-any.whl}
        pushd build
        wget -q -c https://github.com/cython/cython/releases/download/3.0.0/${CYTHON}
        $HPY -m pip install $CYTHON
        popd

    fi
fi

mkdir -p src
pushd $(pwd)/src


echo "
* using main pygame-ce repo
" 1>&2
PG_BRANCH="main"
PG_GIT="https://github.com/pygame-community/pygame-ce.git"

if ${CI:-true}
then
    if [ -d pygame-wasm ]
    then
        pushd $(pwd)/pygame-wasm
        git restore .
        git pull
    else
        git clone --no-tags --depth 1 --single-branch --branch $PG_BRANCH $PG_GIT pygame-wasm
        pushd $(pwd)/pygame-wasm
    fi

    #unsure
    wget -O- https://patch-diff.githubusercontent.com/raw/pmp-p/pygame-ce-wasm/pull/3.diff | patch -p1


    # cython3 / merged
    # wget -O- https://patch-diff.githubusercontent.com/raw/pygame-community/pygame-ce/pull/2395.diff | patch -p1


    # zerodiv mixer.music / merged
    # wget -O - https://patch-diff.githubusercontent.com/raw/pygame-community/pygame-ce/pull/2426.diff | patch -p1

    # weird exception not raised correctly in test/pixelcopy_test
    patch -p1 <<END
diff --git a/src_c/pixelcopy.c b/src_c/pixelcopy.c
index e33eae33..f5f6697e 100644
--- a/src_c/pixelcopy.c
+++ b/src_c/pixelcopy.c
@@ -485,6 +485,7 @@ array_to_surface(PyObject *self, PyObject *arg)
     }

     if (_validate_view_format(view_p->format)) {
+PyErr_SetString(PyExc_ValueError, "Unsupported array item type");
         return 0;
     }

END


else
    pushd $(pwd)/pygame-wasm
    echo "






                NOT UPDATING PYGAME, TEST MODE






"
    read

fi

# test patches go here
# ===================
# patch -p1 <<END

# END
    rm -rf build Setup
# ===================



pwd
env|grep PY

touch $(find | grep pxd$)
if $HPY setup.py cython_only
then
    # do not link -lSDL2 some emmc versions will think .so will use EM_ASM
    #SDL_IMAGE="-s USE_SDL=2 -lfreetype -lwebp"
    SDL_IMAGE="-lSDL2 -lfreetype -lwebp"

    export CFLAGS="-DSDL_NO_COMPAT $SDL_IMAGE"
    EMCC_CFLAGS="-I${SDKROOT}/emsdk/upstream/emscripten/cache/sysroot/include/freetype2"
    EMCC_CFLAGS="$EMCC_CFLAGS -mnontrapping-fptoint -mno-reference-types -sWASM_BIGINT=0 -sMIN_SAFARI_VERSION=120000"
    EMCC_CFLAGS="$EMCC_CFLAGS -I$PREFIX/include/SDL2"
    EMCC_CFLAGS="$EMCC_CFLAGS -Wno-unused-command-line-argument"
    EMCC_CFLAGS="$EMCC_CFLAGS -Wno-unreachable-code-fallthrough"
    EMCC_CFLAGS="$EMCC_CFLAGS -Wno-unreachable-code"
    EMCC_CFLAGS="$EMCC_CFLAGS -Wno-parentheses-equality"
    EMCC_CFLAGS="$EMCC_CFLAGS -Wno-unknown-pragmas"

    export EMCC_CFLAGS="$EMCC_CFLAGS -DHAVE_STDARG_PROTOTYPES -DBUILD_STATIC -ferror-limit=1 -fpic"

    export CC=emcc

    # remove SDL1 for good
    rm -rf /opt/python-wasm-sdk/emsdk/upstream/emscripten/cache/sysroot/include/SDL

    [ -d build ] && rm -r build
    [ -f Setup ] && rm Setup
    [ -f ${SDKROOT}/prebuilt/emsdk/libpygame${PYBUILD}.a ] && rm ${SDKROOT}/prebuilt/emsdk/libpygame${PYBUILD}.a

    if $SDKROOT/python3-wasm setup.py -config -auto -sdl2
    then
        $SDKROOT/python3-wasm setup.py build -j1 || echo "encountered some build errors" 1>&2

        OBJS=$(find build/temp.wasm32-*/|grep o$)


        $SDKROOT/emsdk/upstream/emscripten/emar rcs ${SDKROOT}/prebuilt/emsdk/libpygame${PYBUILD}.a $OBJS
        for obj in $OBJS
        do
            echo $obj
        done

        # to install python part (unpatched)
        cp -r src_py/. ${PKGDIR:-${SDKROOT}/prebuilt/emsdk/${PYBUILD}/site-packages/pygame/}

        # prepare testsuite
        [ -d ${ROOT}/build/pygame-test ] && rm -fr ${ROOT}/build/pygame-test
        mkdir ${ROOT}/build/pygame-test
        cp -r test ${ROOT}/build/pygame-test/test
        cp -r examples ${ROOT}/build/pygame-test/test/
        cp ${ROOT}/packages.d/pygame/tests/main.py ${ROOT}/build/pygame-test/

    else
        echo "ERROR: pygame configuration failed" 1>&2
        exit 109
    fi

else
    echo "cythonize failed" 1>&2
    exit 114
fi

popd
popd

TAG=${PYMAJOR}${PYMINOR}


echo "FIXME: build wheel"


if [ -d testing/pygame_static-1.0-cp${TAG}-cp${TAG}-wasm32_mvp_emscripten ]
then
    TARGET=$(pwd)/testing/pygame_static-1.0-cp${TAG}-cp${TAG}-wasm32_mvp_emscripten/pygame_static.cpython-${TAG}-wasm32-emscripten.so

    . ${SDKROOT}/emsdk/emsdk_env.sh

    [ -f $TARGET ] && rm $TARGET

    emcc -shared -Os -g0 -fpic -o $TARGET $SDKROOT/prebuilt/emsdk/libpygame${PYMAJOR}.${PYMINOR}.a

    if [ -f /data/git/archives/repo/norm.sh ]
    then
        pushd testing/pygame_static-1.0-cp${TAG}-cp${TAG}-wasm32_mvp_emscripten
        /data/git/archives/repo/norm.sh
        rm $TARGET
        popd
    fi
fi






