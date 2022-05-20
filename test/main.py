import asyncio
import pygame

pygame.init()
pygame.display.set_mode((320, 240))
pygame.display.set_caption("TEST")


async def main():

    while True:
        print("""


    Hello from Pygame


""")
        pygame.display.update()
        await asyncio.sleep(0)

        if True:
            return


asyncio.run( main() )
