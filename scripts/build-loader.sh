#!/bin/bash

export SDKROOT=${SDKROOT:-/opt/python-wasm-sdk}


. ${CONFIG:-$SDKROOT/config}


# pre populated site-packages
export REQUIREMENTS=$(realpath ${SDKROOT}/prebuilt/emsdk/${PYBUILD}/site-packages)

# and wasm libraries
export DYNLOAD=${SDKROOT}/prebuilt/emsdk/${PYBUILD}/lib-dynload



. $SDKROOT/emsdk/emsdk_env.sh


echo "
    *   building loader $(pwd)
            PYBUILD=$PYBUILD
            EMFLAVOUR=$EMFLAVOUR
            EMSDK=$EMSDK
            SDKROOT=$SDKROOT
            PYTHONPYCACHEPREFIX=$PYTHONPYCACHEPREFIX
            HPY=$HPY
"


# SDL2_image turned off : -ltiff

# CF_SDL="-sUSE_SDL=2 -sUSE_ZLIB=1 -sUSE_BZIP2=1"

CF_SDL="-I${SDKROOT}/devices/emsdk/usr/include/SDL2"
LD_SDL="-L${SDKROOT}/devices/emsdk/usr/lib -lSDL2_gfx -lSDL2_mixer -lSDL2_image -lwebp -ljpeg -lpng -lSDL2_ttf -lharfbuzz -lfreetype"


SUPPORT_FS=""

DIST_DIR=$(pwd)/build/web/archives/$($SYS_PYTHON -c "import pygbag;print(pygbag.__version__)")

mkdir -p $DIST_DIR/python${PYMAJOR}${PYMINOR}

rm $DIST_DIR/python${PYMAJOR}${PYMINOR}/main.* 2>/dev/null

# git does not keep empty dirs
mkdir -p tests/assets tests/code

ALWAYS_ASSETS=$(realpath tests/assets)
ALWAYS_CODE=$(realpath tests/code)



# crosstools, aio and simulator most likely from pygbag
if [ -d support/cross ]
then
    CROSS=$(realpath support/cross)
    SUPPORT_FS="$SUPPORT_FS --preload-file ${CROSS}@/data/data/org.python/assets/site-packages"
else
    echo "


    WARNING : no cross support lib found
    maybe have a look at pygbag module support subfolder


"
fi


LOPTS="-sMAIN_MODULE --bind -fno-rtti"

# O0/g3 is much faster to build and easier to debug

echo "  ************************************"
if [ -f dev ]
then
    export COPTS="-O0 -g3 -fPIC"

    echo "       building DEBUG $COPTS"
    LOPTS="$LOPTS -s ASSERTIONS=0"
    ALWAYS_FS="--preload-file ${ALWAYS_CODE}@/data/data/org.python/assets"
else
    echo "       building RELEASE $COPTS"
    LOPTS="$LOPTS -s ASSERTIONS=0 -s LZ4=1"
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

if emcc -fPIC -std=gnu99 -D__PYDK__=1 -DNDEBUG $CF_SDL $CPOPTS \
 -c -fwrapv -Wall -Werror=implicit-function-declaration -fvisibility=hidden\
 -I${PYDIR}/internal -I${PYDIR} -I./support -DPy_BUILD_CORE\
 -o build/${MODE}.o support/__EMSCRIPTEN__-pymain.c
then
    STDLIBFS="--preload-file build/stdlib-rootfs/python${PYBUILD}@/usr/lib/python${PYBUILD}"

    # \
    # --preload-file /usr/share/terminfo/x/xterm@/usr/share/terminfo/x/xterm \

    # --preload-file ${REQUIREMENTS}@/data/data/org.python/assets/site-packages \
    # --preload-file ${ROOT}/support/xterm@/etc/termcap \

    if echo ${PYBUILD}|grep -q 10$
    then
        echo " - no sqlite3 for 3.10 -"
        CPY_LDFLAGS=""
    else
        CPY_LDFLAGS="-lsqlite3"
    fi

    for lib in python mpdec expat pygame
    do
        cpylib=${SDKROOT}/prebuilt/emsdk/lib${lib}${PYBUILD}.a
        if [ -f $cpylib ]
        then
            CPY_LDFLAGS="$CPY_LDFLAGS $cpylib"
        fi
    done

    echo CPY_LDFLAGS=$CPY_LDFLAGS


    if emcc $FINAL_OPTS $LOPTS -std=gnu99 -D__PYDK__=1 -DNDEBUG\
     -s TOTAL_MEMORY=256MB -s ALLOW_TABLE_GROWTH -sALLOW_MEMORY_GROWTH \
     $CF_SDL \
     --use-preload-plugins \
     $STDLIBFS \
     $ALWAYS_FS \
     $SUPPORT_FS \
     --preload-file ${DYNLOAD}@/usr/lib/python${PYBUILD}/lib-dynload \
     --preload-file ${REQUIREMENTS}@/data/data/org.python/assets/site-packages \
     -o ${DIST_DIR}/python${PYMAJOR}${PYMINOR}/${MODE}.js build/${MODE}.o  \
     $CPY_LDFLAGS -lffi -lbz2 -lz \
     $LD_SDL \
     -ldl -lm
    then
        rm build/${MODE}.o
        du -hs ${DIST_DIR}/*
        echo Total
        echo _________
        if $CI
        then
            cp -r static/* ${DIST_DIR}/
            cp support/pythonrc.py ${DIST_DIR}/pythonrc.py
        else
            [ -f ${DIST_DIR}/pythonrc.py ] || ln support/pythonrc.py ${DIST_DIR}/pythonrc.py
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

        du -hs ${DIST_DIR}
    else
        echo "pymain+loader linking failed"
        exit 178
    fi
else
    echo "pymain compilation failed"
    exit 182
fi



