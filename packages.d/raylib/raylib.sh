#!/bin/bash

export SDKROOT=${SDKROOT:-/opt/python-wasm-sdk}
export CONFIG=${CONFIG:-$SDKROOT/config}

. ${CONFIG}

PACKAGE=raylib

echo "

    * building ${PACKAGE} for ${CIVER}, PYBUILD=$PYBUILD => CPython${PYMAJOR}.${PYMINOR}
            PYBUILD=$PYBUILD
            EMFLAVOUR=$EMFLAVOUR
            SDKROOT=$SDKROOT
            SYS_PYTHON=${SYS_PYTHON}

" 1>&2


mkdir -p external

if pushd $(pwd)/external
then
    if [ -d ${PACKAGE} ]
    then
        pushd $(pwd)/${PACKAGE}
        git restore .
        git pull
    else
        git clone --no-tags --depth 1 --single-branch --branch master https://github.com/raysan5/raylib ${PACKAGE}
        pushd $(pwd)/${PACKAGE}
    fi

    # This patch is required to avoid brinding ASYNCIFY into the SIDE_MODULE (.so)
    # the main module ( pygbag+libpython ) does not use ASYNCIFY so it would not be
    # compatible
    # the only drawback is to use async for game loop ( same as pygame / panda3D , etc )
    # which is not a problem since only async tasks can solve "os threading"
    # correctly on wasm


    patch -p1 <<END
diff --git a/src/platforms/rcore_web.c b/src/platforms/rcore_web.c
index a13f699..52ab2a1 100644
--- a/src/platforms/rcore_web.c
+++ b/src/platforms/rcore_web.c
@@ -153,7 +153,7 @@ bool WindowShouldClose(void)
     // By default, this function is never called on a web-ready raylib example because we encapsulate
     // frame code in a UpdateDrawFrame() function, to allow browser manage execution asynchronously
     // but now emscripten allows sync code to be executed in an interpreted way, using emterpreter!
-    emscripten_sleep(16);
+    // emscripten_sleep(16);
     return false;
 }

END

    cp ./examples/shapes/raygui.h ${PREFIX}/include/

    popd
    popd
fi

PACKAGE=physac
if pushd $(pwd)/external
then
    if [ -d ${PACKAGE} ]
    then
        pushd $(pwd)/${PACKAGE}
        git restore .
        git pull
    else
        git clone --no-tags --depth 1 --single-branch --branch master https://github.com/raysan5/physac ${PACKAGE}
        pushd $(pwd)/${PACKAGE}
    fi

    cp ./src/physac.h ${PREFIX}/include/

    popd
    popd
fi

PACKAGE=raygui
if pushd $(pwd)/external
then
    if [ -d ${PACKAGE} ]
    then
        pushd $(pwd)/${PACKAGE}
        git restore .
        git pull
    else
        git clone --no-tags --depth 1 --single-branch --branch master https://github.com/raysan5/raygui ${PACKAGE}
        pushd $(pwd)/${PACKAGE}
    fi

    cp src/raygui.h ${PREFIX}/include/

    popd
    popd
fi


# https://github.com/sDos280/raylib-python-ctypes
# https://github.com/pmp-p/raylib-python-ctypes-wasm
RAYPYC=${RAYPYC:-false}

if $RAYPYC
then

    PACKAGE=raylib-python-ctypes

    if pushd $(pwd)/external
    then
        if [ -d ${PACKAGE} ]
        then
            pushd $(pwd)/${PACKAGE}
            git restore .
            git pull
        else
            git clone --no-tags --depth 1 --single-branch --branch main https://github.com/pmp-p/raylib-python-ctypes-wasm ${PACKAGE}
            pushd $(pwd)/${PACKAGE}
        fi
        popd
        popd
    fi
fi



# build raylib C lib as a static
# install it so pkg-config can find it later.

PACKAGE=raylib

mkdir -p build/${PACKAGE}
if pushd build/${PACKAGE}
then
    . ${SDKROOT}/wasm32-${WASM_FLAVOUR}-emscripten-shell.sh
    emcmake cmake ../../external/${PACKAGE} -DCMAKE_INSTALL_PREFIX=$PREFIX \
 -DCMAKE_BUILD_TYPE=Release \
 -DPLATFORM=Web \
 -DGRAPHICS=GRAPHICS_API_OPENGL_ES3 \
 -DBUILD_EXAMPLES=OFF

    emmake make install

    # raypyc rely on a shared lib raylib in its own wheel.
    if $RAYPYC
    then
        # clean up native libs
        rm ../../external/raylib-python-ctypes/raypyc/libs/*.so
        rm ../../external/raylib-python-ctypes/raypyc/libs/*.dll

        emcc -shared -o ../../external/raylib-python-ctypes/raypyc/libs/libraylib.wasm32-${WASM_FLAVOUR}-emscripten.so raylib/libraylib.a

        rm ../../external/raylib-python-ctypes/raypyc/libs/lib*.so.map
    fi

    mv -v raylib/libraylib.a ${SDKROOT}/prebuilt/emsdk/lib${PACKAGE}${PYBUILD}.a

    popd
fi


if $RAYPYC
then
    PACKAGE=raylib-python-ctypes

    if pushd $(pwd)/external/${PACKAGE}
    then

        ${SDKROOT}/python3-wasm -m build --no-isolation .
        if [ -d /data/git/archives/repo/pkg ]
        then
            mv dist/raypyc-*-py3-none-any.whl /data/git/archives/repo/pkg/
        fi

        popd
    fi
fi

# https://github.com/electronstudio/raylib-python-cffi/issues/58
PACKAGE=raylib-python-cffi

if pushd $(pwd)/external
then

    if [ -d ${PACKAGE} ]
    then
        pushd $(pwd)/${PACKAGE}
        git restore .
        git pull
    else
        git clone --no-tags --depth 1 --single-branch --branch master https://github.com/electronstudio/raylib-python-cffi ${PACKAGE}
        pushd $(pwd)/${PACKAGE}
    fi

    # fix some includes
    mkdir -p ${PREFIX}/include/GLFW

    cp ${EMSDK}/upstream/emscripten/system/include/GLFW/glfw3.h ${PREFIX}/include/GLFW/

    # build it

    ${SDKROOT}/python3-wasm setup.py bdist_wheel --py-limited-api=cp310


    popd
fi
