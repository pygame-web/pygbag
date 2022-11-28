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

*/


#include <unistd.h>


#if PYDK_emsdk
    #include <emscripten/html5.h>
    #include <emscripten/key_codes.h>
    #include "emscripten.h"
    #include <SDL2/SDL.h>
    #include <SDL2/SDL_ttf.h>
//    #include <SDL_hints.h> // SDL_HINT_EMSCRIPTEN_KEYBOARD_ELEMENT
    #define SDL_HINT_EMSCRIPTEN_KEYBOARD_ELEMENT   "SDL_EMSCRIPTEN_KEYBOARD_ELEMENT"

    #define HOST_RETURN(value)  return value

    PyObject *sysmod;
    PyObject *sysdict;
#   include "__EMSCRIPTEN__.embed/sysmodule.c"


#else
    #error "wasi unsupported yet"
#endif

#include "../build/gen_inittab.h"


static int preloads = 0;
static long long loops = 0;

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
static PyObject *
embed_webgl(PyObject *self, PyObject *args, PyObject *kwds)
{
    	// setting up EmscriptenWebGLContextAttributes
	EmscriptenWebGLContextAttributes attr;
	emscripten_webgl_init_context_attributes(&attr);
	attr.alpha = 0;

	// target the canvas selector
	EMSCRIPTEN_WEBGL_CONTEXT_HANDLE ctx = emscripten_webgl_create_context("#canvas", &attr);
	emscripten_webgl_make_context_current(ctx);
    glClearColor(0.984, 0.4627, 0.502, 1.0);
	glClear(GL_COLOR_BUFFER_BIT);
    return Py_BuildValue("i", emscripten_webgl_get_current_context() );
}

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
embed_readline(PyObject *self, PyObject *_null); //forward

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


static PyObject *
embed_get_sdl_version(PyObject *self, PyObject *_null)
{
    SDL_version v;

    SDL_GetVersion(&v);
    return Py_BuildValue("iii", v.major, v.minor, v.patch);
}


