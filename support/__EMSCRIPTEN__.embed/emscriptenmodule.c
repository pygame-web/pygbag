/**
 * PANDA 3D SOFTWARE
 * Copyright (c) Carnegie Mellon University.  All rights reserved.
 *
 * All use of this software is subject to the terms of the revised BSD
 * license.  You should have received a copy of this license along
 * with this source code in a file named "LICENSE."
 *
 * @file emscripten.c
 * @author rdb
 * @date 2021-02-02
 */

#undef _POSIX_C_SOURCE
#undef _XOPEN_SOURCE
#define PY_SSIZE_T_CLEAN 1

#include "Python.h"
#include <emscripten/emscripten.h>

/**
 * Decrefs the result of the function call, and prints out an exception if
 * one occurred.
 */
static void
_handle_callback_result(PyObject *result, char *context) {
  if (result != NULL) {
    Py_DECREF(result);
  }
  else {
    fprintf(stderr, "Exception in %s callback:\n", "async_call");
    PyErr_Print();
  }
}

/**
 * Python wrapper for
 * void emscripten_run_script(const char *script)
 */
static PyObject *
_py_run_script(PyObject *self, PyObject *arg) {
  const char *script = PyUnicode_AsUTF8(arg);
  if (script != NULL) {
    emscripten_run_script(script);
    Py_INCREF(Py_None);
    return Py_None;
  }
  return NULL;
}

/**
 * Python wrapper for
 * int emscripten_run_script_int(const char *script)
 */
static PyObject *
_py_run_script_int(PyObject *self, PyObject *arg) {
  const char *script = PyUnicode_AsUTF8(arg);
  if (script != NULL) {
    return PyLong_FromLong(emscripten_run_script_int(script));
  }
  return NULL;
}

/**
 * Python wrapper for
 * char *emscripten_run_script_string(const char *script);
 */
static PyObject *
_py_run_script_string(PyObject *self, PyObject *arg) {
  const char *script = PyUnicode_AsUTF8(arg);
  if (script != NULL) {
    return PyUnicode_FromString(emscripten_run_script_string(script));
  }
  return NULL;
}

/**
 * Python wrapper for
 * void emscripten_async_run_script(const char *script, int millis)
 */
static PyObject *
_py_async_run_script(PyObject *self, PyObject *args, PyObject *kw) {
  char *script;
  int millis = 0;
  static const char *const keywords[] = {"", "millis", NULL};
  if (PyArg_ParseTupleAndKeywords(args, kw, "s|i", (char **)keywords, &script, &millis)) {
    emscripten_async_run_script(script, millis);
    Py_INCREF(Py_None);
    return Py_None;
  }
  return NULL;
}

/**
 * Python wrapper for
 * int emscripten_set_main_loop_timing(int mode, int value)
 */
static PyObject *
_py_set_main_loop_timing(PyObject *self, PyObject *args) {
  int mode;
  int value;
  if (PyArg_ParseTuple(args, "ii", &mode, &value)) {
    int return_value = emscripten_set_main_loop_timing(mode, value);
    return PyLong_FromLong(return_value);
  }
  return NULL;
}

/**
 * Python wrapper for
 * void emscripten_pause_main_loop(void)
 */
static PyObject *
_py_pause_main_loop(PyObject *self, PyObject *noarg) {
  emscripten_pause_main_loop();
  Py_INCREF(Py_None);
  return Py_None;
}

/**
 * Python wrapper for
 * void emscripten_resume_main_loop(void)
 */
static PyObject *
_py_resume_main_loop(PyObject *self, PyObject *noarg) {
  emscripten_resume_main_loop();
  Py_INCREF(Py_None);
  return Py_None;
}

/**
 * Python wrapper for
 * void emscripten_cancel_main_loop(void)
 */
static PyObject *
_py_cancel_main_loop(PyObject *self, PyObject *noarg) {
  emscripten_cancel_main_loop();
  Py_INCREF(Py_None);
  return Py_None;
}

/**
 * Python wrapper for
 * void emscripten_set_main_loop_expected_blockers(int num)
 */
