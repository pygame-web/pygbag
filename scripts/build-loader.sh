#!/bin/bash




. scripts/vendoring.sh

. ${CONFIG:-$SDKROOT/config}


# version independant modules
cp -rf ${SDKROOT}/prebuilt/emsdk/common/* ${SDKROOT}/prebuilt/emsdk/${PYBUILD}/

# pre populated site-packages
export REQUIREMENTS=$(realpath ${SDKROOT}/prebuilt/emsdk/${PYBUILD}/site-packages)

# and wasm libraries
export DYNLOAD=${SDKROOT}/prebuilt/emsdk/${PYBUILD}/lib-dynload



. $SDKROOT/emsdk/emsdk_env.sh


echo "
    *   building loader $(pwd) for ${VENDOR} / ${PACKAGES}
            PYBUILD=$PYBUILD
            EMFLAVOUR=$EMFLAVOUR
            EMSDK=$EMSDK
            SDKROOT=$SDKROOT
            PYTHONPYCACHEPREFIX=$PYTHONPYCACHEPREFIX
            HPY=$HPY
            LD_VENDOR=$LD_VENDOR
" 1>&2


# SDL2_image turned off : -ltiff

# CF_SDL="-sUSE_SDL=2 -sUSE_ZLIB=1 -sUSE_BZIP2=1"


# something triggers sdl2 *full* rebuild.
# also for SDL2_mixer, ogg and vorbis
# all pic


# /
# $EMPIC/libSDL2.a
# $EMPIC/libSDL2_gfx.a
# $EMPIC/libogg.a
# $EMPIC/libvorbis.a
# $EMPIC/libSDL2_mixer_ogg.a

EMPIC=/opt/python-wasm-sdk/emsdk/upstream/emscripten/cache/sysroot/lib/wasm32-emscripten/pic

CF_SDL="-I${SDKROOT}/devices/emsdk/usr/include/SDL2"
#LD_SDL2="-lSDL2_gfx -lSDL2_mixer -lSDL2_ttf"

LD_SDL2="$EMPIC/libSDL2.a"
LD_SDL2="$LD_SDL2 $EMPIC/libSDL2_gfx.a $EMPIC/libogg.a $EMPIC/libvorbis.a"
LD_SDL2="$LD_SDL2 $EMPIC/libSDL2_mixer_ogg.a $EMPIC/libSDL2_ttf.a"
LD_SDL2="-L${SDKROOT}/devices/emsdk/usr/lib $LD_SDL2 -lSDL2_image -lwebp -ljpeg -lpng -lharfbuzz -lfreetype"


SUPPORT_FS=""


mkdir -p $DIST_DIR/python${PYMAJOR}${PYMINOR}

rm $DIST_DIR/python${PYMAJOR}${PYMINOR}/main.* 2>/dev/null

# git does not keep empty dirs
mkdir -p tests/assets tests/code

ALWAYS_ASSETS=$(realpath tests/assets)
ALWAYS_CODE=$(realpath tests/code)



# crosstools, aio and simulator most likely from pygbag
if [ -d pygbag/support/cross ]
then
    CROSS=$(realpath pygbag/support/cross)
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
    export COPTS="-O1 -g1 -fPIC"
    echo "       building DEBUG $COPTS"
    LOPTS="$LOPTS -sASSERTIONS=0"
    ALWAYS_FS="--preload-file ${ALWAYS_CODE}@/data/data/org.python/assets"
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
    echo "building dynamic loader"
    export PACKAGES="emsdk"
fi


for lib in $PACKAGES
do
    CPY_CFLAGS="$CPY_CFLAGS -DPYDK_$lib=1"
done

echo CPY_CFLAGS=$CPY_CFLAGS

if emcc -fPIC -std=gnu99 -D__PYDK__=1 -DNDEBUG $CPY_CFLAGS $CF_SDL $CPOPTS \
 -c -fwrapv -Wall -Werror=implicit-function-declaration -fvisibility=hidden\
 -I${PYDIR}/internal -I${PYDIR} -I./support -DPy_BUILD_CORE\
 -o build/${MODE}.o support/__EMSCRIPTEN__-pymain.c
then
    STDLIBFS="--preload-file build/stdlib-rootfs/python${PYBUILD}@/usr/lib/python${PYBUILD}"

    # \
    # --preload-file /usr/share/terminfo/x/xterm@/usr/share/terminfo/x/xterm \

    # --preload-file ${REQUIREMENTS}@/data/data/org.python/assets/site-packages \
    # --preload-file ${ROOT}/support/xterm@/etc/termcap \


    LDFLAGS="$LD_VENDOR"

    if echo ${PYBUILD}|grep -q 10$
    then
        echo " - no sqlite3 for 3.10 -"
    else
        LDFLAGS="$LDFLAGS -lsqlite3"
    fi

    LDFLAGS="$LDFLAGS $LD_SDL2 -lffi -lbz2 -lz -ldl -lm"

    for lib in python mpdec expat
    do
        cpylib=${SDKROOT}/prebuilt/emsdk/lib${lib}${PYBUILD}.a
        if [ -f $cpylib ]
        then
            LDFLAGS="$LDFLAGS $cpylib"
        fi
    done

    for lib in $PACKAGES
    do
        cpylib=${SDKROOT}/prebuilt/emsdk/lib${lib}${PYBUILD}.a
        LDFLAGS="$LDFLAGS $cpylib"
    done

    echo "

     LDFLAGS=$LDFLAGS

    " 1>&2

    if emcc -m32 $FINAL_OPTS $LOPTS -std=gnu99 -D__PYDK__=1 -DNDEBUG\
     -s TOTAL_MEMORY=256MB -sALLOW_TABLE_GROWTH -sALLOW_MEMORY_GROWTH \
     $CF_SDL \
     --use-preload-plugins \
     $STDLIBFS \
     $ALWAYS_FS \
     $SUPPORT_FS \
     --preload-file ${DYNLOAD}@/usr/lib/python${PYBUILD}/lib-dynload \
     --preload-file ${REQUIREMENTS}@/data/data/org.python/assets/site-packages \
     -o ${DIST_DIR}/python${PYMAJOR}${PYMINOR}/${MODE}.js build/${MODE}.o \
     $LDFLAGS
    then
        rm build/${MODE}.o
        du -hs ${DIST_DIR}/*
        echo Total
        echo _________
        if $CI
        then
            cp -r static/* ${DIST_DIR}/
            cp pygbag/support/pythonrc.py ${DIST_DIR}/pythonrc.py
            # for simulator
            cp pygbag/support/pythonrc.py ${SDKROOT}/support/
        else
            [ -f ${DIST_DIR}/pythonrc.py ] || ln pygbag/support/pythonrc.py ${DIST_DIR}/pythonrc.py
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


