/**
 * PANDA 3D SOFTWARE
 * Copyright (c) Carnegie Mellon University.  All rights reserved.
 *
 * All use of this software is subject to the terms of the revised BSD
 * license.  You should have received a copy of this license along
 * with this source code in a file named "LICENSE."
 *
 * @file browsermodule.c
 * @author rdb
 * @date 2021-02-02
 */

#undef _POSIX_C_SOURCE
#undef _XOPEN_SOURCE
#define PY_SSIZE_T_CLEAN 1

#include "Python.h"
#include "structmember.h"

#include <emscripten/emscripten.h>
#include <stdbool.h>

/**
 * emval interface, excerpted from emscripten/val.h (which is C++)
 */
typedef const void* TYPEID;

void _emval_register_symbol(const char*);

enum {
  _EMVAL_UNDEFINED = 1,
  _EMVAL_NULL = 2,
  _EMVAL_TRUE = 3,
  _EMVAL_FALSE = 4
};

typedef struct _EM_VAL* EM_VAL;
typedef struct _EM_DESTRUCTORS* EM_DESTRUCTORS;
typedef struct _EM_METHOD_CALLER* EM_METHOD_CALLER;
typedef double EM_GENERIC_WIRE_TYPE;
typedef const void* EM_VAR_ARGS;

void _emval_incref(EM_VAL value);
void _emval_decref(EM_VAL value);

void _emval_run_destructors(EM_DESTRUCTORS handle);

EM_VAL _emval_new_array();
EM_VAL _emval_new_object();
EM_VAL _emval_new_cstring(const char*);

EM_VAL _emval_take_value(TYPEID type, EM_VAR_ARGS argv);

EM_VAL _emval_new(
  EM_VAL value,
  unsigned argCount,
  const TYPEID argTypes[],
  EM_VAR_ARGS argv);

EM_VAL _emval_get_global(const char* name);
EM_VAL _emval_get_module_property(const char* name);
EM_VAL _emval_get_property(EM_VAL object, EM_VAL key);
void _emval_set_property(EM_VAL object, EM_VAL key, EM_VAL value);
EM_GENERIC_WIRE_TYPE _emval_as(EM_VAL value, TYPEID returnType, EM_DESTRUCTORS* destructors);

bool _emval_equals(EM_VAL first, EM_VAL second);
bool _emval_strictly_equals(EM_VAL first, EM_VAL second);
bool _emval_greater_than(EM_VAL first, EM_VAL second);
bool _emval_less_than(EM_VAL first, EM_VAL second);
bool _emval_not(EM_VAL object);

EM_VAL _emval_call(
  EM_VAL value,
  unsigned argCount,
  const TYPEID argTypes[],
  EM_VAR_ARGS argv);

// DO NOT call this more than once per signature. It will
// leak generated function objects!
EM_METHOD_CALLER _emval_get_method_caller(
  unsigned argCount, // including return value
  const TYPEID argTypes[]);
EM_GENERIC_WIRE_TYPE _emval_call_method(
  EM_METHOD_CALLER caller,
  EM_VAL handle,
  const char* methodName,
  EM_DESTRUCTORS* destructors,
  EM_VAR_ARGS argv);
void _emval_call_void_method(
  EM_METHOD_CALLER caller,
  EM_VAL handle,
  const char* methodName,
  EM_VAR_ARGS argv);
EM_VAL _emval_typeof(EM_VAL value);
bool _emval_instanceof(EM_VAL object, EM_VAL constructor);
bool _emval_is_number(EM_VAL object);
bool _emval_is_string(EM_VAL object);
bool _emval_in(EM_VAL item, EM_VAL object);
bool _emval_delete(EM_VAL object, EM_VAL property);
bool _emval_throw(EM_VAL object);
EM_VAL _emval_await(EM_VAL promise);

/**
 * Forward declarations.
 */
static EM_VAL py_to_emval(PyObject *val);
static PyObject *emval_to_py(EM_VAL val);
static PyTypeObject Object_Type;
static PyTypeObject Function_Type;
static PyTypeObject Symbol_Type;
static int _next_callback_id = 0;

typedef struct {
  PyObject_HEAD
  EM_VAL result; // 0 = pending, positive = result, negative = exception
  char asyncio_future_blocking;
} PromiseWrapper;

typedef struct {
  PyObject_HEAD
  EM_VAL handle;
} Object;

typedef struct {
  PyObject_HEAD
  EM_VAL handle;
  EM_VAL bound;
} Function;

typedef Object Symbol;