static PyObject *
_py_set_main_loop_expected_blockers(PyObject *self, PyObject *args) {
  int num;
  if (PyArg_ParseTuple(args, "i", &num)) {
    emscripten_set_main_loop_expected_blockers(num);
    Py_INCREF(Py_None);
    return Py_None;
  }
  return NULL;
}

/**
 * Callback wrapper for emscripten.async_call().
 */
static void
_call_callback(void *data) {
  PyObject *func = (PyObject *)data;
  PyObject *result = PyObject_CallNoArgs(func);
  Py_DECREF(func);
  _handle_callback_result(result, "async_call");
}

/**
 * Python wrapper for
 * void emscripten_async_call(em_arg_callback_func func, void *arg, int millis)
 */
static PyObject *
_py_async_call(PyObject *self, PyObject *args, PyObject *kw) {
  PyObject *func;
  int millis;
  static const char *const keywords[] = {"", "millis", NULL};
  if (PyArg_ParseTupleAndKeywords(args, kw, "O|i", (char **)keywords, &func, &millis)) {
    if (!PyCallable_Check(func)) {
      PyErr_SetString(PyExc_TypeError, "expected callable");
      return NULL;
    }
    Py_INCREF(func);
    emscripten_async_call(_call_callback, func, millis);
    Py_INCREF(Py_None);
    return Py_None;
  }
  return NULL;
}

/**
 * Python wrapper for
 * void emscripten_exit_with_live_runtime(void)
 */
static PyObject *
_py_exit_with_live_runtime(PyObject *self, PyObject *noarg) {
  emscripten_exit_with_live_runtime();
  Py_INCREF(Py_None);
  return Py_None;
}

/**
 * Python wrapper for
 * void emscripten_force_exit(int status)
 */
static PyObject *
_py_force_exit(PyObject *self, PyObject *args) {
  int status;
  if (PyArg_ParseTuple(args, "i", &status)) {
    emscripten_force_exit(status);
    Py_INCREF(Py_None);
    return Py_None;
  }
  return NULL;
}

/**
 * Python wrapper for
 * double emscripten_get_device_pixel_ratio(void)
 */
static PyObject *
_py_get_device_pixel_ratio(PyObject *self, PyObject *noarg) {
  double return_value = emscripten_get_device_pixel_ratio();
  return PyFloat_FromDouble(return_value);
}

/**
 * Python wrapper for
 * char *emscripten_get_window_title(void)
 */
static PyObject *
_py_get_window_title(PyObject *self, PyObject *noarg) {
  char *return_value = emscripten_get_window_title();
  return PyUnicode_FromString(return_value);
}

/**
 * Python wrapper for
 * void emscripten_set_window_title(char *title)
 */
static PyObject *
_py_set_window_title(PyObject *self, PyObject *arg) {
  const char *title = PyUnicode_AsUTF8(arg);
  if (title != NULL) {
    emscripten_set_window_title(title);
    Py_INCREF(Py_None);
    return Py_None;
  }
  return NULL;
}

/**
 * Python wrapper for
 * void emscripten_get_screen_size(int *width, int *height)
 */
static PyObject *
_py_get_screen_size(PyObject *self, PyObject *noarg) {
  int width, height;
  emscripten_get_screen_size(&width, &height);
  return Py_BuildValue("(ii)", width, height);
}

/**
 * Python wrapper for
 * void emscripten_hide_mouse(void)
 */
static PyObject *
_py_hide_mouse(PyObject *self, PyObject *noarg) {
  emscripten_hide_mouse();
  Py_INCREF(Py_None);
  return Py_None;
}

/**
 * Python wrapper for
 * double emscripten_get_now(void)
 */
static PyObject *
_py_get_now(PyObject *self, PyObject *noarg) {
  double return_value = emscripten_get_now();
  return PyFloat_FromDouble(return_value);
}

/**
 * Python wrapper for
 * float emscripten_random(void)
 */
static PyObject *
_py_random(PyObject *self, PyObject *noarg) {
  float return_value = emscripten_random();
  return PyFloat_FromDouble(return_value);
}

/**
 * Callback handler for emscripten.async_wget().
 */
