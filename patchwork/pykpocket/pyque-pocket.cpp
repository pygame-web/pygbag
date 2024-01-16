#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "sys/time.h"
#include <sys/stat.h>

#define __PKPY__ 1

#include "pygbag.h"

#include "pocketpy.h"

using namespace pkpy;

/*

    https://github.com/jggatc/pyjsdl/tree/master/pyjsdl

    https://github.com/renpy/pygame_sdl2

*/

VM *vm;

extern "C"
{

#if !defined(__EMSCRIPTEN__)
  bool em_running = true;
#endif

#define CPY 0

#define FD_MAX 64
#define FD_BUFFER_MAX 4096

#define IO_RAW 3
#define IO_RCON 4

  /*
      io_file is the readline/raw/file/socket interface
      io_shm is a buffer list for host->guest transfer
  */

  FILE *io_file[FD_MAX];
  char *io_shm[FD_MAX];
  int io_stdin_filenum;
  int io_raw_filenum;
  int io_rcon_filenum;

  static int embed_readline_bufsize = 0;
  static int embed_readline_cursor = 0;

  static int embed_os_read_bufsize = 0;
  static int embed_os_read_cursor = 0;

// TODO: use ring buffer for multi-io at once
#define IO_MAX FD_BUFFER_MAX * 10

  // to avoid malloc when emptying io_file
  char buf[IO_MAX];

  int
  PyRun_SimpleString (const char *command)
  {
    vm->exec (command);
    return 0;
  }

  int
  PyRun_SimpleFile (FILE *fp, const char *filename)
  {
    fseek (fp, 0, SEEK_END);
    size_t size = ftell (fp);
    if (size > sizeof (buf))
      {
        printf ("Buffer overlow in PyRun_SimpleFile %zu>%lu", size,
                sizeof (buf));
        size = sizeof (buf);
      }
    buf[0] = 0;
    rewind (fp);
    if (fread (&buf[0], size, 1, fp))
      vm->exec (buf);
    else
      puts ("PyRun_SimpleFile: read error");
    return 1;
  }

#define PyRun_InteractiveOne(fp, fn) PyRun_SimpleFile (fp, fn)
#define Py(...) PyRun_SimpleString (fmt (__VA_ARGS__).c_str ())
#define CSTR(str) (const char *)str

  void
  makedir (const char *d)
  {
    if (!mkdir (d, 0700))
      {
        // printf()
      }
  }

  // Python "API"

#include <stdarg.h>

  int
  PyArg_ParseTuple (PyObject *argv, const char *fmt, ...)
  {
    va_list argptr;
    va_start (argptr, fmt);
    vfprintf (stdout, fmt, argptr);
    va_end (argptr);
    return 0;
  }

  PyObject *
  Py_BuildValue (const char *format, ...)
  {
    va_list argptr;
    va_start (argptr, format);
    PyObject *retval = NULL;

    int argc = strlen (format);
    if (argc > 1)
      {
        printf ("Py_BuildValue(multi: %s) N/I", format);
      }
    else
      {

        for (int i = 0; i < argc; i++)
          {
            switch (format[i])
              {
              case 's':
                {
                  retval = py_var (vm, (const char *)va_arg (argptr, char *));
                  break;
                }
              case 'y':
                {
                  std::string_view sv = va_arg (argptr, char *);
                  retval = py_var (vm, Bytes (sv));
                  break;
                }

              case 'i':
                {
                  retval = py_var (vm, va_arg (argptr, int));
                  break;
                }
              default:
                printf ("Py_BuildValue(%c) N/I", format[i]);
                vfprintf (stdout, format, argptr);
              }
          }
      }
    va_end (argptr);
    return retval;
  }

  // ============== PYGBAG "API" ================

  int
  io_file_select (int fdnum)
  {
    int datalen = strlen (io_shm[fdnum]);

    if (datalen)
      {
#define file io_file[fdnum]
        if (fdnum == IO_RCON)
          {
            fwrite (io_shm[fdnum], datalen, 1, file);

            // readline or getc may not consume data each loop, rcon does
            rewind (file);
            ftruncate (fileno (file), datalen);
          }
        else
          {
            if ((ftell (file) + datalen) >= FD_BUFFER_MAX)
              {
                // data has not been gathered, need emergency vaccuum
                printf ("ERROR: buffer overrun in IO channel %d, resetting.\n",
                        fdnum);
                rewind (file);
                ftruncate (fileno (file), 0);
              }
            fwrite (io_shm[fdnum], datalen, 1, file);
          }
        io_shm[fdnum][0] = 0;
#undef file
      }
    return datalen;
  }

  static PyObject *
  embed_readline (PyObject *self, PyObject *_null)
  {
#define file io_file[0]
    // global char buf[IO_MAX];
    buf[0] = 0;

    fseek (file, embed_readline_cursor, SEEK_SET);
    fgets (&buf[0], IO_MAX, file);

    embed_readline_cursor += strlen (buf);

    if (embed_readline_cursor
        && (embed_readline_cursor == embed_readline_bufsize))
      {
        rewind (file);
        ftruncate (fileno (file), 0);
        embed_readline_cursor = 0;
        embed_readline_bufsize = ftell (file);
      }
    // printf("embed_readline[%s]\n", (char*)&buf);
    return Py_BuildValue ("s", &buf);
#undef file
  }

  static PyObject *
  embed_stdin_select (PyObject *self, PyObject *_null)
  {
    return Py_BuildValue ("i", (int)embed_os_read_bufsize);
  }

  static PyObject *
  embed_os_read (PyObject *self, PyObject *_null)
  {
#define file io_file[IO_RAW]
    // global char buf[FD_BUFFER_MAX];
    buf[0] = 0;

    fseek (file, embed_os_read_cursor, SEEK_SET);
    fgets (&buf[0], FD_BUFFER_MAX, file);

    embed_os_read_cursor += strlen (buf);

    if (embed_os_read_cursor
        && (embed_os_read_cursor == embed_os_read_bufsize))
      {
        rewind (file);
        ftruncate (fileno (file), 0);
        embed_os_read_cursor = 0;
        embed_os_read_bufsize = ftell (file);
      }
    return Py_BuildValue ("y", buf);
#undef file
  }

// PYGBAG API

// module generated from pp_modules.cpp
#include "pykpocket_modules.gen"

  void
  pykpy_begin ()
  {
#if defined(__ANDROID__)
    // FIXME: goto assets dir and a lot of things
#else
    // defaults
    setenv ("LC_ALL", "C.UTF-8", 0);
    setenv ("TERMINFO", "/usr/share/terminfo", 0);
    setenv ("COLUMNS", "132", 0);
    setenv ("LINES", "30", 0);
    //    setenv("PYTHONINTMAXSTRDIGITS", "0", 0);
    setenv ("LANG", "en_US.UTF-8", 0);

    setenv ("TERM", "xterm", 0);
    setenv ("NCURSES_NO_UTF8_ACS", "1", 0);
    setenv ("MPLBACKEND", "Agg", 0);

    // force
    setenv ("PYTHONHOME", "/usr", 1);
    setenv ("PYTHONUNBUFFERED", "1", 1);
    setenv ("PYTHONINSPECT", "1", 1);
    setenv ("PYTHONDONTWRITEBYTECODE", "1", 1);
    setenv ("HOME", "/home/web_user", 1);
    setenv ("APPDATA", "/home/web_user", 1);

    setenv ("PYGLET_HEADLESS", "1", 1);

    umask (18); // 0022
#if defined(__EMSCRIPTEN__)
    chdir ("/");
    setenv ("TMP", "/tmp", 0);
#else
    chdir ("/tmp");
    setenv ("HOME", "/tmp/web_user", 1);
    setenv ("APPDATA", "/tmp/web_user", 1);
#endif
    makedir ("data");
    makedir ("data/data");
    makedir ("data/data/org.python");
    makedir ("data/data/org.python/assets");
#endif

    if (!mkdir ("dev", 0700))
      {
        puts ("no 'dev' directory, creating one ...");
      }

    if (!mkdir ("dev/fd", 0700))
      {
        // puts("no 'dev/fd' directory, creating one ...");
      }

    if (!mkdir ("tmp", 0700))
      {
        puts ("no 'tmp' directory, creating one ...");
      }

    for (int i = 0; i < FD_MAX; i++)
      io_shm[i] = NULL;

    io_file[0] = fopen ("dev/fd/0", "w+");
    io_stdin_filenum = fileno (io_file[0]);

    io_file[IO_RAW] = fopen ("dev/cons", "w+");
    io_raw_filenum = fileno (io_file[IO_RAW]);

    io_file[IO_RCON] = fopen ("dev/rcon", "w+");
    io_rcon_filenum = fileno (io_file[IO_RCON]);

    io_shm[0] = (char *)memset (malloc (FD_BUFFER_MAX), 0, FD_BUFFER_MAX);
    io_shm[IO_RAW] = (char *)memset (malloc (FD_BUFFER_MAX), 0, FD_BUFFER_MAX);
    io_shm[IO_RCON]
        = (char *)memset (malloc (FD_BUFFER_MAX), 0, FD_BUFFER_MAX);

#if defined(__EMSCRIPTEN__)

    EM_ASM ({
          const FD_BUFFER_MAX = $0;
          const shm_stdin = $1;
          const shm_rawinput = $2;
          const shm_rcon = $3;

          console.vm = {};
          console.vm.pkpy = $4;
          console.vm.is_browser = ((typeof window !== 'undefined') && 1) || 0;

          Module.printErr = Module.print;
          const is_worker = (typeof WorkerGlobalScope !== 'undefined') && self
              instanceof WorkerGlobalScope;

          if (is_worker) {
              console.log( "PyMain: running in a worker, setting onCustomMessage");
              function onCustomMessage(event) {
                console.log("onCustomMessage:", event);
                stringToUTF8(utf8encode (data), shm_rcon, $0);
              };

              Module['onCustomMessage'] = onCustomMessage;
          } else {
              console.log("PyMain: running in main thread, faking onCustomMessage");
              Module.postMessage = function custom_postMessage(event)  {
              switch (event.type) {
                  case "raw": {
                      stringToUTF8(event.data, shm_rawinput, FD_BUFFER_MAX);
                      break;
                    }

                  case "stdin": {
                      stringToUTF8(event.data, shm_stdin, FD_BUFFER_MAX);
                      break;
                    }
                  case "rcon": {
                      stringToUTF8(event.data, shm_rcon, FD_BUFFER_MAX);
                      break;
                    }
                  default:
                    console.warn("custom_postMessage?", event);
                  }
              };

              if (typeof window === 'undefined') {
                  if (FS)
                      console.warn("PyMain: Running in Node ?");
                  else
                      console.error("PyMain: not Node");
              } else {
                  if (window.BrowserFS) {
                      console.log("PyMain: found BrowserFS");
                  } else {
                      console.error("PyMain: BrowserFS not found");
                  }
                  SYSCALLS.getStreamFromFD(0).tty = true;
                  SYSCALLS.getStreamFromFD(1).tty = true;
                  SYSCALLS.getStreamFromFD(2).tty = false;
              }
            }
        }, FD_BUFFER_MAX, io_shm[0], io_shm[IO_RAW], io_shm[IO_RCON], !CPY);

    puts ("390:em_asm");

#endif // EMSCRIPTEN

    // Create a python virtual machine
    PYGBAG_INIT_VM;

    // add the pygbag "embed" module

    puts ("402:vm");

    // PyImport(embed);
    PyImport_AppendInittab ("embed", PyInit_embed);

    puts ("405");
    // PyObject *mod = PyInit_embed();

    //==============================================================================

    puts ("407:mod");

    PyRun_SimpleString("""
pkpyrc = 0
import os
os.environ = {}
__split__ = str.split

def split(it, value, max=0xdeadbeef):
    all = __split__(it,value)
    if max == 0xdeadbeef:
        return all
    result = []
    for i in range(max):
        if len(all):
            result.append(all.pop(0))
            continue
    if len(all):
        result.append( value.join(all) )
    return result


str.split=split


def rsplit(it, value, max=0xdeadbeef):
    all = __split__(it,value)
    if max == 0xdeadbeef:
        return all
    result = []
    for i in range(max):
        if len(all):
            result.append(all.pop())
            continue
    if len(all):
        result.insert(0, value.join(all) )
    return result


str.rsplit=rsplit
del split, rsplit
""");

    Py("__import__('sys')._emscripten_info = (", __EMSCRIPTEN_major__,",", __EMSCRIPTEN_minor__,",", __EMSCRIPTEN_tiny__,")");


// ============================= pythonrc ==================================
    char **env = environ;

    for (; *env; env++) {
      Py ("k,v = '''", CSTR (*env), "'''.split('=',1);os.environ[k]=v");
    }
  }

  em_callback_func *
  main_iteration (void)
  {

#if !defined(__EMSCRIPTEN__)

    vm->exec("""
import embed
if embed.is_browser():
    embed.jseval("browser: alert('pkpy is here' + JSON.stringify(console.vm))")
else:
    embed.jseval("console.log('node/native: pkpy is here'+JSON.stringify(console.vm))")
""");
    puts("cancelling");
    emscripten_cancel_main_loop();

#else

    int datalen = 0;
    int lines = 0;

    int silent = 0;

    // CONSOLE
    if ((datalen = io_file_select (IO_RCON)))
      {
#define file io_file[IO_RCON]
        // global char buf[IO_MAX];
        while (fgets (&buf[0], IO_MAX, file))
          {
            if (!lines && (strlen (buf) > 1))
              {
                silent = (buf[0] == '#') && (buf[1] == '!');
              }
            lines++;
            if (!silent)
              fprintf (stderr, "%d: %s", lines, buf);
          }
        rewind (file);
        PyRun_SimpleFile (file, "<stdin>");
/*

        if (lines>1)  {
            PyRun_SimpleFile( file, "<stdin>");
        } else {
            lines = 0;
            while( !PyRun_InteractiveOne( file, "<stdin>") ) lines++;
        }
        rewind(file);
*/
#undef file
      }

    // TTY
    if ((datalen = io_file_select (IO_RAW)))
      {
        embed_os_read_bufsize += datalen;
        // printf("raw data %i\n", datalen);
      }

    // READLINE buffer ( TTY accumulator )
    if ((datalen = io_file_select (0)))
      {
        embed_readline_bufsize += datalen;
        // embed_readline(NULL,NULL);
        // printf("stdin data +%i / bs=%i cur=%i [%s]\n", datalen,
        // embed_readline_bufsize, embed_readline_cursor, buf);
        // PyRun_SimpleFile( io_file[0], "<stdin>");
      }

    // TODO: pause instead of kill
    vm->exec("""
try:
    if pkpyrc:asyncio.step()
except:
    import traceback
    traceback.print_exc()
    print()
    print("killed")
    __import__('embed').emscripten_cancel_main_loop()
""");

#endif // __EMSCRIPTEN__
    HOST_RETURN_YIELD;
  }

  // Dispose the virtual machine
  void
  pykpy_end ()
  {
    delete vm;
  }

} // extern "C"
