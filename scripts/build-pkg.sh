#!/bin/bash

. scripts/vendoring.sh

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

export PYMAJOR=$(echo -n $PYBUILD|cut -d. -f1)
export PYMINOR=$(echo -n $PYBUILD|cut -d. -f2)

. /etc/lsb-release

export DISTRIB="${DISTRIB_ID}-${DISTRIB_RELEASE}"
export CONFIG=${CONFIG:-$SDKROOT/config}

export EMSDK_QUIET=1

export CIVER=${CIVER:-$DISTRIB}

export SDK_ARCHIVE=${SDK_ARCHIVE:-python${PYBUILD}-wasm-sdk-${CIVER}.tar.lz4}

export PATH=${SDKROOT}/.local/bin:$PATH

# sdk
if [ -d ${SDKROOT}/prebuilt/emsdk/${PYBUILD} ]
then
    echo "  * not upgrading python-wasm-sdk ${PYBUILD}" 1>&2
else
    if [ -f "../${SDK_ARCHIVE}" ]
    then
        echo "
    * using cached python-wasm-sdk archive ${SDK_ARCHIVE}
" 1>&2
        tar xfvP ../${SDK_ARCHIVE} --use-compress-program=lz4 \
         | pv -f -c -p -l -s 20626 >/dev/null
    else
        url=https://github.com/pygame-web/python-wasm-sdk/releases/download/${SDK_VERSION}/${SDK_ARCHIVE}
        echo "  * getting and installing python-wasm-sdk archive $url
" 1>&2
        curl -sL --retry 5 $url \
         | tar xvP --use-compress-program=lz4 \
         | pv -f -c -p -l -s 20626 >/dev/null
    fi

    # small fix specific to pygame build that does not use  <SDL2/SDL_xxx.h> but <SDL_xxx.h>
    rm -rf	${SDKROOT}/emsdk/upstream/emscripten/cache/sysroot/include/SDL

    # SDL_image update
    cp -r ${SDKROOT}/devices/emsdk/usr/include/SDL2/* ${SDKROOT}/emsdk/upstream/emscripten/cache/sysroot/include/SDL2/

fi


. ${CONFIG}

EXE=python${PYBUILD}


# runtime patches on known modules for specific platform
# applies to prebuilt/emsdk/site-packages at preload stage.
PLATFORM=$(realpath support/__EMSCRIPTEN__)


# pre populated site-packages
export REQUIREMENTS=$(realpath ${SDKROOT}/prebuilt/emsdk/${PYBUILD}/site-packages)

# and wasm libraries
export DYNLOAD=${SDKROOT}/prebuilt/emsdk/${PYBUILD}/lib-dynload


if [ -d ${PLATFORM}.overlay ]
then
    # copy stdlib python patches over installed site packages
    # in case python-wasm-sdk files are not suitable for platform
    # please contribute !

    cp -rf ${PLATFORM}.overlay/* ${REQUIREMENTS}/

    # copy stdlib  version dependant patched files if any
    if [ -d "${PLATFORM}.overlay-${PYBUILD}" ]
    then
        cp -rf ${PLATFORM}.overlay-${PYBUILD}/* ${REQUIREMENTS}/
    fi
fi


# python cross compile patches if any ( should already be applied by sdk )
if [ -d support/__EMSCRIPTEN__.patches/${PYBUILD} ]
then
    cp -rf support/__EMSCRIPTEN__.patches/${PYBUILD}/* ${SDKROOT}/devices/emsdk/usr/lib/python${PYBUILD}/
fi


mkdir -p build

> build/gen_static.h
> build/gen_inittab.h
> build/gen_inittab.c


for pkg in ${PACKAGES}
do

    PKG_PATH=packages.d/${pkg}/${pkg}

    pkg_script=${PKG_PATH}.sh

    if [ -f $pkg_script ]
    then
        echo "

    * processing build script $pkg_script for $pkg from $PKG_PATH

" 1>&2
    else
        echo "



    PACKAGE $pkg HAS NO BUILD FILE

    it must provide ${SDKROOT}/prebuilt/emsdk/lib${pkg}${PYBUILD}.a


"
        continue
    fi



    export PKGDIR=$REQUIREMENTS/$pkg

    # for packages build destination
    mkdir -p $DYNLOAD $REQUIREMENTS $PKGDIR


    if [ -f packages.d/${pkg}/$pkg.static.h ]
    then
        cat >> build/gen_static.h <<END
// auto generated from build-pkg.sh
#   include "../${PKG_PATH}.static.h"
END
    fi

# always do it so we get a warning if lib is not linked
    if [ -f packages.d/${pkg}/$pkg.h ]
    then
        cat >> build/gen_inittab.h <<END
// auto generated from build-pkg.sh
#if defined(PYDK_$pkg)
#   include "../${PKG_PATH}.h"
#endif
END
    fi


    if [ -f ${PKG_PATH}.c ]
    then
        cat >> build/gen_inittab.c <<END
// auto generated from build-pkg.sh
#if defined(PYDK_$pkg) || defined(PYDK_static_$pkg)
#   include "../${PKG_PATH}.c"
#else
    #pragma message "$pkg is not statically linked"
#endif
END
    fi


    # copy non upstreamed patches to loader source dir
    # even if not rebuilding static
    if [ -d ./${PKG_PATH}.overlay ]
    then
        cp -r ./${PKG_PATH}.overlay/* $PKGDIR/
        echo "
        * added ./${PKG_PATH}.overlay to $PKGDIR/
" 1>&2
    else
        echo "
        * no non-upstreamed patches found in ./${PKG_PATH}.overlay/ for $PKGDIR/
" 1>&2
    fi

    if [ -d ./${PGK_PATH}.overlay-$PYBUILD ]
    then
        cp -rf ./${PKG_PATH}.overlay-$PYBUILD/* $PKGDIR/
        echo "
        * added ./${PKG_PATH}.overlay-$PYBUILD to $PKGDIR/
" 1>&2
    else
        echo "
        * no non-upstreamed patches found in ./${PKG_PATH}.overlayoverlay-$PYBUILD/ for $PKGDIR/
" 1>&2

    fi

# TODO make a clean option
    if [ -f ${SDKROOT}/prebuilt/emsdk/lib${pkg}${PYBUILD}.a ]
    then
        echo " RE USING ${pkg} static library
" 1>&2
        continue
    fi

    export pkg

    if ./${PKG_PATH}.sh
    then

        if [ -f ${SDKROOT}/prebuilt/emsdk/lib${pkg}${PYBUILD}.a ]
        then
            echo "success building ${pkg}
" 1>&2
        else
            echo "failed to build lib${pkg}${PYBUILD}.a
" 1>&2
            exit 185
        fi


    else
        echo "$pkg script build failed
" 1>&2
        exit 192
    fi

done


