#ifndef PYGBAG_H
#define PYGBAG_H

#if defined(__EMSCRIPTEN__)
#   include "emscripten.h"
#else

#   define em_callback_func void
#   define emscripten_set_main_loop(func, fps, simloop) { while(em_running) func(); }
#   define emscripten_cancel_main_loop() { em_running = false; }
#   define emscripten_run_script(js) { puts("Host Call");puts(js); }
#   define __EMSCRIPTEN_major__ 0
#   define __EMSCRIPTEN_minor__ 0
#   define __EMSCRIPTEN_tiny__ 0
#endif

#define HOST_RETURN_YIELD  return NULL


#if __PKPY__

#define PYGBAG_INIT_VM vm = new VM()

#define PyMODINIT_FUNC PyObject *
#define PyNULL NULL
#define Py_RETURN_NONE return vm->None


#define PyImport_AppendInittab(Name, PyInit_Name) PyInit_Name()

#endif // __PKPY__


#endif // PYGBAG_H