void EMSCRIPTEN_KEEPALIVE
_wget_callback(PyObject *func, PyObject *otherfunc, char *file) {
  // Also decrease the reference count on the function we're *not* calling,
  // since it will no longer be called.
  Py_XDECREF(otherfunc);

  if (func != NULL) {
    PyObject *result = PyObject_CallFunction(func, "s", file);
    Py_DECREF(func);
    _handle_callback_result(result, "async_wget");
  }
}

/**
 * Python wrapper for
 * void emscripten_async_wget(const char* url, const char* file, em_str_callback_func onload, em_str_callback_func onerror)
 */
static PyObject *
_py_async_wget(PyObject *self, PyObject *args, PyObject *kw) {
  char *url;
  char *file;
  PyObject *onload = NULL;
  PyObject *onerror = NULL;

  static const char *const keywords[] = {"url", "file", "onload", "onerror", NULL};
  if (PyArg_ParseTupleAndKeywords(args, kw, "ss|OO", (char **)keywords, &url, &file, &onload, &onerror)) {
    if (onload != NULL && !PyCallable_Check(onload)) {
      PyErr_SetString(PyExc_TypeError, "expected callable for onload");
      return NULL;
    }
    if (onerror != NULL && !PyCallable_Check(onerror)) {
      PyErr_SetString(PyExc_TypeError, "expected callable for onerror");
      return NULL;
    }

    Py_XINCREF(onload);
    Py_XINCREF(onerror);

    // We actually just excerpt the definition of the function here, so that we
    // can get the memory management for the callback right.
    EM_ASM({
      var _url = UTF8ToString($0);
      var _file = UTF8ToString($1);
      _file = PATH_FS.resolve(_file);
      function doCallback(callback, other) {
        var stack = stackSave();
        __wget_callback(callback, other, allocate(intArrayFromString(_file), ALLOC_STACK));
        stackRestore(stack);
      }
      var destinationDirectory = PATH.dirname(_file);
      FS.createPreloadedFile(
        destinationDirectory,
        PATH.basename(_file),
        _url, true, true,
        function() {
          doCallback($2, $3);
        },
        function() {
          doCallback($3, $2);
        },
        false,
        false,
        function() {
          try {
            FS.unlink(_file);
          } catch (e) {}
          FS.mkdirTree(destinationDirectory);
        }
      );
    }, url, file, onload, onerror);

    Py_INCREF(Py_None);
    return Py_None;
  }

  return NULL;
}

/**
 * Returns callbacks associated with a given handle.
 */
static void
_wget2_pop_callbacks(unsigned handle, PyObject **onload, PyObject **onerror, PyObject **onprogress) {
  EM_ASM({
    var http = (Browser.wgetRequests || wget.wgetRequests)[$0];
    if (http) {
      setValue($1, http.__py_onload, 'i32');
      setValue($2, http.__py_onerror, 'i32');
      setValue($3, http.__py_onprogress, 'i32');
      http.__py_onload = 0;
      http.__py_onerror = 0;
      http.__py_onprogress = 0;
    }
  }, handle, onload, onerror, onprogress);
}

/**
 * Callback wrappers for emscripten_async_wget2.
 */
static void
_wget2_onload_callback(unsigned handle, void *arg, const char *file) {
  PyObject *onload = NULL;
  PyObject *onerror = NULL;
  PyObject *onprogress = NULL;
  _wget2_pop_callbacks(handle, &onload, &onerror, &onprogress);
  Py_XDECREF(onerror);
  Py_XDECREF(onprogress);

  if (onload != NULL) {
    PyObject *result = PyObject_CallFunction(onload, "Is", handle, file);
    Py_DECREF(onload);
    _handle_callback_result(result, "async_wget2");
  }
}

static void
_wget2_onerror_callback(unsigned handle, void *arg, int status) {
  PyObject *onload = NULL;
  PyObject *onerror = NULL;
  PyObject *onprogress = NULL;
  _wget2_pop_callbacks(handle, &onload, &onerror, &onprogress);
  Py_XDECREF(onload);
  Py_XDECREF(onprogress);

  if (onerror != NULL) {
    PyObject *result = PyObject_CallFunction(onerror, "Ii", handle, status);
    Py_DECREF(onerror);
    _handle_callback_result(result, "async_wget2");
  }
}

