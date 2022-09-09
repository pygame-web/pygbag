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


headless tests ?

    https://github.com/paulrouget/servo-embedding-example

    https://chromium.googlesource.com/chromium/src/+/lkgr/headless/README.md


webserver ?
    https://github.com/humphd/nohost


ZIP_LZMA ?
    https://github.com/jvilk/BrowserFS/blob/master/src/backend/ZipFS.ts

self hosting:
    https://github.com/jprendes/emception

*/


#if __EMSCRIPTEN__
    #define EMIFACE
    #include <emscripten/html5.h>
    #include <emscripten/key_codes.h>
    #include "emscripten.h"
    #include <SDL2/SDL.h>
    #include <SDL2/SDL_ttf.h>
//    #include <SDL_hints.h> // SDL_HINT_EMSCRIPTEN_KEYBOARD_ELEMENT
    #define SDL_HINT_EMSCRIPTEN_KEYBOARD_ELEMENT   "SDL_EMSCRIPTEN_KEYBOARD_ELEMENT"

    #define HOST_RETURN(value)  return value

#if defined(EMIFACE)
    PyObject *sysmod;
    PyObject *sysdict;

    #include "__EMSCRIPTEN__.embed/emscriptenmodule.c"
    #include "__EMSCRIPTEN__.embed/browsermodule.c"
    #include "__EMSCRIPTEN__.embed/sysmodule.c"
#endif

#else
    #error "wasi unsupported yet"
#endif

#include <unistd.h>

extern void pygame_Inittab();

#if defined(PY_HARFANG3D)
    extern PyMODINIT_FUNC PyInit_harfang(void);
#endif

static long long embed = 0;

static PyObject *
embed_run(PyObject *self, PyObject *argv,  PyObject *kwds)
{
    if (!embed)
        embed++;
    return Py_BuildValue("L", embed);
}

static PyObject *
embed_counter(PyObject *self, PyObject *argv,  PyObject *kwds)
{
    return Py_BuildValue("L", embed);
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
    SDL_version v;

    SDL_GetVersion(&v);
    TTF_Init();
    return Py_BuildValue("iii", v.major, v.minor, v.patch);

}

void
embed_preload_cb_onload(const char *fn) {
    //fprintf(stderr, __FILE__": preloaded [%s] ok\n", fn );
    remove(fn);
    embed ++ ;
  //  if (embed<0)
     //   fprintf(stderr, "INFO: %lli assets remaining in queue\n", -embed );
}

void
embed_preload_cb_onerror(const char *fn) {
    fprintf(stderr, __FILE__": preload [%s] ERROR\n", "" );
}

