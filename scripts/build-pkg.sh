#!/bin/bash
export SDK_VERSION=${SDK_VERSION:-3.1.19.0}
export PYBUILD=${PYBUILD:-3.11}


export LC_ALL=C
export SDKROOT=${SDKROOT:-/opt/python-wasm-sdk}
export PYMAJOR=$(echo -n $PYBUILD|cut -d. -f1)
export PYMINOR=$(echo -n $PYBUILD|cut -d. -f2)

. /etc/lsb-release

export DISTRIB="${DISTRIB_ID}-${DISTRIB_RELEASE}"
export CONFIG=${CONFIG:-$SDKROOT/config}


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

> build/gen_inittab.h
> build/gen_inittab.c


for pkg in ${PACKAGES:-pygame}
do
    pkg_script=packages.d/$pkg.sh

    #pkg=$(basename $pkg_script .sh)

    echo "
    * processing build script $pkg_script for $pkg
" 1>&2

    export PKGDIR=$REQUIREMENTS/$pkg

    # for packages build destination
    mkdir -p $DYNLOAD $REQUIREMENTS $PKGDIR




# always do it so we get a warning if lib is not linked
    if [ -f packages.d/$pkg.h ]
    then
        cat >> build/gen_inittab.h <<END
// auto generated from build-pkg.sh
#if defined(PYDK_$pkg)
#   include "../packages.d/$pkg.h"
#endif
END
    fi

    if [ -f packages.d/$pkg.c ]
    then
        cat >> build/gen_inittab.c <<END
// auto generated from build-pkg.sh
#if defined(PYDK_$pkg)
#   include "../packages.d/$pkg.c"
#else
    #pragma message "not linking $pkg"
#endif
END
    fi


    # copy non upstreamed patches to loader source dir
    # even if not rebuilding static
    if [ -d ./packages.d/${pkg}.overlay ]
    then
        cp -r ./packages.d/${pkg}.overlay/* $PKGDIR/
        echo "
        * added ./packages.d/${pkg}.overlay to $PKGDIR/
" 1>&2
    fi

    if [ -d ./packages.d/${pkg}.overlay-$PYBUILD ]
    then
        cp -rf ./packages.d/${pkg}.overlay-$PYBUILD/* $PKGDIR/
        echo "
        * added ./packages.d/${pkg}.overlay-$PYBUILD to $PKGDIR/
" 1>&2
    fi

# TODO make a clean option
    if [ -f ${SDKROOT}/prebuilt/emsdk/lib${pkg}${PYBUILD}.a ]
    then
        echo " RE USING  ${pkg}
" 1>&2
        continue
    fi


    if ./packages.d/${pkg}.sh
    then

        if [ -f ${SDKROOT}/prebuilt/emsdk/lib${pkg}${PYBUILD}.a ]
        then
            echo "success building ${pkg}
" 1>&2
        else
            echo "failed to build lib${pkg}${PYBUILD}.a
" 1>&2
            exit 119
        fi


    else
        echo "script $pkg_script failed
" 1>&2
    fi

done


