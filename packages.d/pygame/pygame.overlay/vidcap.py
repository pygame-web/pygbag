import sys
import os
import asyncio
import pygame
import pygame.camera
from pygame.camera import *

del Camera

if sys.platform == "emscripten":
    import platform

    def get_backends() -> [str]:
        return ["html5"]


    def list_cameras() -> [int]:
        return ["/dev/video0"]

# TODO: https://toji.dev/webgpu-best-practices/img-textures



    class Camera:
        cam = platform.window.MM.camera

        def __init__(self, device, size, format):
            self.device = device
            self.width, self.height = size
            self.format = format
            self.surface = None

        async def start(self):
            status = await platform.jsiter(
                platform.window.MM.camera.init(self.device, self.width, self.height, 0, self.format)
            )
            print(f"camera {self.device=} {status=}")

        # queue a image request and pretend we have already the image.
        def query_image(self):
            return platform.window.MM.camera.query_image()

        def get_image(self, surface = None ):
            if surface:
                ...
            try:
                return pygame.image.load(self.device)
            finally:
                os.unlink(self.device)

        def make_surface(self):
            if surface is None:
                ...
            return self.surface


        def get_raw(self):
            platform.window.MM.camera.get_raw()

else:

    class Camera(pygame.camera.Camera):
        async def start(self):
            ...

