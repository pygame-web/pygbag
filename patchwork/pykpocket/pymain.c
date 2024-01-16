
#include "pygbag.h"

extern void pykpy_begin();
extern em_callback_func *main_iteration(void);

int
main(int argc, char **argv) {
    pykpy_begin();
    emscripten_set_main_loop( (em_callback_func)main_iteration, 0, 1);
    return 0;
}


