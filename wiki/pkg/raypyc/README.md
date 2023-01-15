# raypyc on the web

In this little guide you will learn how to use raypyc with pygbag to compile your game for the web.

## Step 1 - Getting pygbag

To get pygbag, use pip, to do so use this command:

```cmd
pip install pygbag
```

## Step 2 - Setting up your environment

### 2.1 - Setting up raypyc

First you need to get the **raypyc** folder from the raypyc repo. To do so, let's begin by cloning it using the
following command:

```cmd
git clone --depth 1 https://github.com/sDos280/raylib-python-ctypes.git
```

After cloning, copy the **raypyc** folder from the repository into your environment.

### 2.2 - Setting up your python code

Here is a basic example:

```py
from raypyc import *


# ------------------------------------------------------------------------------------
# Program main entry point
# ------------------------------------------------------------------------------------
def main():
    # Initialization
    # ------------------------------------------------------------------------------------
    SCREEN_WIDTH = 800
    SCREEN_HEIGHT = 450

    init_window(SCREEN_WIDTH, SCREEN_HEIGHT, b"raylib [core] example - basic window")

    # TODO: Load resources / Initialize variables at this point

    set_target_fps(60)  # Set our game to run at 60 frames-per-second
    # ------------------------------------------------------------------------------------

    # Main game loop
    while not window_should_close():  # Detect window close button or ESC key
        # Update
        # ----------------------------------------------------------------------------------
        # TODO: Update variables / Implement example logic at this point
        # ----------------------------------------------------------------------------------

        # Draw
        # ----------------------------------------------------------------------------------
        begin_drawing()

        clear_background(RAYWHITE)
        draw_text(b"Congrats! You created your first window!", 190, 200, 20, LIGHTGRAY)

        end_drawing()
        # ----------------------------------------------------------------------------------

    # De-Initialization
    # ----------------------------------------------------------------------------------

    # TODO: Unload all loaded resources at this point

    close_window()  # Close window and OpenGL context
    # ----------------------------------------------------------------------------------


# Execute the main function
if __name__ == '__main__':
    main()
```

And here is the basic example for the web:

```py
import asyncio
from raypyc import *


# ------------------------------------------------------------------------------------
# Program main entry point
# ------------------------------------------------------------------------------------
async def main():
    # Initialization
    # ------------------------------------------------------------------------------------
    SCREEN_WIDTH = 800
    SCREEN_HEIGHT = 450

    init_window(SCREEN_WIDTH, SCREEN_HEIGHT, b"raylib [core] example - basic window")

    # TODO: Load resources / Initialize variables at this point

    set_target_fps(60)  # Set our game to run at 60 frames-per-second
    # ------------------------------------------------------------------------------------

    # Main game loop
    while True:
        # Update
        # ----------------------------------------------------------------------------------
        # TODO: Update variables / Implement example logic at this point
        # ----------------------------------------------------------------------------------

        # Draw
        # ----------------------------------------------------------------------------------
        begin_drawing()

        clear_background(RAYWHITE)
        draw_text(b"Congrats! You created your first window!", 190, 200, 20, LIGHTGRAY)

        end_drawing()
        # ----------------------------------------------------------------------------------
        await asyncio.sleep(0)


asyncio.run(main())
```

What we changed:

- We are now using `asyncio`.
- Using a `while True` instead of `while not window_should_close`.
- Not calling `close_window`, using `await asyncio.sleep(0)` instead (the 0 is required).
- Using `asyncio.run(main())` instead of `if __name__ == '__main__': main()`.

in the end your project tree should look like this.

```
your_folder_name/
 | your_file_name.py
 | raypyc /
 | raylib-python-ctypes /
```

## Step 3 - Running our project in the web

run this command:

```cmd
py -m pygbag --ume_block 0 --template noctx.tmpl ../your_folder_name/your_file_name.py
```

open [http://localhost:8000/](http://localhost:8000/), wait a bit (to make sure that everying loaded properly), and we are done!!!
feel free to ask any question / open issue on gethub!!