/**
 * Decrements refcount of this PromiseWrapper.
 */
static void
PromiseWrapper_dealloc(PromiseWrapper *self) {
  if (self->result != NULL) {
    _emval_decref((EM_VAL)abs((int)self->result));
  }
  Py_TYPE(self)->tp_free((PyObject *)self);
}

/**
 * Implements done().
 */
static PyObject *
PromiseWrapper_done(PromiseWrapper *self, PyObject *noarg) {
  return PyBool_FromLong(self->result != NULL);
}

/**
 * Implements cancelled().
 */
static PyObject *
PromiseWrapper_cancelled(PromiseWrapper *self, PyObject *noarg) {
  Py_INCREF(Py_False);
  return Py_False;
}

/**
 * Implements result().
 */
static PyObject *
PromiseWrapper_result(PromiseWrapper *self, PyObject *noarg) {
  if (self->result == NULL) {
    PyErr_SetString(PyExc_Exception, "Still pending.");
    return NULL;
  }
  _emval_incref((EM_VAL)abs((int)self->result));
  return emval_to_py(self->result);
}

/**
 * Implements iter() and await.
 */
static PyObject *
PromiseWrapper_iter(PyObject *self) {
  Py_INCREF(self);
  return self;
}

/**
 * Implements next().
 */
static PyObject *
PromiseWrapper_next(PromiseWrapper *self) {
  if (self->result == NULL) {
    Py_INCREF(self);
    return (PyObject *)self;
  }
  else {
    _emval_incref((EM_VAL)abs((int)self->result));
    PyObject *result = emval_to_py(self->result);
    if (result != NULL) {
      PyErr_SetObject(PyExc_StopIteration, result);
      Py_DECREF(result);
    }
    return NULL;
  }
}

/**
 * Defines future wrapper.
 */
static PyAsyncMethods PromiseWrapper_async = {
  .am_await = (unaryfunc)PromiseWrapper_iter,
};

static PyMethodDef PromiseWrapper_methods[] = {
  { "done", (PyCFunction)PromiseWrapper_done, METH_NOARGS },
  { "cancelled", (PyCFunction)PromiseWrapper_cancelled, METH_NOARGS },
  { "result", (PyCFunction)PromiseWrapper_result, METH_NOARGS },
  { NULL, NULL, 0 }
};

static PyMemberDef PromiseWrapper_members[] = {
  { "_asyncio_future_blocking", T_BOOL, offsetof(PromiseWrapper, asyncio_future_blocking), 0 },
  { NULL }
};

static PyTypeObject PromiseWrapper_Type = {
  PyVarObject_HEAD_INIT(NULL, 0)
  .tp_name = "browser.PromiseWrapper",
  .tp_doc = "JavaScript Promise wrapper",
  .tp_basicsize = sizeof(PromiseWrapper),
  .tp_itemsize = 0,
  .tp_flags = Py_TPFLAGS_DEFAULT,
  .tp_dealloc = (destructor)PromiseWrapper_dealloc,
  .tp_as_async = &PromiseWrapper_async,
  .tp_iter = (getiterfunc)PromiseWrapper_iter,
  .tp_iternext = (iternextfunc)PromiseWrapper_next,
  .tp_methods = PromiseWrapper_methods,
  .tp_members = PromiseWrapper_members,
  .tp_new = PyType_GenericNew,
};

/**
 * Sets promise wrapper result.
 */
void EMSCRIPTEN_KEEPALIVE
_py_notify_done(PromiseWrapper *wrapper, EM_VAL result_handle) {
  if (wrapper->result == NULL && result_handle != NULL) {
    wrapper->result = result_handle;
    Py_DECREF(wrapper);
  }
}

/**
 * Constructs a new Object, or if given a single argument, simply wraps that in
 * an Object (like how it works in JavaScript).
 */

/* unused function */
/*
static int
Object_init(Object *self, PyObject *args, PyObject *kwargs) {
  if (kwargs != NULL && PyDict_Size(kwargs) > 0) {
    PyErr_SetString(PyExc_TypeError, "Object() takes no keyword arguments");
    return -1;
  }

  if (PyTuple_GET_SIZE(args) > 0) {
    EM_VAL handle = py_to_emval(PyTuple_GET_ITEM(args, 0));
    if (handle == NULL) {
      return -1;
    }
    self->handle = handle;
  }
  else {
    self->handle = _emval_new_object();
  }
  return 0;
}
*/

/**
 * Decrements refcount of this Object.
 */
