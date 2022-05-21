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
        await asyncio.sleep(0)

        if not count:
            pygame.quit()
            return
        count = count - 1


asyncio.run( main() )
```



usage:

    pip3 install pygbag --upgrade
    pygbag your_game_folder

command help:

    pygbag --help your_game_folder

```
usage: __main__.py [-h] [--bind ADDRESS] [--directory DIRECTORY]
                   [--cache CACHE] [--cdn CDN] [--template TEMPLATE]
                   [--ssl SSL] [--port [PORT]]

optional arguments:
  -h, --help            show this help message and exit
  --bind ADDRESS        Specify alternate bind address [default: localhost]
  --directory DIRECTORY
                        Specify alternative directory
                        [default: <your_game_folder>/build/web]
  --cache CACHE         md5 based url cache directory
  --cdn CDN             web site to cache locally
                        [default:https://pmp-p.github.io/pygbag/]
  --template TEMPLATE   index.html template
  --ssl SSL             enable ssl with server.pem and key.pem
  --port [PORT]         Specify alternate port [default: 8000]
```


Now navigate to http://localhost:8000 with a modern Browser
v8 based browser are preferred ( chromium/brave/chrome ... )
because imposing some baseline restrictions on WebAssembly loading.


NOTES:

 - first load will be slower, because setting up local cache from cdn to avoid
useless network transfer for getting pygame and cpython prebuilts.

 - each time changing code/template you must restart `pygbag your_game_folder`
   but cache is not destroyed.

 - if you want to reset prebuilts cache, remove the build/web-cache folder in
   your_game_folder




support via Discord:

    https://discord.gg/t3g7YjK7rw   ( #pygame-web on Pygame Community )