// TODO: use PyUnicode_FSConverter()
static int embed_preload_assets_count = 0;
static PyObject *
embed_preload(PyObject *self, PyObject *argv) {
    char *url=NULL;
    char *parent = NULL;
    char *name = NULL;
    if (!PyArg_ParseTuple(argv, "s|ss", &url, &parent, &name)) {
        return NULL;
    }
    embed -- ;

    emscripten_run_preload_plugins(
        url, (em_str_callback_func)embed_preload_cb_onload, (em_str_callback_func)embed_preload_cb_onerror
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
embed_coroutine(PyObject *self, PyObject *argv) {
    char *code = NULL;
    if (!PyArg_ParseTuple(argv, "s", &code)) {
        return NULL;
    }
    return Py_BuildValue("i", emscripten_run_script_int(code) );
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
embed_readline(PyObject *self, PyObject *_null); //forward

static PyObject *
embed_flush(PyObject *self, PyObject *_null) {
    fprintf( stdout, "%c", 4);
    fprintf( stderr, "%c", 4);
    Py_RETURN_NONE;
}

static PyObject *
embed_prompt(PyObject *self, PyObject *_null) {
    fprintf( stderr, ">>> ");
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


static PyObject *
embed_get_sdl_version(PyObject *self, PyObject *_null)
{
    SDL_version v;

    SDL_GetVersion(&v);
    return Py_BuildValue("iii", v.major, v.minor, v.patch);
}


static PyMethodDef mod_embed_methods[] = {
    {"run", (PyCFunction)embed_run, METH_VARARGS | METH_KEYWORDS, "start aio stepping"},
    {"dlopen", (PyCFunction)embed_dlopen, METH_VARARGS | METH_KEYWORDS, ""},
    {"dlcall", (PyCFunction)embed_dlcall, METH_VARARGS | METH_KEYWORDS, ""},
    {"counter", (PyCFunction)embed_counter, METH_VARARGS | METH_KEYWORDS, "read aio loop pass counter"},
    {"test", (PyCFunction)embed_test, METH_VARARGS | METH_KEYWORDS, "test"},
    {"preload", (PyCFunction)embed_preload,  METH_VARARGS, "emscripten_run_preload_plugins"},
    {"symlink", (PyCFunction)embed_symlink,  METH_VARARGS, "FS.symlink"},
    {"run_script", (PyCFunction)embed_run_script,  METH_VARARGS, "run js"},
    {"coroutine", (PyCFunction)embed_coroutine,  METH_VARARGS, "run js coro"},
    {"eval", (PyCFunction)embed_eval,  METH_VARARGS, "run js eval()"},
    {"readline", (PyCFunction)embed_readline,  METH_NOARGS, "get current line"},
    {"flush", (PyCFunction)embed_flush,  METH_NOARGS, "flush stdio+stderr"},
    {"prompt", (PyCFunction)embed_prompt,  METH_NOARGS, "output >>> "},
    {"isatty", (PyCFunction)embed_isatty,  METH_VARARGS, "isatty(int fd)"},
    {"get_sdl_version", embed_get_sdl_version, METH_NOARGS, "get_sdl_version"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef mod_embed = {
    PyModuleDef_HEAD_INIT,
    "embed",
    NULL,
    -1,
    mod_embed_methods
};

static PyObject *embed_dict;

PyMODINIT_FUNC init_embed(void) {

#if defined(EMIFACE)
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
#endif

    PyObject *embed_mod = PyModule_Create(&mod_embed);
    embed_dict = PyModule_GetDict(embed_mod);
    PyDict_SetItemString(embed_dict, "js2py", PyUnicode_FromString("{}"));
    return embed_mod;


}


struct timeval time_last, time_current, time_lapse;

// "files"

#define FD_MAX 64
#define FD_BUFFER_MAX 2048


FILE *io_fd[FD_MAX];
char *io_shm[FD_MAX];
int io_stdin_filenum;
int wa_panic = 0;

#define LOG_V puts
#define wa_break { wa_panic=1;goto panic; }
#define stdin_cstr io_shm[io_stdin_filenum]

/*
    io_shm is a raw keyboard buffer
    io_fd is the readline/file/socket interface
*/
static PyObject *
embed_readline(PyObject *self, PyObject *_null) {
    return Py_BuildValue("s", io_shm[io_stdin_filenum] );
}

em_callback_func
main_iteration(void) {


    if (!wa_panic) {

        // first pass coming back from js
        // if anything js was planned from main() it should be done by now.
        if (embed && embed++) {
            // run a frame.
            PyRun_SimpleString("aio.step()");
        }

// REPL + PyRun_SimpleString asked from wasm vm host .

        gettimeofday(&time_current, NULL);
        timersub(&time_current, &time_last, &time_lapse);

//TODO put a user-def value to get slow func
        if (time_lapse.tv_usec>1) {

            gettimeofday(&time_last, NULL);

            if ( stdin_cstr[0] ) {

#define file io_fd[0]
                int silent = 0;

                if ( stdin_cstr[0] == '#' ) {
                    silent = (stdin_cstr[1] == '!') ;
                    // special message display it on console
                    if (!silent)
                        puts(stdin_cstr);
                }

// TODO: only redirect keyboard buffer to fd if \n found.
// and implement getch for raw mode.

                fprintf( file ,"%s", stdin_cstr );

                if ( !fseek(file, 0L, SEEK_END) ) {
                    if ( ftell(file) ) {
                        rewind(file);
                    }
                }

                int line = 0;
                char buf[FD_BUFFER_MAX];

                while( fgets(&buf[0], FD_BUFFER_MAX, file) ) {
                    line++;
                    //fprintf( stderr, "%d: %s", line, buf );
                }

                rewind(file);


                if (line>1) {
                    line=0;
                    while( fgets(&buf[0], FD_BUFFER_MAX, file) ) {
                        line++;
                        if (!silent)
                            fprintf( stderr, "%d: %s", line, buf );
                    }
                    rewind(file);
                    PyRun_SimpleFile( file, "<stdin>");
                } else {
                    line = 0;
                    while( !PyRun_InteractiveOne( file, "<stdin>") ) line++;
                }

                if (line) {
                    fprintf( stdout, "%c", 4);
                    if (!silent)
                        fprintf( stderr, ">>> %c", 4);
                }

                // reset stdin
                stdin_cstr[0] = 0;
                stdin_cstr[1] = 0;
                rewind(file);
                // ? no op ?
                ftruncate(io_stdin_filenum, 0);

            }

        // TODO: raw mode auto flush

        }
    } else {

//panic:
        pymain_free();
        emscripten_cancel_main_loop();
        puts(" ---------- done ----------");
    }
    HOST_RETURN(0);
}

#undef file
#undef stdin_cstr

PyStatus status;

/*
EM_BOOL
on_keyboard_event(int type, const EmscriptenKeyboardEvent *event, void *user_data) {
    puts("canvas keyboard event");
    return false;
}

SDL_Window *window;
SDL_Renderer *renderer;

*/


int
main(int argc, char **argv)
{
    gettimeofday(&time_last, NULL);
    //LOG_V("---------- SDL2 on #canvas + pygame ---------");

    _PyArgv args = {
        .argc = argc,
        .use_bytes_argv = 1,
        .bytes_argv = argv,
        .wchar_argv = NULL
    };


#if defined(EMIFACE)
    PyImport_AppendInittab("embed_emscripten", PyInit_emscripten);
    PyImport_AppendInittab("embed_browser", PyInit_browser);
#endif
#if defined(PY_HARFANG3D)
    PyImport_AppendInittab("harfang", PyInit_harfang);
#endif

    PyImport_AppendInittab("embed", init_embed);

    pygame_Inittab();
    setenv("LC_ALL", "C.UTF-8", 1);
    setenv("TERM","xterm", 1);
    setenv("TERMINFO", "/usr/share/terminfo", 1);
    setenv("COLS","132", 1);
    setenv("LINES","30", 1);
    setenv("NCURSES_NO_UTF8_ACS","1",1);

    setenv("LANG","en_US.UTF-8", 0);

    setenv("PYTHONHOME","/usr", 1);
    setenv("PYTHONUNBUFFERED", "1", 1);
    setenv("PYTHONINSPECT","1",1);
    setenv("PYTHONDONTWRITEBYTECODE","1",1);

    setenv("HOME", "/home/web_user", 1);
    setenv("APPDATA", "/home/web_user", 1);

    status = pymain_init(&args);

    if (_PyStatus_IS_EXIT(status)) {
        pymain_free();
        return status.exitcode;
    }

    if (_PyStatus_EXCEPTION(status)) {
        puts(" ---------- pymain_exit_error ----------");
        Py_ExitStatusException(status);
        pymain_free();
        return 1;
    }

    chdir("/");

    if (!mkdir("dev", 0700)) {
       LOG_V("no 'dev' directory, creating one ...");
    }

    if (!mkdir("dev/fd", 0700)) {
       LOG_V("no 'dev/fd' directory, creating one ...");
    }

/* ????
>>> ls /proc/self/fd
[Errno 54] Not a directory: '/proc/self/fd'
>>> cat /proc/self/fd
[Errno 31] Is a directory
>>> cd /proc/self/fd
[  /proc/self/fd  ]
>>> ls
[Errno 54] Not a directory: '.'

    if (!mkdir("proc", 0700)) {
       LOG_V("no 'proc' directory, creating one ...");
    }
    if (!mkdir("proc/self", 0700)) {
       LOG_V("no 'proc/self' directory, creating one ...");
    }
    if (!mkdir("proc/self/fd", 0700)) {
       LOG_V("no 'proc/self/fd' directory, creating one ...");
    }
*/
    if (!mkdir("tmp", 0700)) {
       LOG_V("no 'tmp' directory, creating one ...");
    }


    io_fd[0] = fopen("dev/fd/0", "w+" );
    io_stdin_filenum = fileno(io_fd[0]);
// FD LEAK!
    io_shm[io_stdin_filenum] =  (char *) malloc(FD_BUFFER_MAX);

    for (int i=0;i<FD_BUFFER_MAX;i++)
        io_shm[io_stdin_filenum][i]=0;


//TODO: check if shm is cleared ?
// https://stackoverflow.com/questions/7507638/any-standard-mechanism-for-detecting-if-a-javascript-is-executing-as-a-webworker
// https://stackoverflow.com/questions/7931182/reliably-detect-if-the-script-is-executing-in-a-web-worker

EM_ASM({
    var shm_stdin = $0;
    Module.printErr = Module.print;
    const is_worker = (typeof WorkerGlobalScope !== 'undefined') && self instanceof WorkerGlobalScope;

    function jswasm_load(script, aio) {
        if (!aio) aio=false;
        const jswasmloader=document.createElement("script");
        jswasmloader.setAttribute("type","text/javascript");
        jswasmloader.setAttribute("src", script);
        jswasmloader.setAttribute('async', aio);
        document.getElementsByTagName("head")[0].appendChild(jswasmloader);
    };

    if (is_worker) {
        console.log("PyMain: running in a worker, setting onCustomMessage");
        function onCustomMessage(event) {
            stringToUTF8( utf8encode(data), shm_stdin, $1);
        };

        Module['onCustomMessage'] = onCustomMessage;

    } else {
        console.log("PyMain: running in main thread");
        Module.postMessage = function custom_postMessage(data) {
            stringToUTF8( data, shm_stdin, $1);
        };
        window.main_chook = true;
    }

    if (!is_worker && window.BrowserFS) {
        console.log("PyMain: found BrowserFS");
        //if (is_worker)
        //    jswasm_load("fshandler.js");

    } else {
        console.error("PyMain: BrowserFS not found");
    }
    if (0) {
        SYSCALLS.getStreamFromFD(0).tty = true;
        SYSCALLS.getStreamFromFD(1).tty = true;
        SYSCALLS.getStreamFromFD(2).tty = true;
    }
}, io_shm[io_stdin_filenum], FD_BUFFER_MAX);


    PyRun_SimpleString("import sys, os, json, builtins, shutil, time;");

    #if 1
        // display a nice six logo python-powered in xterm.js
        #define MAX 132
        char buf[MAX];
        FILE *six = fopen("/data/data/org.python/assets/cpython.six","r");
        while (six) {
            fgets(buf, MAX, six);
            if (!buf[0]) {
                fclose(six);
                puts("");
                break;
            }
            fputs(buf, stdout);
            buf[0]=0;
        }

    #else
        // same but with python
        // repl banner
        PyRun_SimpleString("print(open('/data/data/org.python/assets/cpython.six').read());");
    #endif

    PyRun_SimpleString("print('CPython',sys.version, '\\n', file=sys.stderr);");

    embed_flush(NULL,NULL);

    // SDL2 basic init
    {
        //SDL_Init(SDL_INIT_EVERYTHING); //SDL_INIT_VIDEO | SDL_INIT_TIMER);

        if (TTF_Init())
            fprintf(stderr, "ERROR: TTF_Init error");

        const char *target = "1";
        SDL_SetHint(SDL_HINT_EMSCRIPTEN_KEYBOARD_ELEMENT, target);

/*
        note for self : typical sdl2 init ( emscripten samples are sdl1 )
        SDL_CreateWindow("default", SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED, 800, 600, 0);
        window = SDL_CreateWindow("CheckKeys Test",
                                  SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
                                  800, 600, 0);
        renderer = SDL_CreateRenderer(window, -1, 0);
        SDL_RenderPresent(renderer);

        emscripten_set_keypress_callback_on_thread(target, NULL, false, &on_keyboard_event, NULL);
        emscripten_set_keypress_callback(target, NULL, false, &on_keyboard_event);
*/
    }

    emscripten_set_main_loop( (em_callback_func)main_iteration, 0, 1);
    return 0;
}