static void
Object_dealloc(Object *self) {
  _emval_decref(self->handle);
  Py_TYPE(self)->tp_free((PyObject *)self);
}

/**
 * Implements await.
 */
static PyObject *
Object_await(Object *self) {
  // Note that all JS objects are awaitable.  Non-thenables simply return a
  // resolved promise with the value already set.
  PromiseWrapper *wrapper = PyObject_New(PromiseWrapper, &PromiseWrapper_Type);
  wrapper->asyncio_future_blocking = 0;

  wrapper->result = (EM_VAL)EM_ASM_INT({
    var value = emval_handle_array[$0].value;
    if (value && typeof value.then === "function") {
      value.then(function (result) {
        __py_notify_done($1, Emval.toHandle(result));
      }, function (error) {
        __py_notify_done($1, -Emval.toHandle(error));
      });
      return 0;
    }
    else {
      // Already done, return the result.
      __emval_incref($0);
      return $0;
    }
  }, self->handle, wrapper);

  if (wrapper->result == NULL) {
    // This is decreffed by _py_notify_done.
    Py_INCREF(wrapper);
  }

  return (PyObject *)wrapper;
}

/**
 * Returns a string representation of the object.
 */
static PyObject *
Object_repr(Object *self) {
  char *str = (char *)EM_ASM_INT({
    var value = emval_handle_array[$0].value;
    var str = value.constructor ? value.constructor.name : 'Object';
    var len = lengthBytesUTF8(str) + 1;
    var buffer = _malloc(len);
    stringToUTF8(str, buffer, len);
    return buffer;
  }, self->handle);

  PyObject *result = PyUnicode_FromFormat("[object %s]", str);
  free(str);
  return result;
}

/**
 * Hash function.
 */
static Py_hash_t
Object_hash(Object *self) {
  return (Py_hash_t)self->handle;
}

/**
 * Returns a string representation of the object.
 */
static PyObject *
Object_str(Object *self) {
  char *str = (char *)EM_ASM_INT({
    var str = emval_handle_array[$0].value.toString();
    var len = lengthBytesUTF8(str) + 1;
    var buffer = _malloc(len);
    stringToUTF8(str, buffer, len);
    return buffer;
  }, self->handle);

  PyObject *result = PyUnicode_FromString(str);
  free(str);
  return result;
}

/**
 * Implements len().
 */
static Py_ssize_t
Object_length(Object *self) {
  int len = EM_ASM_INT({
    var val = emval_handle_array[$0].value;
    if (val[Symbol.iterator] && val.length !== undefined) {
      return val.length;
    }
    else {
      return -1;
    }
  }, self->handle);

  if (len >= 0) {
    return len;
  }
  else {
    PyErr_SetString(PyExc_TypeError, "object has no len()");
    return -1;
  }
}

/**
 * Gets a property of this object.
 */
static PyObject *
Object_getprop(Object *self, PyObject *item) {
  EM_VAL key_handle = py_to_emval(item);
  if (key_handle == NULL) {
    return NULL;
  }

  EM_VAL result = (EM_VAL)EM_ASM_INT({
    try {
      return Emval.toHandle(emval_handle_array[$0].value[emval_handle_array[$1].value]);
    }
    catch (ex) {
      return -Emval.toHandle(ex);
    }
    finally {
      __emval_decref($1);
    }
  }, self->handle, key_handle);

  PyObject *obj =  emval_to_py(result);
  if (obj != NULL && Py_TYPE(obj) == &Function_Type) {
    // Remember self, so that we can make bound method calls.
    _emval_incref(self->handle);
    ((Function *)obj)->bound = self->handle;
  }
  return obj;
}

/**
 * Sets a property of this object.
 */
static int
Object_setprop(Object *self, PyObject *item, PyObject *value) {
  EM_VAL key_handle = py_to_emval(item);
  if (key_handle == NULL) {
    return -1;
  }

  if (value != NULL) {
    EM_VAL value_val = py_to_emval(value);
    if (value_val == NULL) {
      return -1;
    }

    _emval_set_property(self->handle, key_handle, value_val);
    _emval_decref(value_val);
  }
  else {
    if (!_emval_delete(self->handle, key_handle)) {
      //_emval_decref(key_handle);
      //return -1;
    }
  }
  _emval_decref(key_handle);
  return 0;
}

/**
 * Comparison.
 */