static void
_wget2_onprogress_callback(unsigned handle, void *arg, int progress) {
  PyObject *onprogress = (PyObject *)EM_ASM_INT({
    var http = (Browser.wgetRequests || wget.wgetRequests)[$0];
    return http ? http.__py_onprogress : 0;
  }, handle);

  if (onprogress != NULL) {
    PyObject *result = PyObject_CallFunction(onprogress, "Ii", handle, progress);
    _handle_callback_result(result, "async_wget2");
  }
}

/**
 * Python wrapper for
 * int emscripten_async_wget2(const char* url, const char* file, const char* requesttype, const char* param, void *arg, em_async_wget2_onload_func onload, em_async_wget2_onstatus_func onerror, em_async_wget2_onstatus_func onprogress)
 */
static PyObject *
_py_async_wget2(PyObject *self, PyObject *args, PyObject *kw) {
  char *url;
  char *file;
  char *requesttype = "GET";
  char *param = "";
  PyObject *onload = NULL;
  PyObject *onerror = NULL;
  PyObject *onprogress = NULL;

  static const char *const keywords[] = {"url", "file", "requesttype", "param", "onload", "onerror", "onprogress", NULL};
  if (PyArg_ParseTupleAndKeywords(args, kw, "ss|ss$OOO", (char **)keywords, &url, &file, &requesttype, &param, &onload, &onerror, &onprogress)) {
    if (onload != NULL && !PyCallable_Check(onload)) {
      PyErr_SetString(PyExc_TypeError, "expected callable for onload");
      return NULL;
    }
    if (onerror != NULL && !PyCallable_Check(onerror)) {
      PyErr_SetString(PyExc_TypeError, "expected callable for onerror");
      return NULL;
    }
    if (onprogress != NULL && !PyCallable_Check(onprogress)) {
      PyErr_SetString(PyExc_TypeError, "expected callable for onprogress");
      return NULL;
    }
    Py_XINCREF(onload);
    Py_XINCREF(onerror);
    Py_XINCREF(onprogress);
    int handle = emscripten_async_wget2(url, file, requesttype, param, NULL,
                                        _wget2_onload_callback,
                                        _wget2_onerror_callback,
                                        _wget2_onprogress_callback);
    EM_ASM({
      var http = (Browser.wgetRequests || wget.wgetRequests)[$0];
      http.__py_onload = $1;
      http.__py_onerror = $2;
      http.__py_onprogress = $3;
    }, handle, onload, onerror, onprogress);
    return PyLong_FromLong(handle);
  }
  return NULL;
}

/**
 * Callback wrappers for emscripten_async_wget2_data.
 */
static void
_wget2_data_onload_callback(unsigned handle, void *arg, void *buffer, unsigned size) {
  PyObject *onload = NULL;
  PyObject *onerror = NULL;
  PyObject *onprogress = NULL;
  _wget2_pop_callbacks(handle, &onload, &onerror, &onprogress);
  Py_XDECREF(onerror);
  Py_XDECREF(onprogress);

  if (onload != NULL) {
    PyObject *memoryview = PyMemoryView_FromMemory((char *)buffer, size, PyBUF_READ);
    PyObject *result = PyObject_CallFunction(onload, "IN", handle, memoryview);
    Py_DECREF(onload);
    _handle_callback_result(result, "async_wget2_data");
  }
}

static void
_wget2_data_onerror_callback(unsigned handle, void *arg, int status, const char *message) {
  PyObject *onload = NULL;
  PyObject *onerror = NULL;
  PyObject *onprogress = NULL;
  _wget2_pop_callbacks(handle, &onload, &onerror, &onprogress);
  Py_XDECREF(onload);
  Py_XDECREF(onprogress);

  if (onerror != NULL) {
    PyObject *result = PyObject_CallFunction(onerror, "Iis", handle, status, message);
    Py_DECREF(onerror);
    _handle_callback_result(result, "async_wget2_data");
  }
}

static void
_wget2_data_onprogress_callback(unsigned handle, void *arg, int loaded, int total) {
  PyObject *onprogress = (PyObject *)EM_ASM_INT({
    var http = (Browser.wgetRequests || wget.wgetRequests)[$0];
    return http ? http.__py_onprogress : 0;
  }, handle);

  if (onprogress != NULL) {
    PyObject *result = PyObject_CallFunction(onprogress, "Iii", handle, loaded, total);
    _handle_callback_result(result, "async_wget2_data");
  }
}