static PyMethodDef mod_embed_methods[] = {
    {"run", (PyCFunction)embed_run, METH_VARARGS | METH_KEYWORDS, "start aio stepping"},

    {"preload", (PyCFunction)embed_preload,  METH_VARARGS, "emscripten_run_preload_plugins"},
    {"dlopen", (PyCFunction)embed_dlopen, METH_VARARGS | METH_KEYWORDS, ""},
    {"dlcall", (PyCFunction)embed_dlcall, METH_VARARGS | METH_KEYWORDS, ""},

    {"counter", (PyCFunction)embed_counter, METH_VARARGS | METH_KEYWORDS, "read aio loop pass counter"},
    {"preloading", (PyCFunction)embed_preloading, METH_VARARGS | METH_KEYWORDS, "read preloading counter"},

    {"symlink", (PyCFunction)embed_symlink,  METH_VARARGS, "FS.symlink"},
    {"run_script", (PyCFunction)embed_run_script,  METH_VARARGS, "run js"},
    {"eval", (PyCFunction)embed_eval,  METH_VARARGS, "run js eval()"},
    {"readline", (PyCFunction)embed_readline,  METH_NOARGS, "get current line"},
    {"flush", (PyCFunction)embed_flush,  METH_NOARGS, "flush stdio+stderr"},

    {"set_ps1", (PyCFunction)embed_set_ps1,  METH_NOARGS, "set prompt output to >>> "},
    {"set_ps2", (PyCFunction)embed_set_ps2,  METH_NOARGS, "set prompt output to ... "},
    {"prompt", (PyCFunction)embed_prompt,  METH_NOARGS, "output the prompt"},

    {"isatty", (PyCFunction)embed_isatty,  METH_VARARGS, "isatty(int fd)"},

    {"get_sdl_version", embed_get_sdl_version, METH_NOARGS, "get_sdl_version"},

    {"test", (PyCFunction)embed_test, METH_VARARGS | METH_KEYWORDS, "test"},

    {"webgl", (PyCFunction)embed_webgl, METH_VARARGS | METH_KEYWORDS, "test"},

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

#if defined(PYDK_emsdk)
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

FILE *io_file[FD_MAX];
char *io_shm[FD_MAX];
int io_stdin_filenum;
int io_raw_filenum;
int io_rcon_filenum;

int wa_panic = 0;

#define LOG_V puts
#define wa_break { wa_panic=1;goto panic; }


#define IO_RAW 3
#define IO_RCON 4

/*
    io_shm is a raw keyboard buffer
    io_file is the readline/file/socket interface
*/
static int embed_readline_bufsize = 0;
static int embed_readline_cursor = 0;

static PyObject *
embed_readline(PyObject *self, PyObject *_null) {
#   define file io_file[0]
    char buf[FD_BUFFER_MAX];
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
#   undef file
    return Py_BuildValue("s", buf );
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
        char buf[FD_BUFFER_MAX];
        while( fgets(&buf[0], FD_BUFFER_MAX, file) ) {
            if (!lines && (strlen(buf)>1)){
                silent = ( buf[0] == '#' ) && (buf[1] == '!');
            }
            lines++;
            if (!silent)
                fprintf( stderr, "%d: %s", lines, buf );
        }

        //printf("rcon data %i lines=%i\n", datalen, lines);

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

    if ( (datalen =  io_file_select(IO_RAW)) )
        printf("raw data %i\n", datalen);

    if ( (datalen =  io_file_select(0)) ) {
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


PyStatus status;

int
main(int argc, char **argv)
{
    gettimeofday(&time_last, NULL);

    _PyArgv args = {
        .argc = argc,
        .use_bytes_argv = 1,
        .bytes_argv = argv,
        .wchar_argv = NULL
    };


    PyImport_AppendInittab("embed", init_embed);

#   include "../build/gen_inittab.c"

// defaults
    setenv("LC_ALL", "C.UTF-8", 0);
    setenv("TERMINFO", "/usr/share/terminfo", 0);
    setenv("COLS","132", 0);
    setenv("LINES","30", 0);
    setenv("TERM", "xterm", 0);
    setenv("NCURSES_NO_UTF8_ACS", "1", 0);
    setenv("PYTHONINTMAXSTRDIGITS", "0", 0);
    setenv("LANG", "en_US.UTF-8", 0);

// force
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

    umask(18); // 0022

    chdir("/");

    if (!mkdir("dev", 0700)) {
       LOG_V("no 'dev' directory, creating one ...");
    }

    if (!mkdir("dev/fd", 0700)) {
       //LOG_V("no 'dev/fd' directory, creating one ...");
    }

    if (!mkdir("tmp", 0700)) {
       LOG_V("no 'tmp' directory, creating one ...");
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


EM_ASM({
    const shm_stdin = $1;
    const shm_rawinput = $2;
    const shm_rcon = $3;

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
            console.log("onCustomMessage:", event);
            stringToUTF8( utf8encode(data), shm_rcon, $0);
        };

        Module['onCustomMessage'] = onCustomMessage;

    } else {
        console.log("PyMain: running in main thread");
        Module.postMessage = function custom_postMessage(event) {
            switch (event.type) {
                case "raw" :  {
                    stringToUTF8( event.data, shm_rawinput, $0);
                    break;
                }

                case "stdin" :  {
                    stringToUTF8( event.data, shm_stdin, $0);
                    break;
                }
                case "rcon" :  {
                    stringToUTF8( event.data, shm_rcon, $0);
                    break;
                }
                default : console.warn("custom_postMessage?", event);
            }
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
    if (1) {
        SYSCALLS.getStreamFromFD(0).tty = true;
        SYSCALLS.getStreamFromFD(1).tty = true;
        SYSCALLS.getStreamFromFD(2).tty = true;
    }
}, FD_BUFFER_MAX, io_shm[0], io_shm[IO_RAW], io_shm[IO_RCON]);


    PyRun_SimpleString("import sys, os, json, builtins, shutil, time;");

/*
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

    //embed_flush(NULL,NULL);
*/


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
