        PyImport_AppendInittab("embed_emscripten", PyInit_emscripten);
        PyImport_AppendInittab("embed_browser", PyInit_browser);
#       pragma message "emsdk is statically linked as built-in"
