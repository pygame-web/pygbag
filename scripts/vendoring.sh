[ -f vendor/vendor.sh ] && . vendor/vendor.sh

# default is to build pygame only
export VENDOR=${VENDOR:-pygbag}
export PACKAGES=${PACKAGES:-emsdk hpy pygame}

export SDKROOT=${SDKROOT:-/opt/python-wasm-sdk}
export SDK_VERSION=${SDK_VERSION:-3.1.64.1bi}
export CYTHON=${CYTHON:-Cython-3.0.10-py2.py3-none-any.whl}
export PYBUILD=${PYBUILD:-3.12}
export LC_ALL=C

export SYS_PYTHON=${SYS_PYTHON:-$(which python3)}

if $CI
then
    export PYGBAG_BUILD=0.0
else
#    export PYGBAG_BUILD=$($SYS_PYTHON -c "print(__import__('pygbag').VERSION)"|tail -n 1|cut -f1-2 -d.)
    export PYGBAG_BUILD=0.0
fi

export DIST_DIR=$(pwd)/build/web/archives/${PYGBAG_BUILD}
mkdir -p $DIST_DIR


echo "
==============================================================================
    Building $VENDOR loader, target folder :

${DIST_DIR}

    ________________________________________
    statically built modules: $PACKAGES
    with SDK $SDK_VERSION from $SDKROOT
    python versions : $BUILDS
    Cython release: $CYTHON
    SYS_PYTHON: $SYS_PYTHON
    CI=$CI
==============================================================================
"
