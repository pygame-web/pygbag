#define MODULE_NAME "embed"

PyObject *
PyInit_embed() {
    PyObject *mod = vm->new_module(MODULE_NAME);
    if (!mod) {
        puts("PyInit_" MODULE_NAME " : module not allocated");
        return NULL;
    }

    vm->bind(mod, "readline() -> str", [](VM * vm, ArgsView argv) {
         return embed_readline(PyNULL, PyNULL);}
    );

    vm->bind(mod, "stdin_select() -> int", [](VM * vm, ArgsView argv) {
         return embed_stdin_select(PyNULL, PyNULL);
    });

    vm->bind(mod, "os_read() -> bytes", [](VM * vm, ArgsView argv) {
         return embed_os_read(PyNULL, PyNULL);
    });

    vm->bind(mod, "emscripten_cancel_main_loop() -> None", [](VM * vm, ArgsView argv) {
         emscripten_cancel_main_loop(); Py_RETURN_NONE;
    });

    vm->bind(mod, "_new_module(name:str, code:str) -> None", [](VM * vm, ArgsView argv) {
        Str & name = py_cast < Str & >(vm, argv[0]);
        Str & code = py_cast < Str & >(vm, argv[1]);
        vm->_lazy_modules[name] = code;
        Py_RETURN_NONE;
    });

    //_CAST(Str&, vm->py_str(argv[0])).c_str());

#if defined(__EMSCRIPTEN__)
    vm->bind(mod, "jseval(js: str='') -> Any",[](VM * vm, ArgsView argv) {
        Str & js = py_cast < Str & >(vm, argv[0]);
        char *json = (char *)EM_ASM_PTR({
            try {
                const toeval = UTF8ToString($0);
                var result = null;
                const evalue = eval(toeval);
                if (evalue instanceof Function) {
                    result = "[native code]";
                } else {
                    if (evalue === undefined) {
                        result = null;
                    }
                    else {
                        result = evalue;
                    }
                }
            } catch(x) {
                result = (`Exception(${x})`);
            }
            return stringToNewUTF8(JSON.stringify(result));
        }, js.c_str());

        PyObject * json_loads = vm->_modules["json"]->attr("loads");
        PyObject * result = vm->call(json_loads, py_var(vm, std::string_view(json)));
        free(json);
        return result;
    });

#else
    vm->bind(mod, "jseval(js: str='') -> str",[](VM * vm, ArgsView argv) {
        Str & js = py_cast < Str & >(vm, argv[0]);
        emscripten_run_script(js.c_str());
        return py_var(vm, js);
    });
#endif

    vm->bind(mod, "is_browser() -> int",[](VM * vm, ArgsView argv) {
#if defined(__EMSCRIPTEN__)
        int test_result = EM_ASM_INT({
             return console.vm.is_browser;
        });
#else
        int test_result = 0;
#endif
        return py_var(vm, test_result);
    });
    return mod;
}

#undef MODULE_NAME


#if PK_ENABLE_OS
#else
#define MODULE_NAME "os"

PyObject *
PyInit_os() {
    PyObject *mod = vm->new_module(MODULE_NAME);
    if (!mod) {
        puts("PyInit_" MODULE_NAME " : module not allocated");
        return NULL;
    }

    vm->bind(mod, "read() -> bytes",[](VM * vm, ArgsView argv) {
         return embed_os_read(PyNULL, PyNULL);
    });

    return mod;
}

#undef MODULE_NAME
#endif


