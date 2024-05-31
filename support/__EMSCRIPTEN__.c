/*
// from python-main.c
static PyStatus pymain_init(const _PyArgv *args);
static void pymain_free(void);


    http://troubles.md/why-do-we-need-the-relooper-algorithm-again/

    https://medium.com/leaningtech/solving-the-structured-control-flow-problem-once-and-for-all-5123117b1ee2

    https://github.com/WebAssembly/exception-handling

    https://github.com/WebAssembly/design/issues/796

tty ?
https://github.com/emscripten-core/emscripten/blob/6dc4ac5f9e4d8484e273e4dcc554f809738cedd6/src/library_syscall.js#L311
    finish ncurses : https://github.com/jamesbiv/ncurses-emscripten


headless tests ?

    playwright
        https://playwright.dev/docs/screenshots
        https://stackoverflow.com/questions/73267809/run-playwright-in-interactive-mode-in-python

    https://github.com/paulrouget/servo-embedding-example

    https://chromium.googlesource.com/chromium/src/+/lkgr/headless/README.md


webserver ?
    https://github.com/humphd/nohost


ZIP_LZMA ?
    https://github.com/jvilk/BrowserFS/blob/master/src/backend/ZipFS.ts

self hosting:
    https://github.com/jprendes/emception

debug:
    https://developer.chrome.com/blog/wasm-debugging-2020/


*/


#include <unistd.h>


static int preloads = 0;
static long long loops = 0;


struct timeval time_last, time_current, time_lapse;

// crude "files" used for implementing "os level" communications with host.


#define FD_MAX 64
#define FD_BUFFER_MAX 4096

FILE *io_file[FD_MAX];
char *io_shm[FD_MAX];
int io_stdin_filenum;
int io_raw_filenum;
int io_rcon_filenum;

int wa_panic = 0;

#define wa_break { wa_panic=1;goto panic; }


#define IO_RAW 3
#define IO_RCON 4

/*
    io_shm is a raw keyboard buffer
    io_file is the readline/file/socket interface
*/
static int embed_readline_bufsize = 0;
static int embed_readline_cursor = 0;

static int embed_os_read_bufsize = 0;
static int embed_os_read_cursor = 0;


char buf[FD_BUFFER_MAX];

// TODO: store input frame counter + timestamps for all I/O
// for ascii app record/replay.

#if defined(INC_TEST)
#define xstr(s) str(s)
#define str(s) #s
#define INC_TEST_FILE xstr(INC_TEST)
#define MAIN_TEST_FILE xstr(MAIN_TEST)
#include INC_TEST_FILE
#endif


#if defined(WAPY)
#   include "Python.h"
#endif

// ==============================================================================================

#if defined(PKPY)
#   include "Python.h"
#else
#   include "../build/gen_static.h"


// ==============================================================================================



#if PYDK_emsdk
#   include <emscripten/html5.h>
#   include <emscripten/key_codes.h>
#   include "emscripten.h"
#   define HOST_RETURN(value)  return value

    PyObject *sysmod;
    PyObject *sysdict;

#   include "sys/time.h"  // gettimeofday
#   include <sys/stat.h>  // umask

#   if !defined(WAPY)
#       include "__EMSCRIPTEN__.embed/sysmodule.c"
#   endif
#else
#   error "wasi unsupported yet"
#endif

#if !defined(WAPY)
#   include "../build/gen_inittab.h"
#else
#   pragma message  "  @@@@@@@@@@@ NOT YET ../build/gen_inittab.h @@@@@@@@@@@@"
#endif

#if defined(PYDK_static_hpy)
// ===== HPY =======

#define HPY_ABI_UNIVERSAL
#include "hpy.h"

HPyDef_METH(platform_run, "run", HPyFunc_VARARGS)

static HPy
platform_run_impl(HPyContext *ctx, HPy self, const HPy *argv, size_t argc) {
    puts("hpy runs");
    return HPyLong_FromLongLong(ctx, loops);
}

static HPyDef *hpy_platform_Methods[] = {
    &platform_run,
    NULL,
};

static HPyModuleDef hpy_platform_def = {
    .doc = "HPy _platform",
    .defines = hpy_platform_Methods,
};

// The Python interpreter will create the module for us from the
// HPyModuleDef specification. Additional initialization can be
// done in the HPy_mod_exec slot
HPy_MODINIT(_platform, hpy_platform_def)

extern PyModuleDef* _HPyModuleDef_AsPyInit(HPyModuleDef *hpydef);

PyMODINIT_FUNC
PyInit__platform(void)
{
    return (PyObject *)_HPyModuleDef_AsPyInit(&hpy_platform_def);
}
#endif // hpy

#endif // !PKPY




