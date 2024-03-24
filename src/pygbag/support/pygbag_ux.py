# screen pixels (real, hardware)
WIDTH = 1280  # {{cookiecutter.width}}
HEIGHT = 720  # {{cookiecutter.height}}


def dim(w, h):
    global WIDTH, HEIGHT
    WIDTH = int(w)
    HEIGHT = int(h)


# reference/idealized screen pixels
REFX = 1980
REFY = 1080


def u(real, ref, v):
    if abs(v) < 0.9999999:
        result = int((float(real) / 100.0) * (v * 1000))
        if v < 0:
            return real - result
        return result
    return int((real / ref) * v)


def x(*argv):
    global WIDTH, REFX
    acc = 0
    for v in argv:
        acc += u(WIDTH, REFX, v)
    return acc


def y(*argv):
    global HEIGHT, REFY
    acc = 0
    for v in argv:
        acc += u(HEIGHT, REFY, v)
    return acc


def r(*argv):
    rx = x(argv[0])
    ry = y(argv[1])
    ret = [rx, ry]
    if len(argv) > 2:
        w = x(argv[2])
        h = y(argv[3])
        ret.append(w)
        ret.append(h)
    return ret


from pathlib import Path

# ====================== pygame


def pg_load(fn, resize=None, width=0, height=0, alpha=True):
    import pygame
    from pathlib import Path

    if Path(fn).is_file():
        media = pygame.image.load(fn)
    else:
        media = pygame.image.load(Path(__file__).parent / "offline.png")

    if resize:
        tmp = pygame.transform.smoothscale(media, resize)
        media = tmp
    elif width and height:
        media = pygame.transform.smoothscale(
            media,
            (
                width,
                heigh,
            ),
        )

    try:
        if alpha:
            return media.convert_alpha()
        else:
            return media.convert()
    # offscreen case
    except:
        return media


class vpad:
    X = 0
    Z = 1
    Y = 2
    evx = []
    evy = []
    evz = []
    axis = [evx, evz, evy]

    LZ = 0.5

    @classmethod
    def get_axis(self, n):
        if len(self.axis[n]):
            return self.axis[n].pop(0)
        return 0.0

    @classmethod
    def emit(self, axis, value):
        import pygame

        self.axis[axis].append(float(value))
        ev = pygame.event.Event(pygame.JOYAXISMOTION)
        pygame.event.post(ev)
        return False