static PyObject *
Object_richcompare(Object *self, PyObject *other, int op) {
  EM_VAL other_handle = py_to_emval(other);
  if (other_handle == NULL) {
    PyErr_Clear();
    Py_INCREF(Py_NotImplemented);
    return Py_NotImplemented;
  }

  switch (op) {
  case Py_LT:
    return PyBool_FromLong(_emval_less_than(self->handle, other_handle));

  case Py_LE:
    return PyBool_FromLong(!_emval_greater_than(self->handle, other_handle));

  case Py_EQ:
    return PyBool_FromLong(self->handle == other_handle ||
                           _emval_strictly_equals(self->handle, other_handle));

  case Py_NE:
    return PyBool_FromLong(self->handle != other_handle &&
                           !_emval_strictly_equals(self->handle, other_handle));

  case Py_GT:
    return PyBool_FromLong(_emval_greater_than(self->handle, other_handle));

  case Py_GE:
    return PyBool_FromLong(!_emval_less_than(self->handle, other_handle));
  }

  return NULL;
}

/**
 * Implements iter().
 */
static PyObject *
Object_iter(Object *self) {
  EM_VAL val = (EM_VAL)EM_ASM_INT({
    var val = emval_handle_array[$0].value;
    if (val[Symbol.iterator]) {
      return Emval.toHandle(val[Symbol.iterator]());
    } else {
      return 0;
    }
  }, self->handle);

  if (val == self->handle) {
    // Common case, don't create a new wrapper.
    Py_INCREF(self);
    return (PyObject *)self;
  }
  else if (val != NULL) {
    return emval_to_py(val);
  }
  else {
    PyErr_SetString(PyExc_TypeError, "object has no iter()");
    return NULL;
  }
}

/**
 * Implements next().
 */
static PyObject *
Object_next(Object *self) {
  EM_VAL val = (EM_VAL)EM_ASM_INT({
    var val = emval_handle_array[$0].value;
    if (!val.next) {
      return 0;
    }
    var result = val.next();
    if (result && !result.done) {
      return Emval.toHandle(result.value);
    } else {
      return 0;
    }
  }, self->handle);

  if (val != NULL) {
    return emval_to_py(val);
  }
  else {
    return NULL;
  }
}

/**
 * Implements dir().
 */
static PyObject *
Object_dir(Object *self, PyObject *noarg) {
  return emval_to_py((EM_VAL)EM_ASM_INT({
    var props = [];
    for (var prop in emval_handle_array[$0].value) {
      props.push(prop);
    }
    return Emval.toHandle(props);
  }, self->handle));
}

static PyAsyncMethods Object_async = {
  .am_await = (unaryfunc)Object_await,
};

static PyMappingMethods Object_mapping = {
  .mp_length = (lenfunc)Object_length,
  .mp_subscript = (binaryfunc)Object_getprop,
  .mp_ass_subscript = (objobjargproc)Object_setprop,
};

static PyMethodDef Object_methods[] = {
  { "__dir__", (PyCFunction)Object_dir, METH_NOARGS },
  { NULL, NULL },
};

static PyTypeObject Object_Type = {
  PyVarObject_HEAD_INIT(NULL, 0)
  .tp_name = "browser.Object",
  .tp_doc = "JavaScript object",
  .tp_basicsize = sizeof(Object),
  .tp_itemsize = 0,
  .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
  .tp_dealloc = (destructor)Object_dealloc,
  .tp_as_async = &Object_async,
  .tp_repr = (reprfunc)Object_repr,
  .tp_as_mapping = &Object_mapping,
  .tp_hash = (hashfunc)Object_hash,
  .tp_str = (reprfunc)Object_str,
  .tp_getattro = (getattrofunc)Object_getprop,
  .tp_setattro = (setattrofunc)Object_setprop,
  .tp_richcompare = (richcmpfunc)Object_richcompare,
  .tp_iter = (getiterfunc)Object_iter,
  .tp_iternext = (iternextfunc)Object_next,
  .tp_methods = Object_methods,
  .tp_new = PyType_GenericNew,
};

/**
 * Decrements refcount of this Function.
 */
static void
Function_dealloc(Function *self) {
  _emval_decref(self->handle);
  if (self->bound != (EM_VAL)_EMVAL_UNDEFINED) {
    _emval_decref(self->bound);
  }
  Py_TYPE(self)->tp_free((PyObject *)self);
}

/**
 * Calls the object.
 */