/**
 * Python wrapper for
 * int emscripten_async_wget2_data(const char* url, const char* requesttype, const char* param, void *arg, int free, em_async_wget2_data_onload_func onload, em_async_wget2_data_onerror_func onerror, em_async_wget2_data_onprogress_func onprogress)
 */
static PyObject *
_py_async_wget2_data(PyObject *self, PyObject *args, PyObject *kw) {
  char *url;
  char *requesttype = "GET";
  char *param = "";
  PyObject *onload = NULL;
  PyObject *onerror = NULL;
  PyObject *onprogress = NULL;

  static const char *const keywords[] = {"url", "requesttype", "param", "onload", "onerror", "onprogress", NULL};
  if (PyArg_ParseTupleAndKeywords(args, kw, "s|ss$OOO", (char **)keywords, &url, &requesttype, &param, &onload, &onerror, &onprogress)) {
    if (onload != NULL && !PyCallable_Check(onload)) {
      PyErr_SetString(PyExc_TypeError, "expected callable for onload");
      return NULL;
    }
    if (onerror != NULL && !PyCallable_Check(onerror)) {
      PyErr_SetString(PyExc_TypeError, "expected callable for onerror");
      return NULL;
    }
    if (onprogress != NULL && !PyCallable_Check(onprogress)) {
      PyErr_SetString(PyExc_TypeError, "expected callable for onprogress");
      return NULL;
    }
    Py_XINCREF(onload);
    Py_XINCREF(onerror);
    Py_XINCREF(onprogress);
    int handle = emscripten_async_wget2_data(url, requesttype, param, NULL, 1,
                                             _wget2_data_onload_callback,
                                             _wget2_data_onerror_callback,
                                             _wget2_data_onprogress_callback);
    EM_ASM({
      var http = (Browser.wgetRequests || wget.wgetRequests)[$0];
      http.__py_onload = $1;
      http.__py_onerror = $2;
      http.__py_onprogress = $3;
    }, handle, onload, onerror, onprogress);
    return PyLong_FromLong(handle);
  }
  return NULL;
}

/**
 * Python wrapper for
 * void emscripten_async_wget_abort(int handle)
 */
static PyObject *
_py_async_wget2_abort(PyObject *self, PyObject *args) {
  int handle;
  if (PyArg_ParseTuple(args, "i", &handle)) {
    emscripten_async_wget2_abort((int)handle);
    Py_INCREF(Py_None);
    return Py_None;
  }
  return NULL;
}

/**
 * Python wrapper for
 * void emscripten_wget(const char *url, const char *file)
 */
static PyObject *
_py_wget(PyObject *self, PyObject *args) {
  char *url;
  char *file;
  if (PyArg_ParseTuple(args, "ss", &url, &file)) {
    emscripten_wget(url, file);
    Py_INCREF(Py_None);
    return Py_None;
  }
  return NULL;
}

/**
 * Python wrapper for
 * worker_handle emscripten_create_worker(const char *url)
 */
static PyObject *
_py_create_worker(PyObject *self, PyObject *args) {
  char *url;
  if (PyArg_ParseTuple(args, "s", &url)) {
    worker_handle return_value = emscripten_create_worker(url);
    return PyLong_FromLong(return_value);
  }
  return NULL;
}

/**
 * Python wrapper for
 * void emscripten_destroy_worker(worker_handle worker)
 */
static PyObject *
_py_destroy_worker(PyObject *self, PyObject *args) {
  int worker;
  if (PyArg_ParseTuple(args, "i", &worker)) {
    emscripten_destroy_worker((worker_handle)worker);
    Py_INCREF(Py_None);
    return Py_None;
  }
  return NULL;
}

/**
 * Callback wrapper for emscripten_call_worker.
 */
/*
static void
_worker_callback(char *buffer, int size, void *data) {
  PyObject *func = (PyObject *)data;
  PyObject *result = PyObject_CallNoArgs(func);
  Py_DECREF(func);
  _handle_callback_result(result, "call_worker");
}
*/

