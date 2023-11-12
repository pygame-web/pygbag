#!/bin/bash




. scripts/vendoring.sh

. ${CONFIG:-$SDKROOT/config}


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




if emcc -fPIC -std=gnu99 -D__PYDK__=1 -DNDEBUG $CPY_CFLAGS $CF_SDL $CPOPTS \
 -c -fwrapv -Wall -Werror=implicit-function-declaration -fvisibility=hidden\
 -I${PYDIR}/internal -I${PYDIR} -I./support -I./src/hpy/hpy/devel/include -DPy_BUILD_CORE\
 -o build/${MODE}.o support/__EMSCRIPTEN__-pymain.c
then
    STDLIBFS="--preload-file build/stdlib-rootfs/python${PYBUILD}@/usr/lib/python${PYBUILD}"

    # \
    # --preload-file /usr/share/terminfo/x/xterm@/usr/share/terminfo/x/xterm \

    # --preload-file ${REQUIREMENTS}@/data/data/org.python/assets/site-packages \
    # --preload-file ${ROOT}/support/xterm@/etc/termcap \


# TODO: test -sWEBGL2_BACKWARDS_COMPATIBILITY_EMULATION

    LDFLAGS="-sUSE_GLFW=3 -sUSE_WEBGL2 -sMIN_WEBGL_VERSION=2 -sOFFSCREENCANVAS_SUPPORT=1 -sFULL_ES2 -sFULL_ES3"

    LDFLAGS="$LDFLAGS -lsqlite3"

    LDFLAGS="-L${SDKROOT}/devices/emsdk/usr/lib $LDFLAGS -lssl -lcrypto -lffi -lbz2 -lz -ldl -lm"

    LINKPYTHON="python mpdec expat"

    if  echo $PYBUILD|grep -q 3.12
    then
        LINKPYTHON="Hacl_Hash_SHA2 $LINKPYTHON"
    fi


    for lib in $LINKPYTHON
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

#  -std=gnu99 -std=c++23

    cat > final_link.sh <<END
#!/bin/bash
emcc $FINAL_OPTS $LOPTS  -D__PYDK__=1 -DNDEBUG \\
     -sTOTAL_MEMORY=256MB -sSTACK_SIZE=4MB -sALLOW_TABLE_GROWTH -sALLOW_MEMORY_GROWTH \\
     $CF_SDL \\
     --use-preload-plugins \\
     $STDLIBFS \\
     $ALWAYS_FS \\
     $SUPPORT_FS \\
     $PATCH_FS \\
     --preload-file ${DYNLOAD}@/usr/lib/python${PYBUILD}/lib-dynload \\
     --preload-file ${REQUIREMENTS}@/data/data/org.python/assets/site-packages \\
     -o ${DIST_DIR}/python${PYMAJOR}${PYMINOR}/${MODE}.js build/${MODE}.o \\
     $LDFLAGS -lembind -sERROR_ON_UNDEFINED_SYMBOLS=0


# --bind -fno-rtti


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
#echo "
#    @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#    emsdk tot js gen temp fix
#    @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
#"
#        sed -i 's/_glfwSetWindowContentScaleCallback_sig=iii/_glfwSetWindowContentScaleCallback_sig="iii"/g' \
#         ${DIST_DIR}/python${PYMAJOR}${PYMINOR}/${MODE}.js
        du -hs ${DIST_DIR}/python*
    else
        echo "pymain+loader linking failed"
        exit 178
    fi
else
    echo "pymain compilation failed"
    exit 182
fi




















