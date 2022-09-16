# pygbag

pygame wasm for everyone ( packager + test server )

runs pygame directly in modern web browsers, including mobile versions.



"your_game_folder" must contains a main.py and its loop must be async aware eg :

```py
import asyncio
import pygame

pygame.init()
pygame.display.set_mode((320, 240))
pygame.display.set_caption("TEST")


async def main():
    count = 3

    while True:
        print(f"""

        Hello[{count}] from Pygame

""")
        pygame.display.update()
        await asyncio.sleep(0)  # very important, and keep it 0

        if not count:
            pygame.quit()
            return
        count = count - 1

asyncio.run( main() )

# do not add anything from here
# asyncio.run is non block on pygame-wasm
```

usage:

    pip3 install pygbag --user --upgrade
    pygbag your_game_folder

command help:

    pygbag --help your_game_folder


eg

```
user@pp /data/git/pygbag-wip $ python3.8 -m pygbag --help test
 *pygbag 0.2.0*

Serving python files from [/data/git/pygbag-wip/test/build/web]

with no security/performance in mind, i'm just a test tool : don't rely on me

usage: __main__.py [-h] [--bind ADDRESS] [--directory DIRECTORY]
 [--app_name APP_NAME] [--ume_block UME_BLOCK] [--cache CACHE]
 [--package PACKAGE] [--title TITLE] [--version VERSION] [--build]
 [--archive] [--icon ICON] [--cdn CDN] [--template TEMPLATE]
 [--ssl SSL] [--port [PORT]]

optional arguments:
  -h, --help            show this help message and exit
  --bind ADDRESS        Specify alternate bind address [default: localhost]
  --directory DIRECTORY
                        Specify alternative directory [default:/data/git/pygbag/test/build/web]
  --PYBUILD PYBUILD     Specify python version [default:3.11]
  --app_name APP_NAME   Specify user facing name of application [default:test]
  --ume_block UME_BLOCK
                        Specify wait for user media engagement before running [default:1]
  --can_close CAN_CLOSE
                        Specify if window will ask confirmation for closing [default:0]
  --cache CACHE         md5 based url cache directory
  --package PACKAGE     package name, better make it unique
  --title TITLE         App nice looking name
  --version VERSION     override prebuilt version path [default:0.3.0]
  --build               build only, do not run test server
  --html                build as html with embedded assets (pygame-script)
  --no_opt              turn off assets optimizer
  --archive             make build/web.zip archive for itch.io
  --icon ICON           icon png file 32x32 min should be favicon.png
  --cdn CDN             web site to cache locally [default:https://pygame-web.github.io/archives/0.3.0/]
  --template TEMPLATE   index.html template [default:default.tmpl]
  --ssl SSL             enable ssl with server.pem and key.pem
  --port [PORT]         Specify alternate port [default: 8000]
```

Now navigate to http://localhost:8000 with a modern Browser.

use http://localhost:8000#debug for getting a terminal and a sized down canvas

for pygame-script go to http://localhost:8000/your_game_folder.html



v8 based browsers are preferred ( chromium/brave/chrome ... )
starting with 81.0.4044 ( android 4.4 ).
Because they set baseline restrictions on WebAssembly loading.
Using them while testing ensure proper operation on all browsers.


NOTES:

 - first load will be slower, because setting up local cache from cdn to avoid
useless network transfer for getting pygame and cpython prebuilts.

 - each time changing code/template you must restart `pygbag your_game_folder`
   but cache is not destroyed.

 - if you want to reset prebuilts cache, remove the build/web-cache folder in
   your_game_folder


BUILDING:

pygbag is not only a python module, and rebuilding all the toolchain can be quite
hard

https://github.com/pygame-web/python-wasm-sdk  <= build CPython (not pyodide)

then read/use pygbag CI to see how to build pygame + the C loader (pymain) and
link it to libpython + libpygame

https://github.com/pygame-web/pygbag

prebuilts used by pygbag are stored on github
from the repo https://github.com/pygame-web/archives under versionned folders


ADDING STATIC MODULES:

    see in package.d directory



Support via Discord:

    https://discord.gg/t3g7YjK7rw   ( #pygame-web on Pygame Community )


French support:

    forum thead:
        https://discuss.afpy.org/t/moteur-2d-pour-python-pygame-web/834/2

    irc:
        #python-fr-off on libera.chat