/**
 * Python wrapper for
 * void emscripten_call_worker(worker_handle worker, const char *funcname, char *data, int size, em_worker_callback_func callback, void *arg)
 */
/*
static PyObject *
_py_call_worker(PyObject *self, PyObject *args) {
  int worker;
  char *funcname;
  char *data;
  Py_ssize_t size;
  PyObject *callback = NULL;
  if (PyArg_ParseTuple(args, "iss#|O", &worker, &funcname, &data, &size, callback)) {
    if (callback != NULL) {
      if (!PyCallable_Check(callback)) {
        PyErr_SetString(PyExc_TypeError, "expected callable");
        return NULL;
      }
      Py_INCREF(callback);
      emscripten_call_worker((worker_handle)worker, funcname, data, (int)size, _worker_callback, callback);
    }
    else {
      emscripten_call_worker((worker_handle)worker, funcname, data, (int)size, NULL, NULL);
    }
    Py_INCREF(Py_None);
    return Py_None;
  }
  return NULL;
}
*/

/**
 * Python wrapper for
 * void emscripten_worker_respond(char *data, int size)
 */
/*
static PyObject *
_py_worker_respond(PyObject *self, PyObject *arg) {
  char *data;
  Py_ssize_t size;
  if (PyBytes_AsStringAndSize(arg, &data, &size) == 0) {
    emscripten_worker_respond(data, (int)size);
    Py_INCREF(Py_None);
    return Py_None;
  }
  return NULL;
}
*/

/**
 * Python wrapper for
 * void emscripten_worker_respond_provisionally(char *data, int size)
 */
/*
static PyObject *
_py_worker_respond_provisionally(PyObject *self, PyObject *arg) {
  char *data;
  Py_ssize_t size;
  if (PyBytes_AsStringAndSize(arg, &data, &size) == 0) {
    emscripten_worker_respond_provisionally(data, (int)size);
    Py_INCREF(Py_None);
    return Py_None;
  }
  return NULL;
}
*/

/**
 * Python wrapper for
 * int emscripten_get_worker_queue_size(worker_handle worker)
 */
static PyObject *
_py_get_worker_queue_size(PyObject *self, PyObject *args) {
  int worker;
  if (PyArg_ParseTuple(args, "i", &worker)) {
    int return_value = emscripten_get_worker_queue_size((worker_handle)worker);
    return PyLong_FromLong(return_value);
  }
  return NULL;
}

/**
 * Python wrapper for
 * int emscripten_get_compiler_setting(const char *name)
 */
static PyObject *
_py_get_compiler_setting(PyObject *self, PyObject *arg) {
  const char *name = PyUnicode_AsUTF8(arg);
  if (name != NULL) {
    int return_value = emscripten_get_compiler_setting(name);
    return PyLong_FromLong(return_value);
  }
  return NULL;
}

/**
 * Python wrapper for
 * int emscripten_has_asyncify(void)
 */
static PyObject *
_py_has_asyncify(PyObject *self, PyObject *noarg) {
  return PyBool_FromLong(emscripten_has_asyncify());
}

/**
 * Python wrapper for
 * void emscripten_debugger(void)
 */
static PyObject *
_py_debugger(PyObject *self, PyObject *noarg) {
  emscripten_debugger();
  Py_INCREF(Py_None);
  return Py_None;
}

/**
 * Python wrapper for
 * void emscripten_log(int flags, const char *format, ...)
 */
static PyObject *
_py_log(PyObject *self, PyObject *args) {
  int flags;
  char *msg;
  if (PyArg_ParseTuple(args, "is", &flags, &msg)) {
    emscripten_log(flags, "%s", msg);
    Py_INCREF(Py_None);
    return Py_None;
  }
  return NULL;
}

/**
 * Python wrapper for
 * int emscripten_get_callstack(int flags, char *out, int maxbytes)
 */
static PyObject *
_py_get_callstack(PyObject *self, PyObject *args) {
  int flags;
  if (PyArg_ParseTuple(args, "i", &flags)) {
    int num_bytes = emscripten_get_callstack(flags, NULL, 0);
    assert(num_bytes > 0);

    char *data = (char *)alloca((size_t)num_bytes);
    num_bytes = emscripten_get_callstack(flags, data, num_bytes);
    return PyUnicode_FromStringAndSize(data, num_bytes);
  }
  return NULL;
}

