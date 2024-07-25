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



CYTHON=${CYTHON:-Cython-3.0.10-py2.py3-none-any.whl}
if echo $GITHUB_WORKSPACE|grep wip
then
    DEV=true
else
    DEV=${DEV:-false}

    # update cython
    TEST_CYTHON=$($HPY -m cython -V 2>&1)
    if echo $TEST_CYTHON| grep -q 3.1.0a0$
    then
        echo "  * not upgrading cython $TEST_CYTHON
" 1>&2
    else
        echo "  * upgrading cython $TEST_CYTHON to 3.0.10
"  1>&2

        if echo $PYBUILD|grep -q 3.13$
        then
           echo "

 ================= forcing Cython git instead of release ${CYTHON}  =================

"
            $HPY -m pip install --upgrade --force git+https://github.com/cython/cython.git
            /opt/python-wasm-sdk/python3-wasm -m pip install --upgrade --force --no-build-isolation --force git+https://github.com/cython/cython.git
        else
            echo "

 ================= Using Cython release ${CYTHON}  =================

"
            pushd build
            wget -q -c https://github.com/cython/cython/releases/download/3.0.10/${CYTHON}
            $HPY -m pip install $CYTHON
            popd
        fi

    fi
fi


mkdir -p external
pushd $(pwd)/external


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

    # to upstream after tests
    # done wget -O- https://patch-diff.githubusercontent.com/raw/pmp-p/pygame-ce-wasm/pull/7.diff | patch -p1

    #unsure
    wget -O- https://patch-diff.githubusercontent.com/raw/pmp-p/pygame-ce-wasm/pull/3.diff | patch -p1

    # new cython (git)
    wget -O- https://patch-diff.githubusercontent.com/raw/pmp-p/pygame-ce-wasm/pull/8.diff | patch -p1


    # added Vector2.from_polar and Vector3.from_spherical classmethods
    # breaks, left a review !
    # wget -O- https://patch-diff.githubusercontent.com/raw/pygame-community/pygame-ce/pull/2141.diff | patch -p1


    # cython3 / merged
    # wget -O- https://patch-diff.githubusercontent.com/raw/pygame-community/pygame-ce/pull/2395.diff | patch -p1


    # zerodiv mixer.music / merged
    # wget -O- https://patch-diff.githubusercontent.com/raw/pygame-community/pygame-ce/pull/2426.diff | patch -p1

    patch -p1 <<END
diff --git a/src_c/key.c b/src_c/key.c
index 3a2435d2..a353c24f 100644
--- a/src_c/key.c
+++ b/src_c/key.c
@@ -150,8 +150,10 @@ static PyTypeObject pgScancodeWrapper_Type = {
     PyVarObject_HEAD_INIT(NULL, 0).tp_name = "pygame.key.ScancodeWrapper",
     .tp_repr = (reprfunc)pg_scancodewrapper_repr,
     .tp_as_mapping = &pg_scancodewrapper_mapping,
+/*
     .tp_iter = (getiterfunc)pg_iter_raise,
     .tp_iternext = (iternextfunc)pg_iter_raise,
+*/
 #ifdef PYPY_VERSION
     .tp_new = pg_scancodewrapper_new,
 #endif
END


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

    if echo $PYBUILD|grep -q 3.13$
    then
        echo "


============================================
    Forcing cython regen for 3.13+
============================================


"
        rm src_c/_sdl2/sdl2.c src_c/_sdl2/audio.c src_c/_sdl2/mixer.c src_c/_sdl2/controller_old.c src_c/_sdl2/video.c src_c/pypm.c
    fi

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
    EMCC_CFLAGS="$EMCC_CFLAGS -I$PREFIX/include/SDL2"
    EMCC_CFLAGS="$EMCC_CFLAGS -Wno-unused-command-line-argument"
    EMCC_CFLAGS="$EMCC_CFLAGS -Wno-unreachable-code-fallthrough"
    EMCC_CFLAGS="$EMCC_CFLAGS -Wno-unreachable-code"
    EMCC_CFLAGS="$EMCC_CFLAGS -Wno-parentheses-equality"
    EMCC_CFLAGS="$EMCC_CFLAGS -Wno-unknown-pragmas"


    # FIXME 3.13
    EMCC_CFLAGS="$EMCC_CFLAGS -Wno-deprecated-declarations"



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


SDL2="-sUSE_ZLIB=1 -sUSE_BZIP2=1 -sUSE_LIBPNG -sUSE_SDL=2 -sUSE_SDL_MIXER=2 -lSDL2 -L/opt/python-wasm-sdk/devices/emsdk/usr/lib -lSDL2_image -lSDL2_gfx -lSDL2_mixer -lSDL2_mixer_ogg -lSDL2_ttf -lvorbis -logg -lwebp -ljpeg -lpng -lharfbuzz -lfreetype"
SDL2="$SDL2 -lssl -lcrypto -lffi -lbz2 -lz -ldl -lm"


if [ -d testing/pygame_static-1.0-cp${TAG}-cp${TAG}-wasm32_mvp_emscripten ]
then
    TARGET_FOLDER=$(pwd)/testing/pygame_static-1.0-cp${TAG}-cp${TAG}-wasm32_${WASM_FLAVOUR}_emscripten
    TARGET_FILE=${TARGET_FOLDER}/pygame_static.cpython-${TAG}-wasm32-emscripten.so

    . ${SDKROOT}/emsdk/emsdk_env.sh

    [ -f ${TARGET_FILE} ] && rm ${TARGET_FILE} ${TARGET_FILE}.map

    emcc -shared -Os -g0 -fpic -o ${TARGET_FILE} $SDKROOT/prebuilt/emsdk/libpygame${PYMAJOR}.${PYMINOR}.a $SDL2

    # github CI does not build wheel for now.
    if [ -d /data/git/archives/repo/cp${TAG} ]
    then
        mkdir -p $TARGET_FOLDER
        /bin/cp -rf testing/pygame_static-1.0-cp${TAG}-cp${TAG}-wasm32_mvp_emscripten/. ${TARGET_FOLDER}/

        if pushd testing/pygame_static-1.0-cp${TAG}-cp${TAG}-wasm32_${WASM_FLAVOUR}_emscripten
        then
            rm ${TARGET_FILE}.map
            if $WASM_PURE
            then
                /data/git/archives/repo/norm.sh
            else
                whl=/data/git/archives/repo/cp${TAG}/$(basename $(pwd)).whl
                [ -f $whl ] && rm $whl
                zip $whl -r .
            fi
            rm ${TARGET_FILE}
            popd
        fi
    fi
fi






