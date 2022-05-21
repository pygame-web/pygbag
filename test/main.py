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