/**
 * Python wrapper for
 * void emscripten_sleep(unsigned int ms)
 */
static PyObject *
_py_sleep(PyObject *self, PyObject *arg) {
  PyObject *ms = PyNumber_Long(arg);
  if (ms != NULL) {
    emscripten_sleep((unsigned int)PyLong_AsUnsignedLong(ms));
    Py_DECREF(ms);
    Py_INCREF(Py_None);
    return Py_None;
  }
  return NULL;
}


static PyMethodDef python_simple_funcs[] = {
  { "run_script", &_py_run_script, METH_O },
  { "run_script_int", &_py_run_script_int, METH_O },
  { "run_script_string", &_py_run_script_string, METH_O },
  { "async_run_script", (PyCFunction)&_py_async_run_script, METH_VARARGS | METH_KEYWORDS },
  { "set_main_loop_timing", &_py_set_main_loop_timing, METH_VARARGS },
  { "pause_main_loop", &_py_pause_main_loop, METH_NOARGS },
  { "resume_main_loop", &_py_resume_main_loop, METH_NOARGS },
  { "cancel_main_loop", &_py_cancel_main_loop, METH_NOARGS },
  { "set_main_loop_expected_blockers", &_py_set_main_loop_expected_blockers, METH_VARARGS },
  { "async_call", (PyCFunction)&_py_async_call, METH_VARARGS | METH_KEYWORDS },
  { "exit_with_live_runtime", &_py_exit_with_live_runtime, METH_NOARGS },
  { "force_exit", &_py_force_exit, METH_VARARGS },
  { "get_device_pixel_ratio", &_py_get_device_pixel_ratio, METH_NOARGS },
  { "get_window_title", &_py_get_window_title, METH_NOARGS },
  { "set_window_title", &_py_set_window_title, METH_O },
  { "get_screen_size", &_py_get_screen_size, METH_NOARGS },
  { "hide_mouse", &_py_hide_mouse, METH_NOARGS },
  { "get_now", &_py_get_now, METH_NOARGS },
  { "random", &_py_random, METH_NOARGS },
  { "async_wget", (PyCFunction)&_py_async_wget, METH_VARARGS | METH_KEYWORDS },
  { "async_wget2", (PyCFunction)&_py_async_wget2, METH_VARARGS | METH_KEYWORDS },
  { "async_wget2_data", (PyCFunction)&_py_async_wget2_data, METH_VARARGS | METH_KEYWORDS },
  { "async_wget2_abort", &_py_async_wget2_abort, METH_VARARGS },
  { "wget", &_py_wget, METH_VARARGS },
  { "create_worker", &_py_create_worker, METH_VARARGS },
  { "destroy_worker", &_py_destroy_worker, METH_VARARGS },
//  { "worker_respond", &_py_worker_respond, METH_O },
//  { "worker_respond_provisionally", &_py_worker_respond_provisionally, METH_O },
  { "get_worker_queue_size", &_py_get_worker_queue_size, METH_VARARGS },
  { "get_compiler_setting", &_py_get_compiler_setting, METH_O },
  { "has_asyncify", &_py_has_asyncify, METH_NOARGS },
  { "debugger", &_py_debugger, METH_NOARGS },
  { "log", &_py_log, METH_VARARGS },
  { "get_callstack", &_py_get_callstack, METH_VARARGS },
  { "sleep", &_py_sleep, METH_O },
  { NULL, NULL }
};

static struct PyModuleDef emscripten_module = {
  PyModuleDef_HEAD_INIT,
  "emscripten",
  NULL,
  -1,
  python_simple_funcs,
  NULL, NULL, NULL, NULL
};

#ifdef _WIN32
extern __declspec(dllexport) PyObject *PyInit_emscripten();
#elif __GNUC__ >= 4
extern __attribute__((visibility("default"))) PyObject *PyInit_emscripten();
#else
extern PyObject *PyInit_emscripten();
#endif

PyObject *PyInit_emscripten() {
  return PyModule_Create(&emscripten_module);
}
