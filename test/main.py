# this test is only for pygbag internals
# to learn about pygbag, go to https://pygame-web.github.io instead.

# Green threads are ordered at runtime unlike system threads.
# they may be usefull for ECS and porting software to async web.

# on native, this test show how threading model can be toxic for drawing.
# do not use this code :
#   hardware threads are better used for I/O, neural net, pipelines


import builtins

# fixme should be auto
if __import__("os").uname().machine.startswith("wasm"):
    import aio.gthread as threading

else:
    # native case

    import asyncio as aio

    aio.exit = False
    aio.frame = 1.0 / 60
    aio.sync = False

    # because threading target= does not handle generators
    def synchronized(f):
        def run(*argv, **kw):
            global Native
            gen = f(*argv, **kw)
            while True:
                deadline = time.time() + aio.frame
                if next(gen) is StopIteration:
                    return
                alarm = deadline - time.time()
                if alarm > 0:
                    time.sleep(alarm)

        return run


import asyncio
import pygame
import time

pygame.init()

import module

print()
print(f"{aio=} {aio.sync=}")
print()


def new_screen(title):
    global screen
    pygame.display.set_caption(title)
    screen = pygame.display.set_mode((640, 360))
    return screen


from threading import Thread


class Moving_svg(Thread):

    def __init__(self):
        super().__init__()
        print(f"{self.native_id=} {self.ident=} {self.is_alive()=}")
        self.surf = pygame.image.load("img/tiger.svg")
        self.way = 1
        self.auth = False

    def loop(self):
        decal = abs(count) % 100
        if not decal:
            self.way = -self.way
        self.win.blit(self.surf, (50 + (self.way * decal), 50 + (-self.way * decal)))

    @synchronized
    def run(self):
        print(f"{self.native_id=} {self.ident=} {self.is_alive()=}")
        while self:
            if self.auth:
                self.loop()
                self.auth = False
            yield aio


# ok model
moving_svg = None


@synchronized
def color_background(win):
    global moving_svg, count
    while not aio.exit:
        if 1:
            if moving_svg:
                if not moving_svg.auth:
                    win.fill((count % 50, count % 50, count % 50))
                    moving_svg.auth = True
            else:
                win.fill((count % 50, count % 50, count % 50))
        yield aio


@synchronized
def moving_bmp(win):
    global count
    print("moving_bmp started")
    bmp = pygame.image.load_basic("img/pygc.bmp")
    way = 1
    while not aio.exit:
        decal = abs(count) % 100
        if not decal:
            way = -way

        win.blit(bmp, (50 + (way * decal), 50 + (-way * decal)))
        yield aio


@synchronized
def moving_png(win):
    global count
    print("moving_png started")
    try:
        png = pygame.image.load("img/pygc.png")
    except:
        print("png support error upgrade SDL_image !")
        return

    way = 1
    while not aio.exit:
        decal = abs(count) % 100
        if not decal:
            way = -way

        win.blit(png, (200 + (way * decal), 100 + (way * decal)))
        yield aio


async def main():
    global count, bmp, moving_svg

    # using the whole display.
    win = new_screen("TEST")

    count = 3

    # still bugs in that thread model
    # mbmp = Moving_bmp()

    # erase and fill
    (t1 := Thread(target=color_background, args=[win])).start()

    moving_svg = Moving_svg()
    moving_svg.win = win
    print(f"{moving_svg.native_id=} {moving_svg.ident=} {moving_svg.is_alive()=}")
    moving_svg.start()

    # 1st object to draw
    t2 = Thread(target=moving_bmp, args=[win])
    t2.start()

    # 2nd

    t3 = Thread(target=moving_png, args=[win])
    t3.start()

    print(t1.native_id, t2.native_id, t3.native_id)

    while True:
        if count >= 0:
            print(
                f"""

    Hello[{count}] from Pygame

"""
            )

        #        if moving_svg and moving_svg.native_id:
        #            moving_svg.loop()

        pygame.display.update()

        if not aio.sync:
            time.sleep(aio.frame)  # frametime idle

        await asyncio.sleep(0)

        if count < -60 * 30:  # about * seconds
            print("exit game loop")
            break

        count = count - 1

    pygame.quit()


asyncio.run(main())
