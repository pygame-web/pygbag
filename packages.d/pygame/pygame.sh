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

sed -i 's|check.warn(importable)|pass|g' ${HOST_PREFIX}/lib/python${PYMAJOR}.${PYMINOR}/site-packages/setuptools/command/build_py.py

if ${CI:-false}
then
    CYTHON_URL=git+https://github.com/pygame-web/cython.git

    CYTHON=${CYTHON:-Cython-3.0.11-py2.py3-none-any.whl}

    # update cython
    TEST_CYTHON=$($HPY -m cython -V 2>&1)
    if echo $TEST_CYTHON| grep -q 3\\.1\\.0a0$
    then
        echo "  * not upgrading cython $TEST_CYTHON
" 1>&2
    else
        echo "  * upgrading cython $TEST_CYTHON to at least 3.0.11
"  1>&2

        if [ ${PYMINOR} -ge 13 ]
        then
           echo "

 ================= forcing Cython git instead of release ${CYTHON}  =================

"
            # ${SDKROOT}/python3-wasm -m pip install --upgrade --force --no-build-isolation git+${CYTHON_URL}
            NO_CYTHON_COMPILE=true $HPY -m pip install --upgrade --force --no-build-isolation ${CYTHON_URL}
        else
            echo "

 ================= Using Cython release ${CYTHON}  =================

"
            pushd build
                wget -q -c https://github.com/cython/cython/releases/download/3.0.11-1/${CYTHON}
                ${SDKROOT}/python3-wasm -m pip install --upgrade --force $CYTHON
                $HPY -m pip install --upgrade --force $CYTHON
            popd
        fi

    fi
fi

# PYTHON_GIL=0
# Fatal Python error: config_read_gil: Disabling the GIL is not supported by this build
# Python runtime state: preinitialized

echo "cython ? $( $HPY -m cython -V 2>&1)"


mkdir -p external
pushd $(pwd)/external


echo "
* using main pygame-ce repo
" 1>&2
PG_BRANCH="main"
PG_GIT="https://github.com/pygame-community/pygame-ce.git"



if ${CI:-true}
then
    if [ -f pygame_ce-2.5.7.tar.gz ]
    then
        rm -rf pygame-wasm
        echo Release Mode : https://github.com/pygame-community/pygame-ce/releases/download/2.5.7/pygame_ce-2.5.7.tar.gz
        tar xfz pygame_ce-2.5.7.tar.gz
        mv pygame_ce-2.5.7 pygame-wasm
        pushd pygame-wasm
    else
        if [ -d pygame-wasm ]
        then
            pushd pygame-wasm
            git restore .
            git pull
        else
            git clone --no-tags --depth 1 --single-branch --branch $PG_BRANCH $PG_GIT pygame-wasm
            pushd pygame-wasm
        fi
    fi

    # to upstream after tests
    # done wget -O- https://patch-diff.githubusercontent.com/raw/pmp-p/pygame-ce-wasm/pull/7.diff | patch -p1




    # unsure : wasm pygame.freetype hack
    # wget -O- https://patch-diff.githubusercontent.com/raw/pmp-p/pygame-ce-wasm/pull/3.diff | patch -p1

    wget -O- https://patch-diff.githubusercontent.com/raw/pygame-community/pygame-ce/pull/1967.diff  | patch -p1

    # 313t controller fix merged
    # wget -O- https://patch-diff.githubusercontent.com/raw/pygame-community/pygame-ce/pull/3137.diff | patch -p1

    # new cython (git)
    wget -O- https://patch-diff.githubusercontent.com/raw/pmp-p/pygame-ce-wasm/pull/8.diff | patch -p1

    # fix 3.13 build , merged
    # wget -O- https://patch-diff.githubusercontent.com/raw/pygame-community/pygame-ce/pull/3496.diff | patch -p1

    # cython3 / merged
    # wget -O- https://patch-diff.githubusercontent.com/raw/pygame-community/pygame-ce/pull/2395.diff | patch -p1


    # zerodiv mixer.music / merged
    # wget -O- https://patch-diff.githubusercontent.com/raw/pygame-community/pygame-ce/pull/2426.diff | patch -p1


    # remove cython/gil warnings
    patch -p1 <<END
diff --git a/src_c/cython/pygame/_sdl2/audio.pyx b/src_c/cython/pygame/_sdl2/audio.pyx
index c3667d5e3..dfe85fb72 100644
--- a/src_c/cython/pygame/_sdl2/audio.pyx
+++ b/src_c/cython/pygame/_sdl2/audio.pyx
@@ -68,7 +68,7 @@ def get_audio_device_names(iscapture = False):
     return names

 import traceback
-cdef void recording_cb(void* userdata, Uint8* stream, int len) nogil:
+cdef int recording_cb(void* userdata, Uint8* stream, int len) nogil:
     """ This is called in a thread made by SDL.
         So we need the python GIL to do python stuff.
     """
diff --git a/src_c/cython/pygame/_sdl2/mixer.pyx b/src_c/cython/pygame/_sdl2/mixer.pyx
index ebc23b992..c70cebab6 100644
--- a/src_c/cython/pygame/_sdl2/mixer.pyx
+++ b/src_c/cython/pygame/_sdl2/mixer.pyx
@@ -14,7 +14,7 @@ import traceback
 # Mix_SetPostMix(noEffect, NULL);


-cdef void recording_cb(void* userdata, Uint8* stream, int len) nogil:
+cdef int recording_cb(void* userdata, Uint8* stream, int len) nogil:
     """ This is called in a thread made by SDL.
         So we need the python GIL to do python stuff.
     """
END


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


if ${CI:-false}
then
    touch $(find | grep pxd$)
    if $HPY setup.py cython_only
    then
        echo -n
    else
        echo "cythonize failed" 1>&2
        exit 208
    fi
else
    echo "skipping cython regen"
fi

    if $SDKROOT/python3-wasm dev.py build --wheel
    then
        touch ${SDKROOT}/prebuilt/emsdk/lib${pkg}${PYBUILD}.a
    else
        echo "${pkg} build failed"
        rm ${SDKROOT}/prebuilt/emsdk/lib${pkg}${PYBUILD}.a
    fi

    popd
popd


