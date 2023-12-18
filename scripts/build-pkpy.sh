#!/bin/bash
reset

export CI=${CI:-false}

export STATIC=${STATIC:-true}

export BUILDS=1.3
export PYBUILD=1.3
export MODE=main


. scripts/vendoring.sh




pushd pythons/pykpocket/
    rm pymain
    python3 scripts/multiline_parser.py pyque-pocket.cpp > pykpocket.gen
    python3 scripts/multiline_parser.py pyque-pocket_begin.cpp > pykpocket_begin.gen
    python3 scripts/multiline_parser.py pyque-pocket_main.cpp > pykpocket_main.gen

#    pushd ../pykpocket.native
#    rm libpocketpy.*
#    if make && (echo 'print(42)' | ./main)
#    then
#        popd

#        if clang++ -DPYDK -std=c++17 -O1 -fPIC -fexceptions -Iinclude -o pymain pykpocket_main.cpp ../pykpocket.native/libpocketpy.a
#        then
#            if ./pymain
#            then
                mkdir -p ../pykpocket.js ../pykpocket.html

                pushd ../pykpocket.html
                . /opt/python-wasm-sdk/wasm32-*-emscripten-shell.sh

                if [ -f Makefile ]
                then
                    echo cmake already ran
                    rm libpocketpy.a
                else
                    emcmake cmake ../pykpocket -DTARGET=html -DCMAKE_EXECUTABLE_SUFFIX=html
                fi
                emmake make
                popd

#            fi
#        fi
#    else
#        popd
#    fi
popd

ALWAYS_ASSETS=$(realpath assets/pkpy)


mkdir -p $DIST_DIR/pkpy${PYMAJOR}${PYMINOR}

rm $DIST_DIR/pkpy${PYMAJOR}${PYMINOR}/main.* 2>/dev/null


echo "
    *   building loader $(pwd) for ${VENDOR} / ${PACKAGES}
            PYBUILD=$PYBUILD python${PYMAJOR}${PYMINOR}
            EMFLAVOUR=$EMFLAVOUR
            EMSDK=$EMSDK
            SDKROOT=$SDKROOT
            PYTHONPYCACHEPREFIX=$PYTHONPYCACHEPREFIX
            HPY=$HPY
            LD_VENDOR=$LD_VENDOR

            toward : $DIST_DIR/pkpy${PYMAJOR}${PYMINOR}/
" 1>&2

    # clang++ -DPYDK -std=c++17 -O1 -fPIC -fexceptions -Iinclude -o pymain pykpocket_main.cpp -L../pykpocket.native -lpocketpy
#  -fvisibility=hidden \
    emcc -fPIC -std=gnu99 -Os -g0 -DPYDK=1 -DPKPY=1 \
 -sFORCE_FILESYSTEM=1 -sMAIN_MODULE=2 \
 -fexceptions -sASSERTIONS=0 -sMODULARIZE=0 -sEXTRA_EXPORTED_RUNTIME_METHODS=FS \
 -Ipythons/pykpocket -Ipythons/pykpocket/include \
 -sTOTAL_MEMORY=256MB -sSTACK_SIZE=4MB -sALLOW_TABLE_GROWTH -sALLOW_MEMORY_GROWTH \
 --use-preload-plugins \
 --preload-file ${ALWAYS_ASSETS}@/data/data/org.python/assets \
 -o ${DIST_DIR}/pkpy${PYMAJOR}${PYMINOR}/${MODE}.js pythons/pykpocket/pymain.c \
 -Lpythons/pykpocket.html -lpocketpy

du -hs ${DIST_DIR}/pkpy${PYMAJOR}${PYMINOR}/*



