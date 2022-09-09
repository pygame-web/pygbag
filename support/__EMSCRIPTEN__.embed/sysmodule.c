/* Updating the sys namespace, returning NULL pointer on error */
#define SET_SYS(key, value)                                \
    do {                                                   \
        PyObject *v = (value);                             \
        if (v == NULL) {                                   \
            goto err_occurred;                             \
        }                                                  \
        res = PyDict_SetItemString(sysdict, key, v);   \
        Py_DECREF(v);                                      \
        if (res < 0) {                                     \
            goto err_occurred;                             \
        }                                                  \
    } while (0)

#define SET_SYS_FROM_STRING(key, value) \
        SET_SYS(key, PyUnicode_FromString(value))


#if 2695

PyDoc_STRVAR(emscripten_info__doc__,
"sys._emscripten_info\n\
\n\
WebAssembly Emscripten platform information.");

static PyTypeObject *EmscriptenInfoType;

static PyStructSequence_Field emscripten_info_fields[] = {
    {"emscripten_version", "Emscripten version (major, minor, micro)"},
    {"runtime", "Runtime (Node.JS version, browser user agent)"},
    {"pthreads", "pthread support"},
    {"shared_memory", "shared memory support"},
    {0}
};

static PyStructSequence_Desc emscripten_info_desc = {
    "sys._emscripten_info",     /* name */
    emscripten_info__doc__ ,    /* doc */
    emscripten_info_fields,     /* fields */
    4
};

EM_JS(char *, _Py_emscripten_runtime, (void), {
    var info;
    if (typeof navigator == 'object') {
        info = navigator.userAgent;
    } else if (typeof process == 'object') {
        info = "Node.js ".concat(process.version)
    } else {
        info = "UNKNOWN"
    }
    var len = lengthBytesUTF8(info) + 1;
    var res = _malloc(len);
    stringToUTF8(info, res, len);
    return res;
});

static PyObject *
make_emscripten_info(void)
{
    PyObject *emscripten_info = NULL;
    PyObject *version = NULL;
    char *ua;
    int pos = 0;

    emscripten_info = PyStructSequence_New(EmscriptenInfoType);
    if (emscripten_info == NULL) {
        return NULL;
    }

    version = Py_BuildValue("(iii)",
        __EMSCRIPTEN_major__, __EMSCRIPTEN_minor__, __EMSCRIPTEN_tiny__);
    if (version == NULL) {
        goto error;
    }
    PyStructSequence_SET_ITEM(emscripten_info, pos++, version);

    ua = _Py_emscripten_runtime();
    if (ua != NULL) {
        PyObject *oua = PyUnicode_DecodeUTF8(ua, strlen(ua), "strict");
        free(ua);
        if (oua == NULL) {
            goto error;
        }
        PyStructSequence_SET_ITEM(emscripten_info, pos++, oua);
    } else {
        Py_INCREF(Py_None);
        PyStructSequence_SET_ITEM(emscripten_info, pos++, Py_None);
    }

#define SetBoolItem(flag) \
    PyStructSequence_SET_ITEM(emscripten_info, pos++, PyBool_FromLong(flag))

#ifdef __EMSCRIPTEN_PTHREADS__
    SetBoolItem(1);
#else
    SetBoolItem(0);
#endif

#ifdef __EMSCRIPTEN_SHARED_MEMORY__
    SetBoolItem(1);
#else
    SetBoolItem(0);
#endif

#undef SetBoolItem

    if (PyErr_Occurred()) {
        goto error;
    }
    return emscripten_info;

  error:
    Py_CLEAR(emscripten_info);
    return NULL;
}

#endif // __EMSCRIPTEN__
//2794