static PyObject *
Function_call(Function *self, PyObject *args, PyObject *kwargs) {
  if (kwargs != NULL && PyDict_Size(kwargs) > 0) {
    PyErr_SetString(PyExc_TypeError, "__call__() takes no keyword arguments");
    return NULL;
  }

  EM_VAL result;

  // emval has no elegant call interface, so we add it ourselves.  Make more
  // optimal special cases for 0 and 1 args.
  int num_args = PyTuple_GET_SIZE(args);
  switch (num_args) {
  case 0:
    result = (EM_VAL)EM_ASM_INT({
      try {
        return Emval.toHandle(emval_handle_array[$0].value.call(emval_handle_array[$1].value));
      }
      catch (ex) {
        return -Emval.toHandle(ex);
      }}, self->handle, self->bound);
    break;

  case 1:
    {
      EM_VAL arg_handle = py_to_emval(PyTuple_GET_ITEM(args, 0));
      if (arg_handle == NULL) {
        return NULL;
      }
      result = (EM_VAL)EM_ASM_INT({
        try {
          return Emval.toHandle(emval_handle_array[$0].value.call(emval_handle_array[$1].value, emval_handle_array[$2].value));
        }
        catch (ex) {
          return -Emval.toHandle(ex);
        }
        finally {
          __emval_decref($2);
        }
      }, self->handle, self->bound, arg_handle);
    }
    break;

  default:
    {
      EM_VAL *arg_handles = (EM_VAL *)alloca(num_args * sizeof(EM_VAL));
      for (int i = 0; i < num_args; ++i) {
        EM_VAL handle = py_to_emval(PyTuple_GET_ITEM(args, i));
        if (handle == NULL) {
          while (--i >= 0) {
            _emval_decref(arg_handles[i]);
          }
          return NULL;
        }
        arg_handles[i] = handle;
      }

      result = (EM_VAL)EM_ASM_INT({
        var arg_handles = [];
        try {
          var arg_values = [];
          for (var i = 0; i < $2; ++i) {
            var arg_handle = getValue($3+i*4, 'i32');
            arg_handles.push(arg_handle);
            arg_values.push(emval_handle_array[arg_handle].value);
          }
          return Emval.toHandle(emval_handle_array[$0].value.apply(emval_handle_array[$1].value, arg_values));
        }
        catch (ex) {
          return -Emval.toHandle(ex);
        }
        finally {
          for (var i = 0; i < $2; ++i) {
            __emval_decref(arg_handles[i]);
          }
        }
      }, self->handle, self->bound, num_args, arg_handles);
    }
    break;
  }

  return emval_to_py(result);
}

/**
 * Subclass for functions.
 */
static PyTypeObject Function_Type = {
  PyVarObject_HEAD_INIT(NULL, 0)
  .tp_name = "browser.Function",
  .tp_doc = "JavaScript function",
  .tp_basicsize = sizeof(Function),
  .tp_itemsize = 0,
  .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
  .tp_dealloc = (destructor)Function_dealloc,
  .tp_call = (ternaryfunc)Function_call,
  .tp_base = &Object_Type,
};

/**
 * obj.description is the only property that Symbol exports.
 */
static PyObject *
Symbol_description(Symbol *self, void *unused) {
  char *str = (char *)EM_ASM_INT({
    var str = emval_handle_array[$0].value.description;
    var len = lengthBytesUTF8(str) + 1;
    var buffer = _malloc(len);
    stringToUTF8(str, buffer, len);
    return buffer;
  }, self->handle);

  PyObject *result = PyUnicode_FromString(str);
  free(str);
  return result;
}

static PyGetSetDef Symbol_getset[] = {
  { "description", (getter)Symbol_description, NULL, NULL, NULL },
  { NULL, NULL, NULL, NULL, NULL }
};

/**
 * Wraps around the JavaScript Symbol type.  Does not derive from Object, even
 * though it uses the same struct!
 */
static PyTypeObject Symbol_Type = {
  PyVarObject_HEAD_INIT(NULL, 0)
  .tp_name = "browser.Symbol",
  .tp_doc = "JavaScript symbol",
  .tp_basicsize = sizeof(Object),
  .tp_itemsize = 0,
  .tp_flags = Py_TPFLAGS_DEFAULT,
  .tp_dealloc = (destructor)Object_dealloc,
  .tp_repr = (reprfunc)Object_repr,
  .tp_hash = (hashfunc)Object_hash,
  .tp_str = (reprfunc)Object_str,
  .tp_richcompare = (richcmpfunc)Object_richcompare,
  .tp_getset = Symbol_getset,
  .tp_new = PyType_GenericNew,
};

/**
 * Calls a Python method from C.  Frees given argv pointer.
 */
