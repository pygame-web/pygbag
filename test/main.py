#fixme should be auto
import aio.gthread

import asyncio
import pygame

pygame.init()

def new_screen(title):
    global screen
    pygame.display.set_caption(title)
    screen = pygame.display.set_mode((640, 360))
    return screen




from threading import Thread


class Moving_bmp(Thread):
    async def run(self):
        global count, screen
        bmp = pygame.image.load_basic( "pygc.bmp" )

        while await self:
            decal = abs(count) % 100
            if not decal:
                way = -way
            screen.blit( bmp, 50+(way*decal), 50 + (way*decal) )


def moving_png(win):
    global count
    png = pygame.image.load( "pygc.png" )
    way = 1
    while not aio.exit:
        decal = abs(count) % 100
        if not decal:
            way = -way

        win.blit( png, (200+(way*decal), 100 + (way*decal) ) )
        yield aio


def color_background(win):
    while not aio.exit:
        win.fill( (count % 50, count % 50, count % 50) )
        yield aio



bmp = pygame.image.load_basic( "pygc.bmp" )

async def main():
    global count, bmp

    # using the whole display.
    win = new_screen("TEST")

    count = 3

    mbmp = Moving_bmp()
    mpng = Thread(target=moving_png, args=[win])

    mbg = Thread(target=color_background, args=[win])


    while True:
        if count>=0:
            print(
            f"""

    Hello[{count}] from Pygame

"""
        )

        if count == 0:

            screen.blit( bmp, (abs(count) % 100,abs(count) % 100) )
            mbmp.start()
            mbg.start()
            mpng.start()


        pygame.display.update()
        await asyncio.sleep(0)

        if count < -60 * 30: # about * seconds
            pygame.quit()
            return

        count = count - 1


asyncio.run(main())