// ==============================================================================================


static PyObject *
embed_run(PyObject *self, PyObject *argv,  PyObject *kwds)
{
    //if (preloads>0)
      //  fprintf(stderr, "INFO: %i assets remaining in queue\n", preloads );

    if (!preloads) {
        // start async looping
        loops++;
    }

    return Py_BuildValue("L", loops);
}

static PyObject *
embed_counter(PyObject *self, PyObject *argv,  PyObject *kwds)
{
    return Py_BuildValue("L", loops);
}

static PyObject *
embed_preloading(PyObject *self, PyObject *argv,  PyObject *kwds)
{
    return Py_BuildValue("i", preloads);
}


#include <dlfcn.h>
static void *handle;
static PyObject *
embed_dlopen(PyObject *self, PyObject *argv,  PyObject *kwds)
{
    char * dlo = NULL;
    if (!PyArg_ParseTuple(argv, "s", &dlo)) {
        return NULL;

    }
    handle = dlopen (dlo, RTLD_NOW);


    Py_RETURN_NONE;
}

static PyObject *
embed_dlcall(PyObject *self, PyObject *argv,  PyObject *kwds)
{
    char * sym = NULL;
    char * data = NULL;

    if (!PyArg_ParseTuple(argv, "ss", &sym, &data)) {
        return NULL;
    }
    void (*func)(char *);

    func = dlsym(handle, sym);

    func(data);

    Py_RETURN_NONE;
}

static PyObject *
embed_test(PyObject *self, PyObject *args, PyObject *kwds)
{
    puts("test function : return 1");
    return Py_BuildValue("i", 1);
}

#include <emscripten/html5.h>
#include <GLES2/gl2.h>

static PyObject *embed_webgl(PyObject *self, PyObject *args, PyObject *kwds);


void
embed_preload_cb_onload(const char *fn) {
    preloads -- ;
    //if (preloads>0)
      //  fprintf(stderr, "INFO: %i assets remaining in queue\n", preloads );
}

void
embed_preload_cb_onerror(const char *fn) {
    fprintf(stderr, __FILE__": preload [%s] ERROR\n", fn );
    // do not block asyncio for a missing preload.
    preloads--;
}

// TODO: use PyUnicode_FSConverter()
static PyObject *
embed_preload(PyObject *self, PyObject *argv) {
    char *url=NULL;
    char *parent = NULL;
    char *name = NULL;
    if (!PyArg_ParseTuple(argv, "s|ss", &url, &parent, &name)) {
        return NULL;
    }
    preloads ++ ;

    emscripten_run_preload_plugins(
        url,
        (em_str_callback_func)embed_preload_cb_onload,
        (em_str_callback_func)embed_preload_cb_onerror
    );
    Py_RETURN_NONE;
}


static PyObject *
embed_symlink(PyObject *self, PyObject *argv) {
    char *src = NULL;
    char *dst = NULL;

    if (!PyArg_ParseTuple(argv, "ss", &src, &dst)) {
        return NULL;
    }
    EM_ASM({
        FS.symlink( UTF8ToString($0), UTF8ToString($1));
    }, src,dst );
    Py_RETURN_NONE;
}

static PyObject *
embed_run_script(PyObject *self, PyObject *argv) {
    char *code = NULL;
    int delay = 0;

    if (!PyArg_ParseTuple(argv, "s|i", &code, &delay)) {
        return NULL;
    }

    if (delay) {
        emscripten_async_run_script(code, delay);
        Py_RETURN_NONE;
    }

    return Py_BuildValue("s", emscripten_run_script_string(code) );
}

static PyObject *
embed_eval(PyObject *self, PyObject *argv) {
    char *code = NULL;
    if (!PyArg_ParseTuple(argv, "s", &code)) {
        return NULL;
    }
    EM_ASM({ eval(UTF8ToString($0)); }, code);
    Py_RETURN_NONE;
}

static PyObject *
embed_warn(PyObject *self, PyObject *argv) {
    char *code = NULL;
    if (!PyArg_ParseTuple(argv, "s", &code)) {
        return NULL;
    }
    EM_ASM({ console.warn(UTF8ToString($0)); }, code);
    Py_RETURN_NONE;
}

static PyObject *
embed_error(PyObject *self, PyObject *argv) {
    char *code = NULL;
    if (!PyArg_ParseTuple(argv, "s", &code)) {
        return NULL;
    }
    EM_ASM({ console.error(UTF8ToString($0)); }, code);
    Py_RETURN_NONE;
}

static PyObject *
embed_readline(PyObject *self, PyObject *_null); //forward

static PyObject *
embed_os_read(PyObject *self, PyObject *_null); //forward