EM_VAL EMSCRIPTEN_KEEPALIVE
_py_call(PyObject *func, PyObject *self, EM_VAL this_handle, int argc, EM_VAL *argv) {
  PyObject *args;
  if (self != NULL) {
    args = PyTuple_New(argc + 1);
    PyTuple_SET_ITEM(args, 0, self);
    Py_INCREF(self);
    for (int i = 0; i < argc; ++i) {
      PyTuple_SET_ITEM(args, i + 1, emval_to_py(argv[i]));
    }
  }
  else {
    args = PyTuple_New(argc);
    for (int i = 0; i < argc; ++i) {
      PyTuple_SET_ITEM(args, i, emval_to_py(argv[i]));
    }
  }
  free(argv);

  // Store the old "this" from the globals object.
  PyObject *globals = PyFunction_GET_GLOBALS(func);
  PyObject *old_this = PyDict_GetItemString(globals, "this");
  Py_XINCREF(old_this);

  // Replace it with the new one.
  PyObject *this = emval_to_py(this_handle);
  PyDict_SetItemString(globals, "this", this);
  Py_DECREF(this);

  PyObject *result = PyObject_Call(func, args, NULL);
  Py_DECREF(args);

  EM_VAL result_handle = (EM_VAL)_EMVAL_UNDEFINED;
  if (result == NULL) {
    PyErr_Print();
  }
  else {
    if (result != Py_None) {
      result_handle = py_to_emval(result);
    }
    Py_DECREF(result);
  }

  // Put back the old "this" object.
  if (old_this != NULL) {
    PyDict_SetItemString(globals, "this", old_this);
    Py_DECREF(old_this);
  }
  else {
    PyDict_DelItemString(globals, "this");
  }

  return result_handle;
}

/**
 * Unregisters the given callback with JavaScript.
 */
static PyObject *
py_callback_destructor(PyObject *handle, PyObject *weakref) {
  int id = PyLong_AsLong(handle);
  EM_ASM(__py_alive.delete($0), id);
  Py_DECREF(weakref);
  Py_INCREF(Py_None);
  return Py_None;
}

static PyMethodDef py_callback_destructor_def = {
  "__callback__", &py_callback_destructor, METH_O
};

/**
 * Returns the given Python object as emval.
 */
static EM_VAL py_to_emval(PyObject *val) {
  if (val == Py_None) {
    return (EM_VAL)_EMVAL_NULL;
  }
  else if (val == Py_True) {
    return (EM_VAL)_EMVAL_TRUE;
  }
  else if (val == Py_False) {
    return (EM_VAL)_EMVAL_FALSE;
  }
  else if (Py_TYPE(val) == &Object_Type ||
           Py_TYPE(val) == &Function_Type ||
           Py_TYPE(val) == &Symbol_Type) {
    EM_VAL handle = ((Object *)val)->handle;
    _emval_incref(handle);
    return handle;
  }
  else if (PyFloat_Check(val)) {
    return (EM_VAL)EM_ASM_INT(return Emval.toHandle($0), PyFloat_AsDouble(val));
  }
  else if (PyLong_Check(val)) {
    return (EM_VAL)EM_ASM_INT(return Emval.toHandle($0), PyLong_AsLong(val));
  }
  else if (PyUnicode_Check(val)) {
    return _emval_new_cstring(PyUnicode_AsUTF8(val));
  }
  else if (PyFunction_Check(val) || PyMethod_Check(val)) {
    PyObject *func = val;
    PyObject *self = NULL;
    if (PyMethod_Check(val)) {
      func = PyMethod_GET_FUNCTION(val);
      self = PyMethod_GET_SELF(val);
    }

    // Allocate a function ID, which we use to identify this this function, to
    // determine whether it is still alive in the Python interpreter.
    int callback_id = _next_callback_id++;
    PyObject *id_obj = PyLong_FromLong(callback_id);

    // Register a callback that gets invoked when either the "func" or "self"
    // objects go away, which marks them as no longer being alive.
    PyObject *callback = PyCFunction_New(&py_callback_destructor_def, id_obj);
    PyWeakref_NewRef(func, callback);
    if (self != NULL) {
      PyWeakref_NewRef(self, callback);
    }
    Py_DECREF(id_obj);
    Py_DECREF(callback);

    // Like in JS, extraneous arguments should be ignored, so we need to check how
    // many arguments this function actually takes.
    int max_args = -1;
    PyCodeObject *code = (PyCodeObject *)PyFunction_GET_CODE(func);
    if ((code->co_flags & CO_VARARGS) == 0) {
      max_args = code->co_argcount;
      if (self != NULL) {
        --max_args;
      }
    }

    return (EM_VAL)EM_ASM_INT({
      __py_alive.add($0);
      return Emval.toHandle(function() {
        if (__py_alive.has($0)) {
          var argc = arguments.length;
          if ($3 >= 0 && argc > $3) {
            argc = $3;
          }
          var argv = _malloc(argc * 4);
          for (var i = 0; i < argc; ++i) {
            setValue(argv+i*4, Emval.toHandle(arguments[i]), 'i32');
          }
          var result = __py_call($1, $2, Emval.toHandle(this), argc, argv);
          return emval_handle_array[result].value;
        }
      });
    }, callback_id, func, self, max_args);
  }
  else {
    return (EM_VAL)PyErr_Format(PyExc_TypeError,
                                "object of type '%002s' cannot be converted to JavaScript",
                                Py_TYPE(val)->tp_name);
  }
}

