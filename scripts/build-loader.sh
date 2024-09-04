#!/bin/bash

. scripts/vendoring.sh

. ${CONFIG:-$SDKROOT/config}

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

ln -sf $(pwd)/src/pygbag $(pwd)/pygbag

pushd src/pygbag/support
cp -r _xterm_parser ${SDKROOT}/prebuilt/emsdk/common/site-packages/
#cp pygbag_*.py readline.py typing_extensions.py ${SDKROOT}/prebuilt/emsdk/common/site-packages/
cp typing_extensions.py ${SDKROOT}/prebuilt/emsdk/common/site-packages/
popd


DISTRO=cpython

# version independant modules
cp -rf ${SDKROOT}/prebuilt/emsdk/common/* ${SDKROOT}/prebuilt/emsdk/${PYBUILD}/

# pre populated site-packages
export REQUIREMENTS=${SDKROOT}/prebuilt/emsdk/${PYBUILD}/site-packages

# and wasm libraries
export DYNLOAD=${SDKROOT}/prebuilt/emsdk/${PYBUILD}/lib-dynload


. $SDKROOT/emsdk/emsdk_env.sh


echo "
    *   building loader $(pwd) for ${VENDOR} / ${PACKAGES}
            PYBUILD=$PYBUILD python${PYMAJOR}${PYMINOR}
            EMFLAVOUR=$EMFLAVOUR
            EMSDK=$EMSDK
            SDKROOT=$SDKROOT
            PYTHONPYCACHEPREFIX=$PYTHONPYCACHEPREFIX
            HPY=$HPY
            LD_VENDOR=$LD_VENDOR
" 1>&2


EMPIC=/opt/python-wasm-sdk/emsdk/upstream/emscripten/cache/sysroot/lib/wasm32-emscripten/pic

if echo -n $PYBUILD|grep -q 13$
then
    MIMALLOC="-I/opt/python-wasm-sdk/emsdk/upstream/emscripten/system/lib/mimalloc/include"
else
    MIMALLOC=""
fi

SUPPORT_FS=""


mkdir -p $DIST_DIR/${DISTRO}${PYMAJOR}${PYMINOR}

rm $DIST_DIR/${DISTRO}${PYMAJOR}${PYMINOR}/main.* 2>/dev/null

# git does not keep empty dirs
mkdir -p tests/assets tests/code


ALWAYS_CODE=$(realpath tests/code)

#ALWAYS_ASSETS=$(realpath tests/assets)
ALWAYS_ASSETS=$(realpath assets/cpython)

for asset in readline pyodide pygbag_app pygbag_fsm pygbag_host pygbag_ui pygbag_ux
do
    [ -f ${ALWAYS_ASSETS}/${asset}.py ] || ln ./src/pygbag/support/${asset}.py ${ALWAYS_ASSETS}/${asset}.py
done


# crosstools, aio and simulator most likely from pygbag
if [ -d src/pygbag/support/cross ]
then
    CROSS=$(realpath src/pygbag/support/cross)
    SUPPORT_FS="$SUPPORT_FS --preload-file ${CROSS}@/data/data/org.python/assets/site-packages"
else
    echo "


    WARNING : no cross support lib found
    maybe have a look at pygbag module support subfolder


"
fi

if [ -d /data/git/platform_wasm ]
then
    cp -Rf /data/git/platform_wasm ./
else
    if [ -d platform_wasm ]
    then
        pushd platform_wasm
        git pull
        popd
    else
        git clone https://github.com/pygame-web/platform_wasm
    fi
fi


export PATCH_FS="--preload-file $(realpath platform_wasm/platform_wasm)@/data/data/org.python/assets/site-packages/platform_wasm"

# =2 will break pyodide module reuses
LOPTS="-sMAIN_MODULE=1"

# O0/g3 is much faster to build and easier to debug


echo "  ************************************"
if [ -f dev ]
then
    export COPTS="-O0 -g3 -fPIC --source-map-base http://localhost:8000/maps/"
    echo "       building DEBUG $COPTS"
    LOPTS="$LOPTS -sASSERTIONS=0"
#    ALWAYS_FS="--preload-file ${ALWAYS_CODE}@/data/data/org.python/assets"
else
    export COPTS="-Os -g0 -fPIC"
    echo "       building RELEASE $COPTS"
    LOPTS="$LOPTS -sASSERTIONS=0 -sLZ4"
    ALWAYS_FS=""
fi

echo "  ************************************"

ALWAYS_FS="$ALWAYS_FS --preload-file ${ALWAYS_ASSETS}@/data/data/org.python/assets"


# pre populated site-packages given by env
# REQUIREMENTS
# DYNLOAD


# runtime patches on known modules for specific platform
# applies to prebuilt/emsdk/site-packages at preload stage.
PLATFORM=$(realpath support/__EMSCRIPTEN__)


echo "

site-packages=${PLATFORM}
crosstoosl=${CROSS}

COPTS=$COPTS
LOPTS=$LOPTS

ALWAYS_ASSETS=$ALWAYS_ASSETS
ALWAYS_CODE=$ALWAYS_CODE

REQUIREMENTS=$REQUIREMENTS
DYNLOAD=$DYNLOAD

"


if false
then
    FINAL_OPTS="$COPTS --proxy-to-worker -s ENVIRONMENT=web,worker"
    MODE="worker"
    WORKER_STATUS="using worker"
else
    # https://github.com/emscripten-core/emscripten/issues/10086
    #       EXPORT_NAME does not affect generated html
    #
    FINAL_OPTS="$COPTS"
    MODE="main"
    WORKER_STATUS="not using worker"
fi

if false
then
    FINAL_OPTS="$FINAL_OPTS -s MODULARIZE=1"
    FINAL_OPTS="$FINAL_OPTS -s EXPORT_NAME=\"${EXE}\""
    FINAL_OPTS="$FINAL_OPTS -s EXPORTED_RUNTIME_METHODS=[\"FS\"]"
fi

# pack the minimal stdlib for current implicit requirements
# see inside ./scripts/build-rootfs.sh to view them
./scripts/build-rootfs.sh


PYDIR=${SDKROOT}/devices/emsdk/usr/include/python${PYBUILD}

# gnu99 not c99 for EM_ASM() js calls functions.

if $STATIC
then
    echo "building static loader"
else
    export PACKAGES=${BUILD_STATIC:-emsdk hpy _ctypes}

    echo "building dynamic loader


    with static parts : ${BUILD_STATIC}


"

fi


for lib in $PACKAGES
do
    CPY_CFLAGS="$CPY_CFLAGS -DPYDK_$lib=1"
done

echo CPY_CFLAGS=$CPY_CFLAGS

#\
#    -I/opt/python-wasm-sdk/emsdk/upstream/emscripten/cache/sysroot/include/freetype2 -lfreetype\
#    -lopenal \
#\



if [ -f ${WORKSPACE}/integration/${INTEGRATION}.h ]
then
    LNK_TEST=${WORKSPACE}/integration/${INTEGRATION}
else
    LNK_TEST=/tmp/pygbag_integration_test
fi

INC_TEST="${LNK_TEST}.h"
MAIN_TEST="${LNK_TEST}.c"


touch ${INT_TEST} ${INC_TEST} ${LNK_TEST} ${MAIN_TEST}

# -L${SDKROOT}/emsdk/upstream/emscripten/cache/sysroot/lib/wasm32-emscripten/pic only !

if emcc -fPIC -std=gnu99 -D__PYDK__=1 -DNDEBUG $MIMALLOC $CPY_CFLAGS $CF_SDL $CPOPTS \
 -DINC_TEST=$INC_TEST -DMAIN_TEST=$MAIN_TEST \
 -c -fwrapv -Wall -Werror=implicit-function-declaration -fvisibility=hidden \
 -I${PYDIR}/internal -I${PYDIR} -I./support -I./external/hpy/hpy/devel/include -DPy_BUILD_CORE \
 -o build/${MODE}.o support/__EMSCRIPTEN__-pymain.c
then
    if echo $PYBUILD | grep -q 13$
    then
        STDLIBFS="--preload-file build/stdlib-rootfs/python${PYBUILD}t@/usr/lib/python${PYBUILD}t"
    else
        STDLIBFS="--preload-file build/stdlib-rootfs/python${PYBUILD}@/usr/lib/python${PYBUILD}"
    fi

    # \
    # --preload-file /usr/share/terminfo/x/xterm@/usr/share/terminfo/x/xterm \

    # --preload-file ${REQUIREMENTS}@/data/data/org.python/assets/site-packages \
    # --preload-file ${ROOT}/support/xterm@/etc/termcap \


# TODO: test -sWEBGL2_BACKWARDS_COMPATIBILITY_EMULATION

#

    LDFLAGS="-sUSE_GLFW=3 -sUSE_WEBGL2 -sMIN_WEBGL_VERSION=2 -sMAX_WEBGL_VERSION=2 -sOFFSCREENCANVAS_SUPPORT=1 -sFULL_ES2 -sFULL_ES3"

    LDFLAGS="$LDFLAGS -lsqlite3"

    LDFLAGS="-L${SDKROOT}/devices/emsdk/usr/lib $LDFLAGS -lssl -lcrypto -lffi -lbz2 -lz -ldl -lm"

    LINKPYTHON="python mpdec expat"

    if  echo $PYBUILD|grep -q 3.12
    then
        LINKPYTHON="Hacl_Hash_SHA2 $LINKPYTHON"
    else
        if  echo $PYBUILD|grep -q 3.13
        then
            LINKPYTHON="Hacl_Hash_SHA2 $LINKPYTHON"
        fi
    fi

    for lib in $LINKPYTHON
    do
        cpylib=${SDKROOT}/prebuilt/emsdk/lib${lib}${PYBUILD}.a
        if [ -f $cpylib ]
        then
            LDFLAGS="$LDFLAGS $cpylib"
        else
            echo "  Not found : $cpylib"
        fi
    done


    for lib in $PACKAGES
    do
        cpylib=${SDKROOT}/prebuilt/emsdk/lib${lib}${PYBUILD}.a
        LDFLAGS="$LDFLAGS $cpylib"
    done


    LDFLAGS="$LDFLAGS $(cat $LNK_TEST) -lembind"


    echo "

     LDFLAGS=$LDFLAGS

    " 1>&2

#  -std=gnu99 -std=c++23
# EXTRA_EXPORTED_RUNTIME_METHODS => EXPORTED_RUNTIME_METHODS after 3.1.52


PG=/pgdata
    cat > final_link.sh <<END
#!/bin/bash
emcc \\
 $FINAL_OPTS \\
 $LOPTS \\
 -D__PYDK__=1 -DNDEBUG  \\
     -sTOTAL_MEMORY=256MB -sSTACK_SIZE=4MB -sALLOW_TABLE_GROWTH -sALLOW_MEMORY_GROWTH \\
    -sEXPORTED_RUNTIME_METHODS=FS \\
     $CF_SDL \\
     --use-preload-plugins \\
     $STDLIBFS \\
     $ALWAYS_FS \\
     $SUPPORT_FS \\
     $PATCH_FS \\
     --preload-file ${DYNLOAD}@/usr/lib/python${PYBUILD}/lib-dynload \\
     --preload-file ${REQUIREMENTS}@/data/data/org.python/assets/site-packages \\
     -o ${DIST_DIR}/${DISTRO}${PYMAJOR}${PYMINOR}/${MODE}.js build/${MODE}.o \\
     $LDFLAGS


END
    chmod +x ./final_link.sh
    if ./final_link.sh
    then
        rm build/${MODE}.o
        du -hs ${DIST_DIR}/*
        echo Total
        echo _________

        if $CI
        then
            if [ -f /pp ]
            then
                USECP=false
            else
                USECP=true
            fi
        else
            USECP=false
        fi


        if $USECP
        then
            cp -R static/* ${DIST_DIR}/
            cp src/pygbag/support/cpythonrc.py ${DIST_DIR}/cpythonrc.py
            # for simulator
            cp src/pygbag/support/cpythonrc.py ${SDKROOT}/support/
        else
            [ -f ${DIST_DIR}/cpythonrc.py ] || ln src/pygbag/support/cpythonrc.py ${DIST_DIR}/cpythonrc.py
            pushd static
            for fn in *
            do
                if [ -f $fn ]
                then
                    [ -f ${DIST_DIR}/$fn ] && continue
                    ln $fn ${DIST_DIR}/$fn
                    continue
                fi
                [ -L ${DIST_DIR}/$fn ] && continue
                ln -s $(pwd)/$fn ${DIST_DIR}/$fn
            done
            popd
        fi
        du -hs ${DIST_DIR}/*
    else
        echo "pymain+loader linking failed"
        exit 178
    fi
else
    echo "pymain compilation failed"
    exit 182
fi




