static PyObject *
embed_stdin_select(PyObject *self, PyObject *_null); // forward

static PyObject *
embed_flush(PyObject *self, PyObject *_null) {
    fprintf( stdout, "%c", 4);
    fprintf( stderr, "%c", 4);
    Py_RETURN_NONE;
}

static int sys_ps = 1;

static PyObject *
embed_set_ps1(PyObject *self, PyObject *_null) {
    sys_ps = 1;
    Py_RETURN_NONE;
}

static PyObject *
embed_set_ps2(PyObject *self, PyObject *_null) {
    sys_ps = 2;
    Py_RETURN_NONE;
}

static PyObject *
embed_prompt(PyObject *self, PyObject *_null) {
    if (sys_ps==1)
        fprintf( stderr, ">>> ");
    else
        fprintf( stderr, "... ");
    embed_flush(self,_null);
    Py_RETURN_NONE;
}

static PyObject *
embed_isatty(PyObject *self, PyObject *argv) {
    int fd = 0;
    if (!PyArg_ParseTuple(argv, "i", &fd)) {
        return NULL;
    }
    return Py_BuildValue("i", isatty(fd) );
}

/*
static PyObject *
embed_PyErr_Clear(PyObject *self, PyObject *_null) {
    PyErr_Clear();
    Py_RETURN_NONE;
}
*/

#if TEST_ASYNCSLEEP

#include "pycore_ceval.h"
#include "pycore_function.h"
#include "pycore_pystate.h"       // _PyInterpreterState_GET()
#include "pycore_frame.h"

static void
_PyEvalFrameClearAndPop(PyThreadState *tstate, _PyInterpreterFrame * frame)
{
    // Make sure that this is, indeed, the top frame. We can't check this in
    // _PyThreadState_PopFrame, since f_code is already cleared at that point:
    assert((PyObject **)frame + frame->f_code->co_nlocalsplus +
        frame->f_code->co_stacksize + FRAME_SPECIALS_SIZE == tstate->datastack_top);
    tstate->recursion_remaining--;
    assert(frame->frame_obj == NULL || frame->frame_obj->f_frame == frame);
    assert(frame->owner == FRAME_OWNED_BY_THREAD);
    _PyFrame_Clear(frame);
    tstate->recursion_remaining++;
    _PyThreadState_PopFrame(tstate, frame);
}

extern PyObject *WASM_PyEval_EvalFrameDefault(PyThreadState *tstate, _PyInterpreterFrame *frame, int throwflag);