/**
 * And the other way around.  Steals a reference to handle.
 */
static PyObject *emval_to_py(EM_VAL handle) {
  if (handle == (EM_VAL)_EMVAL_TRUE) {
    Py_INCREF(Py_True);
    return Py_True;
  }
  if (handle == (EM_VAL)_EMVAL_FALSE) {
    Py_INCREF(Py_False);
    return Py_False;
  }
  if (handle == (EM_VAL)_EMVAL_UNDEFINED || handle == (EM_VAL)_EMVAL_NULL) {
    Py_INCREF(Py_None);
    return Py_None;
  }

  // We use a negative handle to raise an exception from JavaScript to Python.
  if ((int)handle < 0) {
    handle = (EM_VAL)-(int)handle;
    char message[512];
    message[0] = 0;

    // Extract the message and the exception type.
    int type = EM_ASM_INT({
      var exc = emval_handle_array[$0].value;
      try {
        if (exc.message) {
          stringToUTF8(exc.message, $1, 512);
        }
        if (exc instanceof TypeError) {
          return 1;
        }
        if (exc instanceof SyntaxError) {
          return 2;
        }
        return 0;
      }
      finally {
        __emval_decref($0);
      }
    }, handle, message);

    PyObject *exc_type;
    switch (type) {
    case 1:
      exc_type = PyExc_TypeError;
      break;

    case 2:
      exc_type = PyExc_SyntaxError;
      break;

    default:
      exc_type = PyExc_Exception;
      break;
    }

    PyErr_SetString(exc_type, message);
    return NULL;
  }

  // Get the type and value in one JS call.
  union {
    int _integer;
    double _number;
    char *_str;
  } target;

  int type = EM_ASM_INT(({
    var value = emval_handle_array[$0].value;
    var type = typeof value;
    if (type === "number") {
      // Check whether it fits in an int.
      if ((value | 0) === value) {
        setValue($1, value, "i32");
        __emval_decref($0);
        return 1;
      }
      else {
        setValue($1, value, "double");
        __emval_decref($0);
        return 2;
      }
    }
    else if (type === "string") {
      var len = lengthBytesUTF8(value) + 1;
      var buffer = _malloc(len);
      stringToUTF8(value, buffer, len);
      __emval_decref($0);
      setValue($1, buffer, "i32");
      return 3;
    }
    else if (type === "function") {
      return 4;
    }
    else if (type === "symbol") {
      return 5;
    }
    else { // object
      return 6;
    }
  }), handle, &target);

  switch (type) {
  case 1: // integer
    return PyLong_FromLong(target._integer);

  case 2: // number
    return PyFloat_FromDouble(target._number);

  case 3: // string
    {
      PyObject *result = PyUnicode_FromString(target._str);
      free(target._str);
      return result;
    }

  case 4: // function
    {
      Function *obj = PyObject_New(Function, &Function_Type);
      obj->handle = handle;
      obj->bound = (EM_VAL)_EMVAL_UNDEFINED;
      return (PyObject *)obj;
    }

  case 5: // symbol
    {
      Object *obj = PyObject_New(Object, &Symbol_Type);
      obj->handle = handle;
      return (PyObject *)obj;
    }

  default: // object
    {
      Object *obj = PyObject_New(Object, &Object_Type);
      obj->handle = handle;
      return (PyObject *)obj;
    }
  }
}

/**
 * Returns an arbitrary global.
 */
