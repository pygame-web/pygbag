# pygbag
PyGame wasm for everyone ( packager + test server )


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

```

usage: __main__.py [-h] your_game_folder[/main.py]

optional arguments:
  -h, --help            show this help message and exit
  --bind ADDRESS        Specify alternate bind address [default: localhost]
  --directory DIRECTORY
                        Specify alternative directory [default:/data/git/pygbag/test/build/web]
  --app_name APP_NAME   Specify user facing name of application[default:test]
  --cache CACHE         md5 based url cache directory
  --package PACKAGE     package name, better make it unique
  --version VERSION     package name, please make it unique
  --build               build only, do not run test server
  --main MAIN           Specify main script[default:main.py]
  --icon ICON           package name, please make it unique
  --cdn CDN             web site to cache locally [default:https://pygame-web.github.io/pygbag/]
  --template TEMPLATE   index.html template
  --ssl SSL             enable ssl with server.pem and key.pem
  --port [PORT]         Specify alternate port [default: 8000]

```

Now navigate to http://localhost:8000 with a modern Browser.

v8 based browsers are preferred ( chromium/brave/chrome ... )
because they set baseline restrictions on WebAssembly loading.
using them while testing ensure proper operation on all browsers.


NOTES:

 - first load will be slower, because setting up local cache from cdn to avoid
useless network transfer for getting pygame and cpython prebuilts.

 - each time changing code/template you must restart `pygbag your_game_folder`
   but cache is not destroyed.

 - if you want to reset prebuilts cache, remove the build/web-cache folder in
   your_game_folder




support via Discord:

    https://discord.gg/t3g7YjK7rw   ( #pygame-web on Pygame Community )