static PyObject *
embed_bcrun(PyObject *self, PyObject *argv) {
    PyThreadState *tstate = _PyThreadState_GET();
    PyObject *globals = NULL;
    PyObject *locals = NULL;

#if 0
    const char *bc = NULL;
    if (!PyArg_ParseTuple(argv, "y", &bc)) {
#else
    PyObject *co = NULL;
    if (!PyArg_ParseTuple(argv, "OO", &co, &globals)) {

#endif
        return NULL;
    }

    PyObject *builtins = _PyEval_BuiltinsFromGlobals(tstate, globals); // borrowed ref
    if (builtins == NULL) {
        return NULL;
    }


    locals = globals;

    puts("got bc");
    /*
    PyObject* local_dict = PyDict_New();
    PyObject* obj = PyEval_EvalCode(co, globals , globals);
*/
    PyFrameConstructor desc = {
        .fc_globals = globals,
        .fc_builtins = builtins,
        .fc_name = ((PyCodeObject *)co)->co_name,
        .fc_qualname = ((PyCodeObject *)co)->co_name,
        .fc_code = co,
        .fc_defaults = NULL,
        .fc_kwdefaults = NULL,
        .fc_closure = NULL
    };
    PyFunctionObject *func = _PyFunction_FromConstructor(&desc);
    if (func == NULL) {
        return NULL;
    }
    PyObject* const* args = NULL;
    size_t argcount = 0;
    PyObject *kwnames = NULL;

    //PyObject *res = _PyEval_Vector(tstate, func, locals, NULL, 0, NULL);
    /* _PyEvalFramePushAndInit consumes the references
     * to func and all its arguments */
    Py_INCREF(func);
    for (size_t i = 0; i < argcount; i++) {
        Py_INCREF(args[i]);
    }
    if (kwnames) {
        Py_ssize_t kwcount = PyTuple_GET_SIZE(kwnames);
        for (Py_ssize_t i = 0; i < kwcount; i++) {
            Py_INCREF(args[i+argcount]);
        }
    }
/*
    _PyInterpreterFrame *frame = _PyEvalFramePushAndInit(
        tstate, func, locals, args, argcount, kwnames);
*/

    PyCodeObject * code = (PyCodeObject *)func->func_code;
    size_t size = code->co_nlocalsplus + code->co_stacksize + FRAME_SPECIALS_SIZE;
    CALL_STAT_INC(frames_pushed);
    _PyInterpreterFrame *frame = _PyThreadState_BumpFramePointer(tstate, size);
    if (frame == NULL) {
        goto fail;
    }
    _PyFrame_InitializeSpecials(frame, func, locals, code->co_nlocalsplus);
    PyObject **localsarray = &frame->localsplus[0];
    for (int i = 0; i < code->co_nlocalsplus; i++) {
        localsarray[i] = NULL;
    }
    /*
    if (initialize_locals(tstate, func, localsarray, args, argcount, kwnames)) {
        assert(frame->owner != FRAME_OWNED_BY_GENERATOR);
        _PyEvalFrameClearAndPop(tstate, frame);
    }
    */
    goto skip;

fail:
    /* Consume the references */
    for (size_t i = 0; i < argcount; i++) {
        Py_DECREF(args[i]);
    }
    if (kwnames) {
        Py_ssize_t kwcount = PyTuple_GET_SIZE(kwnames);
        for (Py_ssize_t i = 0; i < kwcount; i++) {
            Py_DECREF(args[i+argcount]);
        }
    }
    PyErr_NoMemory();

skip:

// _PyEvalFramePushAndInit
    if (frame == NULL) {
        return NULL;
    }

    int throwflag = 0;
/*
    PyObject *retval = _PyEval_EvalFrame(tstate, frame, 0);
    _PyEval_EvalFrameDefault(PyThreadState *tstate, _PyInterpreterFrame *frame, int throwflag)
*/

    //PyObject *retval = _PyEval_EvalFrameDefault(tstate, frame, throwflag);
puts("479");
    PyObject *retval = WASM_PyEval_EvalFrameDefault(tstate, frame, throwflag);
puts("481");

    assert(
        _PyFrame_GetStackPointer(frame) == _PyFrame_Stackbase(frame) ||
        _PyFrame_GetStackPointer(frame) == frame->localsplus
    );

    _PyEvalFrameClearAndPop(tstate, frame);
    Py_DECREF(func);
//_PyEval_Vector

    puts("done");
    Py_RETURN_NONE;
}
#endif // TEST_ASYNCSLEEP

#if SDL2
static PyObject *
embed_get_sdl_version(PyObject *self, PyObject *_null)
{
    SDL_version v;

    SDL_GetVersion(&v);
    return Py_BuildValue("iii", v.major, v.minor, v.patch);
}
#endif



static PyMethodDef mod_embed_methods[] = {
    {"run", (PyCFunction)embed_run, METH_VARARGS | METH_KEYWORDS, "start aio stepping"},
#if TEST_ASYNCSLEEP
    {"bcrun", (PyCFunction)embed_bcrun, METH_VARARGS, ""},
#endif
    //{"PyErr_Clear", (PyCFunction)embed_PyErr_Clear, METH_NOARGS, ""},
    {"preload", (PyCFunction)embed_preload,  METH_VARARGS, "emscripten_run_preload_plugins"},
    {"dlopen", (PyCFunction)embed_dlopen, METH_VARARGS | METH_KEYWORDS, ""},
    {"dlcall", (PyCFunction)embed_dlcall, METH_VARARGS | METH_KEYWORDS, ""},

    {"counter", (PyCFunction)embed_counter, METH_VARARGS | METH_KEYWORDS, "read aio loop pass counter"},
    {"preloading", (PyCFunction)embed_preloading, METH_VARARGS | METH_KEYWORDS, "read preloading counter"},

    {"symlink", (PyCFunction)embed_symlink,  METH_VARARGS, "FS.symlink"},
    {"run_script", (PyCFunction)embed_run_script,  METH_VARARGS, "run js"},

    {"eval", (PyCFunction)embed_eval,  METH_VARARGS, "run js eval()"},
    // log goes with unimplemented RT functions
    {"warn", (PyCFunction)embed_warn,  METH_VARARGS, "console.warn()"},
    {"error", (PyCFunction)embed_error,  METH_VARARGS, "console.error()"},

    {"readline", (PyCFunction)embed_readline,  METH_NOARGS, "get current line"},
    {"os_read",  (PyCFunction)embed_os_read,  METH_NOARGS, "get current raw stdin"},
    {"stdin_select", (PyCFunction)embed_stdin_select,  METH_NOARGS, "get current raw stdin bytes length"},

    {"flush", (PyCFunction)embed_flush,  METH_NOARGS, "flush stdio+stderr"},

    {"set_ps1", (PyCFunction)embed_set_ps1,  METH_NOARGS, "set prompt output to >>> "},
    {"set_ps2", (PyCFunction)embed_set_ps2,  METH_NOARGS, "set prompt output to ... "},
    {"prompt", (PyCFunction)embed_prompt,  METH_NOARGS, "output the prompt"},

    {"isatty", (PyCFunction)embed_isatty,  METH_VARARGS, "isatty(int fd)"},
#if SDL2
    {"get_sdl_version", embed_get_sdl_version, METH_NOARGS, "get_sdl_version"},
#endif
    {"test", (PyCFunction)embed_test, METH_VARARGS | METH_KEYWORDS, "test"},

    {"webgl", (PyCFunction)embed_webgl, METH_VARARGS | METH_KEYWORDS, "open a canvas as webgl"},

    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef mod_embed = {
    PyModuleDef_HEAD_INIT,
    "embed",
    NULL,
    -1,
    mod_embed_methods,
    NULL, // m_slots
    NULL, // m_traverse
    NULL, // m_clear
    NULL, // m_free
};

static PyObject *embed_dict;

PyMODINIT_FUNC
PyInit_embed(void) {

// activate javascript bindings that were moved from libpython to pymain.
// but not for wapy
#if defined(PYDK_emsdk) && !defined(WAPY)
    int res;
    sysmod = PyImport_ImportModule("sys"); // must call Py_DECREF when finished
    sysdict = PyModule_GetDict(sysmod); // borrowed ref, no need to delete

    if (EmscriptenInfoType == NULL) {
        EmscriptenInfoType = PyStructSequence_NewType(&emscripten_info_desc);
        if (EmscriptenInfoType == NULL) {
            goto type_init_failed;
        }
    }
    SET_SYS("_emscripten_info", make_emscripten_info());
    Py_DECREF(sysmod); // release ref to sysMod
err_occurred:;
type_init_failed:;
#else

        puts("PyInit_embed");
#endif

// helper module for pygbag api not well defined and need clean up.
// callable as "platform" module.
    PyObject *embed_mod = PyModule_Create(&mod_embed);

// from old aiolink poc
    //embed_dict = PyModule_GetDict(embed_mod);
    //PyDict_SetItemString(embed_dict, "js2py", PyUnicode_FromString("{}"));

    return embed_mod;

}


static PyObject *
embed_readline(PyObject *self, PyObject *_null) {
#define file io_file[0]

    //global char buf[FD_BUFFER_MAX];
    buf[0]=0;

    fseek(file, embed_readline_cursor, SEEK_SET);
    fgets(&buf[0], FD_BUFFER_MAX, file);

    embed_readline_cursor += strlen(buf);

    if ( embed_readline_cursor && (embed_readline_cursor == embed_readline_bufsize) ) {
        rewind(file);
        ftruncate(fileno(file), 0);
        embed_readline_cursor = 0;
        embed_readline_bufsize = ftell(file);
    }
    return Py_BuildValue("s", buf );
#undef file
}


static PyObject *
embed_os_read(PyObject *self, PyObject *_null) {
#define file io_file[IO_RAW]
    //global char buf[FD_BUFFER_MAX];
    buf[0]=0;

    fseek(file, embed_os_read_cursor, SEEK_SET);
    fgets(&buf[0], FD_BUFFER_MAX, file);

    embed_os_read_cursor += strlen(buf);

    if ( embed_os_read_cursor && (embed_os_read_cursor == embed_os_read_bufsize) ) {
        rewind(file);
        ftruncate(fileno(file), 0);
        embed_os_read_cursor = 0;
        embed_os_read_bufsize = ftell(file);
    }
    return Py_BuildValue("y", buf );
#undef file
}

static PyObject *
embed_stdin_select(PyObject *self, PyObject *_null) {
    return Py_BuildValue("i", embed_os_read_bufsize );
}



int io_file_select(int fdnum) {
    int datalen = strlen( io_shm[fdnum] );

    if (datalen) {
#       define file io_file[fdnum]
        fwrite(io_shm[fdnum], 1, datalen, file);

        if (fdnum == IO_RCON) {
            rewind(file);
            ftruncate(fileno(file), datalen);
        } else {
            // readline or getc may not consume data each loop
        }
#       undef file
        io_shm[fdnum][0] = 0;
        io_shm[fdnum][1] = 0;
    }
    return datalen;
}


em_callback_func
main_iteration(void) {

    // fill stdin file with raw keyboard buffer
    int datalen= 0;
    int lines = 0;

    //int silent = 1;
    int silent = 0;

    if ( (datalen =  io_file_select(IO_RCON)) ) {
#       define file io_file[IO_RCON]
        // global char buf[FD_BUFFER_MAX];
        while( fgets(&buf[0], FD_BUFFER_MAX, file) ) {
            if (!lines && (strlen(buf)>1)){
                silent = ( buf[0] == '#' ) && (buf[1] == '!');
            }
            lines++;
            if (!silent)
                fprintf( stderr, "%d: %s", lines, buf );
        }

        rewind(file);

        if (lines>1)  {
            PyRun_SimpleFile( file, "<stdin>");
        } else {
            lines = 0;
            while( !PyRun_InteractiveOne( file, "<stdin>") ) lines++;
        }

        rewind(file);

#       undef file
    }

    if ( (datalen = io_file_select(IO_RAW)) ) {
        embed_os_read_bufsize += datalen;
        //printf("raw data %i\n", datalen);
    }

    if ( (datalen = io_file_select(0)) ) {
        embed_readline_bufsize += datalen;
        //printf("stdin data q+%i / q=%i dq=%i\n", datalen, embed_readline_bufsize, embed_readline_cursor);
    }

    // first pass coming back from js
    // if anything js was planned from main() it should be done by now.
    if (!preloads && loops) {
        // run a frame.
        PyRun_SimpleString("aio.step()");
        loops++;
    }
    HOST_RETURN(0);
}


static void reprint(const char *fmt, PyObject *obj) {
    PyObject* repr = PyObject_Repr(obj);
    PyObject* str = PyUnicode_AsEncodedString(repr, "utf-8", "~E~");
    const char *bytes = PyBytes_AS_STRING(str);
    printf("REPR(%s): %s\n", fmt, bytes);
    Py_XDECREF(repr);
    Py_XDECREF(str);
}




#define EGLTEST



#if defined(EGLTEST)
    #include <GLES2/gl2.h>
    #include <EGL/egl.h>

    // #include <SDL2/SDL_egl.h>

// for GL
    #include <SDL2/SDL.h>


EMSCRIPTEN_KEEPALIVE EGLBoolean
egl_ChooseConfig (EGLDisplay dpy, const EGLint *attrib_list, EGLConfig *configs, EGLint config_size, EGLint *num_config) {
    return eglChooseConfig(dpy, attrib_list, configs, config_size, num_config);
}

EMSCRIPTEN_KEEPALIVE EGLDisplay
egl_GetCurrentDisplay (void) {
    return eglGetCurrentDisplay();
}


EMSCRIPTEN_KEEPALIVE void egl_test() {
    EGLContext context = NULL;
    EGLSurface surface = NULL;
    EGLDisplay display = NULL;
    EGLNativeWindowType dummyWindow = 0;
    EGLConfig config;


#if 0

    display = eglGetDisplay(EGL_DEFAULT_DISPLAY);
    assert(display != EGL_NO_DISPLAY);
    assert(eglGetError() == EGL_SUCCESS);

    EGLint major = 2, minor = 0;
    EGLBoolean ret = eglInitialize(display, &major, &minor);
    assert(eglGetError() == EGL_SUCCESS);
    assert(ret == EGL_TRUE);
    assert(major * 10000 + minor >= 10004);

    EGLint numConfigs;
    ret = eglGetConfigs(display, NULL, 0, &numConfigs);
    assert(eglGetError() == EGL_SUCCESS);
    assert(ret == EGL_TRUE);

    EGLint attribs[] = {
        /*
        EGL_RED_SIZE, 5,
        EGL_GREEN_SIZE, 6,
        EGL_BLUE_SIZE, 5,
        */
        EGL_CONTEXT_CLIENT_VERSION, 2,
        EGL_NONE,
        EGL_NONE
    };

    ret = egl_ChooseConfig(display, attribs, &config, 0, &numConfigs);
    assert(eglGetError() == EGL_SUCCESS);
    assert(ret == EGL_TRUE);

    dummyWindow = 0;

    surface = eglCreateWindowSurface(display, config, dummyWindow, NULL);
    if ( surface == EGL_NO_SURFACE ){
        puts("EGL_NO_SURFACE");
    }

    EGLint width, height;
    eglQuerySurface(display, surface, EGL_WIDTH, &width);
    eglQuerySurface(display, surface, EGL_HEIGHT, &height);
    printf("(%d, %d)\n", width, height);

    // Create a GL context

    context = eglCreateContext(display, config, EGL_NO_CONTEXT, attribs );

    surface = eglCreateWindowSurface(display, config, dummyWindow, NULL);
    if ( surface == EGL_NO_SURFACE ){
        puts("EGL_NO_SURFACE");
    }

    // Make the context current
    if ( !eglMakeCurrent(display, surface, surface, context) ) {
        puts("!eglMakeCurrent");
        //goto fail;
    }

#else
    EmscriptenWebGLContextAttributes attr;
    emscripten_webgl_init_context_attributes(&attr);
    attr.alpha = 0;
    EMSCRIPTEN_WEBGL_CONTEXT_HANDLE ctx = emscripten_webgl_create_context("#canvas3d", &attr);
    emscripten_webgl_make_context_current(ctx);

    context = (EGLContext)emscripten_webgl_get_current_context();

    display = eglGetDisplay(EGL_DEFAULT_DISPLAY);
    assert(display != EGL_NO_DISPLAY);
    assert(eglGetError() == EGL_SUCCESS);

#endif


    if ( context == EGL_NO_CONTEXT ) {
        puts("EGL_NO_CONTEXT");
    } else {
        puts("EGL_CONTEXT");
    }

    puts("EGL test complete");

    puts(glGetString(GL_VERSION));

    return;

fail:
    puts("EGL test failed");
}

#endif // EGLTEST

static PyObject *
embed_webgl(PyObject *self, PyObject *argv, PyObject *kw)
{

    EMSCRIPTEN_WEBGL_CONTEXT_HANDLE ctx ;
    EGLContext context = NULL;
    EGLSurface surface = NULL;
    EGLDisplay display = NULL;
    EGLNativeWindowType dummyWindow = 0;
    EGLConfig config;

    char * target = NULL;
    if (!PyArg_ParseTuple(argv, "|s", &target)) {
        target = NULL;
    }
    EmscriptenWebGLContextAttributes attr;
    emscripten_webgl_init_context_attributes(&attr);
    attr.alpha = 0;
    if (target) {
        ctx = emscripten_webgl_create_context(target, &attr);
        setenv("WebGL", target, 1);
    } else {
        ctx = emscripten_webgl_create_context("#canvas", &attr);
    }

    emscripten_webgl_make_context_current(ctx);

    context = (EGLContext)emscripten_webgl_get_current_context();

    display = eglGetDisplay(EGL_DEFAULT_DISPLAY);
    puts(glGetString(GL_VERSION));

    return Py_BuildValue("i", emscripten_webgl_get_current_context() );
}

PyStatus status;

#if defined(WAPY) || defined(PKPY)
#define CPY 0

__attribute__((noinline)) int
main_(int argc, char **argv)

#else
#define CPY 1
int
main(int argc, char **argv)
#endif
{
    gettimeofday(&time_last, NULL);
    PyImport_AppendInittab("embed", PyInit_embed);

// wip hpy
#if defined(PYDK_static_hpy)
    PyImport_AppendInittab("_platform", PyInit__platform);
#endif

#   include "../build/gen_inittab.c"

// defaults
    setenv("LC_ALL", "C.UTF-8", 0);
    setenv("TERMINFO", "/usr/share/terminfo", 0);
    setenv("COLUMNS","132", 0);
    setenv("LINES","30", 0);
    setenv("PYGBAG","1", 1);

//    setenv("PYTHONINTMAXSTRDIGITS", "0", 0);
    setenv("LANG", "en_US.UTF-8", 0);

    setenv("TERM", "xterm", 0);
    setenv("NCURSES_NO_UTF8_ACS", "1", 0);
    setenv("MPLBACKEND", "Agg", 0);

// force
    setenv("PYTHONHOME","/usr", 1);
    setenv("PYTHONUNBUFFERED", "1", 1);
    setenv("PYTHONINSPECT","1",1);
    setenv("PYTHONDONTWRITEBYTECODE","1",1);
    setenv("HOME", "/home/web_user", 1);
    setenv("APPDATA", "/home/web_user", 1);

    setenv("PYGLET_HEADLESS", "1", 1);
    setenv("ELECTRIC_TELEMETRY","disabled", 1);
    setenv("PSYCOPG_WAIT_FUNC", "wait_select", 1);


    status = pymain_init(NULL);

    if (PyErr_Occurred()) {
        puts(" ---------- pymain_exit_error ----------");
        Py_ExitStatusException(status);
        pymain_free();
        return 1;
    }

    umask(18); // 0022

    chdir("/");

    if (!mkdir("dev", 0700)) {
       puts("no 'dev' directory, creating one ...");
    }

    if (!mkdir("dev/fd", 0700)) {
       //puts("no 'dev/fd' directory, creating one ...");
    }

    if (!mkdir("tmp", 0700)) {
       puts("no 'tmp' directory, creating one ...");
    }

    for (int i=0;i<FD_MAX;i++)
        io_shm[i]= NULL;

    io_file[0] = fopen("dev/fd/0", "w+" );
    io_stdin_filenum = fileno(io_file[0]);

    io_file[IO_RAW] = fopen("dev/cons", "w+" );
    io_raw_filenum = fileno(io_file[IO_RAW]);

    io_file[IO_RCON] = fopen("dev/rcon", "w+" );
    io_rcon_filenum = fileno(io_file[IO_RCON]);

    io_shm[0] = memset(malloc(FD_BUFFER_MAX) , 0, FD_BUFFER_MAX);
    io_shm[IO_RAW] = memset(malloc(FD_BUFFER_MAX) , 0, FD_BUFFER_MAX);
    io_shm[IO_RCON] = memset(malloc(FD_BUFFER_MAX) , 0, FD_BUFFER_MAX);

    #include MAIN_TEST_FILE


EM_ASM({
    globalThis.FD_BUFFER_MAX = $0;
    globalThis.shm_stdin = $1;
    globalThis.shm_rawinput = $2;
    globalThis.shm_rcon = $3;

    Module.printErr = Module.print;
    globalThis.is_worker = (typeof WorkerGlobalScope !== 'undefined') && self instanceof WorkerGlobalScope;

    function jswasm_load(script, aio) {
        if (!aio) aio=false;
        const jswasmloader=document.createElement("script");
        jswasmloader.setAttribute("type","text/javascript");
        jswasmloader.setAttribute("src", script);
        jswasmloader.setAttribute("async", aio);
        document.getElementsByTagName("head")[0].appendChild(jswasmloader);
    };

    if (is_worker) {
        console.log("PyMain: running in a worker, setting onCustomMessage");
        function onCustomMessage(event) {
            console.log("onCustomMessage:", event);
            stringToUTF8( utf8encode(data), shm_rcon, $0);
        };

        Module['onCustomMessage'] = onCustomMessage;

    } else {
        console.log("PyMain: running in main thread, faking onCustomMessage");
        Module.postMessage = function custom_postMessage(event) {
            switch (event.type) {
                case "raw" :  {
                    stringToUTF8( event.data, shm_rawinput, FD_BUFFER_MAX);
                    break;
                }

                case "stdin" :  {
                    stringToUTF8( event.data, shm_stdin, FD_BUFFER_MAX);
                    break;
                }
                case "rcon" :  {
                    stringToUTF8( event.data, shm_rcon, FD_BUFFER_MAX);
                    break;
                }
                default : console.warn("custom_postMessage?", event);
            }
        };

    }

    if (!is_worker) {
        if (typeof window === 'undefined') {
            if (FS)
                console.warn("PyMain: Running in Node ?");
            else
                console.error("PyMain: not Node");
        } else {
            if (window.BrowserFS) {
                console.log("PyMain: found BrowserFS");
                //if (is_worker)
                //    jswasm_load("fshandler.js");
            } else {
                console.error("PyMain: BrowserFS not found");
            }
        }
    }


}, FD_BUFFER_MAX, io_shm[0], io_shm[IO_RAW], io_shm[IO_RCON]);

    PyRun_SimpleString("import sys, os, json, builtins, time");
    PyRun_SimpleString("sys.ps1 = ''");

    //PyRun_SimpleString("import hpy;import hpy.universal;print('HPy init done')");
#if defined(FT)
    int error;

    FT_Library library;
    error = FT_Init_FreeType(&library);
    if (error) {
        printf("FT error %d\n", error);
    } else {
        puts(" @@@@@@@@@@@@@@@@@@@@@ FT OK @@@@@@@@@@@@@@@@@@@@");
    }
#endif

#if SDL2
    // SDL2 basic init
    {
        if (TTF_Init())
            fprintf(stderr, "ERROR: TTF_Init error");

        const char *target = "1";
        SDL_SetHint(SDL_HINT_EMSCRIPTEN_KEYBOARD_ELEMENT, target);
    }
#endif


#if ASYNCIFIED
    clock_t start = clock()+100;
    while (1) {
        main_iteration();
        clock_t current = clock();
        if (current > start) {
            start = current+100;
            emscripten_sleep(1);
        }
    }
#else
    emscripten_set_main_loop( (em_callback_func)main_iteration, 0, 1);
#endif
    puts("\nEnd");
    return 0;
}

#if defined(WAPY)
int main(int argc, char **argv) {
     #if MICROPY_PY_THREAD
    mp_thread_init();
    #endif
    // We should capture stack top ASAP after start, and it should be
    // captured guaranteedly before any other stack variables are allocated.
    // For this, actual main (renamed main_) should not be inlined into
    // this function. main_() itself may have other functions inlined (with
    // their own stack variables), that's why we need this main/main_ split.
    mp_stack_ctrl_init();
    return main_(argc, argv);
}
#endif // WAPY

#if defined(PKPY)
int main(int argc, char **argv) {
    pkpy_init()    return main_(argc, argv);
}
#endif


