static PyObject *
browser_getattr(PyObject *self, PyObject *arg) {
  EM_VAL key_handle = py_to_emval(arg);
  if (key_handle == NULL) {
    return NULL;
  }
  EM_VAL result = (EM_VAL)EM_ASM_INT({
    try {
      return Emval.toHandle(window[emval_handle_array[$0].value]);
    }
    catch (ex) {
      return -Emval.toHandle(ex);
    }
    finally {
      __emval_decref($0);
    }
  }, key_handle);

  if (result == (EM_VAL)_EMVAL_UNDEFINED) {
    PyErr_SetObject(PyExc_AttributeError, arg);
    return NULL;
  }
  return emval_to_py(result);
}

/**
 * Opens an alert window to print the given message.
 */
static PyObject *
browser_alert(PyObject *self, PyObject *arg) {
  const char *message = PyUnicode_AsUTF8(arg);
  if (message != NULL) {
    EM_ASM(alert(UTF8ToString($0)), message);
    Py_INCREF(Py_None);
    return Py_None;
  }
  return NULL;
}

/**
 * Opens an yes/no confirmation box, returning True or False.
 */
static PyObject *
browser_confirm(PyObject *self, PyObject *arg) {
  const char *message = PyUnicode_AsUTF8(arg);
  if (message != NULL) {
    int result = EM_ASM_INT({
      return confirm(UTF8ToString($0));
    }, message);
    return PyBool_FromLong(result);
  }
  return NULL;
}

/**
 * Opens a prompt box.
 */
static PyObject *
browser_prompt(PyObject *self, PyObject *args) {
  char *message;
  char *default_value = NULL;
  if (PyArg_ParseTuple(args, "s|s", &message, &default_value)) {
    char *str = (char *)EM_ASM_INT({
      var str = prompt(UTF8ToString($0), $1 ? UTF8ToString($1) : undefined);
      if (str === null) {
        return 0;
      }
      var len = lengthBytesUTF8(str) + 1;
      var buffer = _malloc(len);
      stringToUTF8(str, buffer, len);
      return buffer;
    }, message, default_value);

    PyObject *result;
    if (str != NULL) {
      result = PyUnicode_FromString(str);
      free(str);
    }
    else {
      result = Py_None;
      Py_INCREF(result);
    }
    return result;
  }
  return NULL;
}

static PyMethodDef browser_functions[] = {
  { "__getattr__", &browser_getattr, METH_O },
  { "alert", &browser_alert, METH_O },
  { "confirm", &browser_confirm, METH_O },
  { "prompt", &browser_prompt, METH_VARARGS },
  { NULL, NULL }
};

static struct PyModuleDef browser_module = {
  PyModuleDef_HEAD_INIT,
  "browser",
  NULL,
  -1,
  browser_functions,
  NULL, NULL, NULL, NULL
};

#ifdef _WIN32
extern __declspec(dllexport) PyObject *PyInit_browser();
#elif __GNUC__ >= 4
extern __attribute__((visibility("default"))) PyObject *PyInit_browser();
#else
extern PyObject *PyInit_browser();
#endif

PyObject *PyInit_browser() {

  if (PyType_Ready(&PromiseWrapper_Type) < 0) {
    return NULL;
  }
  if (PyType_Ready(&Object_Type) < 0) {
    return NULL;
  }
  if (PyType_Ready(&Function_Type) < 0) {
    return NULL;
  }
  if (PyType_Ready(&Symbol_Type) < 0) {
    return NULL;
  }

  PyObject *module = PyModule_Create(&browser_module);
  if (module == NULL) {
    return NULL;
  }

  Object *window = PyObject_New(Object, &Object_Type);
  if (PyModule_AddObject(module, "window", (PyObject *)window) < 0) {
    Py_DECREF(&window);
    Py_DECREF(module);
    return NULL;
  }

  Object *console = PyObject_New(Object, &Object_Type);
  if (PyModule_AddObject(module, "console", (PyObject *)console) < 0) {
    Py_DECREF(&console);
    Py_DECREF(module);
    return NULL;
  }

  Object *document = PyObject_New(Object, &Object_Type);
  if (PyModule_AddObject(module, "document", (PyObject *)document) < 0) {
    Py_DECREF(&document);
    Py_DECREF(module);
    return NULL;
  }

  EM_ASM({

    setValue($0, Emval.toHandle(window), "i32");
    setValue($1, Emval.toHandle(console), "i32");
    setValue($2, Emval.toHandle(document), "i32");

    window.__py_alive = new Set();
  }, &window->handle, &console->handle, &document->handle);

  return module;
}
