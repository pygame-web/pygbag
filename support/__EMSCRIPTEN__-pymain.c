/* Minimal main program -- everything is loaded from the library */

#include "Python.h"

#if __PYDK__

static PyStatus
pymain_init(const void *args)
{
    PyStatus status;
    Py_Initialize();
    return status;
}

static void
pymain_free(void)
{
    Py_FinalizeEx();
}

// run a main customized for browser/wasi fd and renderAnimationFrame.
#include "__EMSCRIPTEN__.c"

#else
// normal host build.
int
main(int argc, char **argv)
{
    return Py_BytesMain(argc, argv);
}
#endif //#if __PYDK__
