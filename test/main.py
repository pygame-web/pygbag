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


# still bugs in that thread model
class Moving_bmp(Thread):
    async def run(self):
        global count, screen
        bmp = pygame.image.load_basic( "pygc.bmp" )
        way = 1
        while await self:
            decal = abs(count) % 100
            if not decal:
                way = -way
            screen.blit( bmp, (50+(way*decal), 50 + (-way*decal)) )


def moving_bmp(win):
    global count
    bmp = pygame.image.load_basic( "pygc.bmp" )
    way = 1
    while not aio.exit:
        decal = abs(count) % 100
        if not decal:
            way = -way

        win.blit( bmp, (50+(way*decal), 50 + (-way*decal)) )
        yield aio




def moving_png(win):
    global count
    try:
        png = pygame.image.load( "pygc.png" )
        way = 1
        while not aio.exit:
            decal = abs(count) % 100
            if not decal:
                way = -way

            win.blit( png, (200+(way*decal), 100 + (way*decal) ) )
            yield aio
    except:
        print("png support error upgrade SDL_image !")


def color_background(win):
    while not aio.exit:
        win.fill( (count % 50, count % 50, count % 50) )
        yield aio


async def main():
    global count, bmp

    # using the whole display.
    win = new_screen("TEST")

    count = 3

    # still bugs in that thread model
    #mbmp = Moving_bmp()

    mbmp = Thread(target=moving_bmp, args=[win])
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
            # Green threads are ordered at runtime unlike system threads.

            # erase and fill
            mbg.start()

            # 1st object to draw
            mpng.start()

            # 2nd
            mbmp.start()




        pygame.display.update()
        await asyncio.sleep(0)

        if count < -60 * 30: # about * seconds
            pygame.quit()
            return

        count = count - 1


asyncio.run(main())
