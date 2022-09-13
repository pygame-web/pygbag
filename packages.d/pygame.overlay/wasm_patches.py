import sys
import asyncio
import json

from platform import window, is_browser

from pathlib import Path

#=================================================
# do no change import order for *thread*
# patching threading.Thread
import aio.gthread
# patched module
from threading import Thread
#=================================================



pygame = sys.modules[__package__]

# ====================================================================
# replace non working native function.

print(
    """\
https://github.com/pygame-web/pygbag/issues/16
    applying: use aio green thread for pygame.time.set_timer
"""
)

# build the event and send it directly in the queue
# caveats :
#   - could be possibly very late
#   - delay cannot be less than frametime at device refresh rate.

def patch_set_timer(cust_event_no, millis, loops=0):
    dlay = float(millis) / 1000
    cevent = pygame.event.Event(cust_event_no)

    async def fire_event():
        while true:
            await asyncio.sleep(dlay)
            if aio.exit:
                break
            pygame.event.post(cevent)

    Thread(target=fire_event).start()


pygame.time.set_timer = patch_set_timer

# ====================================================================
# pygame.quit is too hard on gc, and re-importing pygame is problematic
# if interpreter is not fully renewed.
# so just clear screen cut music and hope for the best.


def patch_pygame_quit():
    pygame.mixer.music.stop()
    pygame.mixer.music.unload()
    pygame.display.update()


pygame.quit = patch_pygame_quit


# =====================================================================
# we want fullscreen-windowed template for games as a default
# so call javascript to resize canvas viewport to fill the current
# window each time mode is changed, also remove the "scaled" option

__pygame_display_set_mode__ = pygame.display.set_mode


def patch_pygame_display_set_mode(size=(0,0), flags=0, depth=0):

    # apparently no need to remove scaled.
    if size != (0,0):
        if (sys.platform == "emscripten") and is_browser:
            try:
                window.window_resize()
            except:
                print("ERROR: browser host does not provide window_resize() function",file=sys.__stderr__)

    return __pygame_display_set_mode__(size, flags, depth)


pygame.display.set_mode = patch_pygame_display_set_mode


#=======================================================================
# replace sdl thread music playing by browser native player
#

tracks = { "current": 0 }


def patch_pygame_mixer_music_stop_pause_unload():
    last = tracks["current"]
    if last:
        window.MM.stop(last)
        tracks["current"] = 0

pygame.mixer.music.unload = patch_pygame_mixer_music_stop_pause_unload

def patch_pygame_mixer_music_load(fileobj, namehint=""):

    global tracks

    patch_pygame_mixer_music_stop_pause_unload()

    tid = tracks.get( fileobj, None)

    # stop previously loaded track
    if tid is not None:
        window.MM.stop(tid)
    else:
        # track was never loaded before
        track = patch_pygame_mixer_sound(fileobj, auto=True)
        tid = track.trackid

    # set new current track
    tracks["current"] = tid

pygame.mixer.music.load = patch_pygame_mixer_music_load

# TODO various buffer input
# FIXME tracks hash key
def patch_pygame_mixer_sound(data, auto=False):
    global tracks
    if isinstance(data, (Path,str) ):
        data = str(data)
        trackid = tracks.get(data,None)
        if trackid is not None:
            return tracks[trackid]
    else:
        pdb(__file__, "137 TODO buffer types !")

    if Path(data).is_file():
        transport = "fs"
    else:
        transport = "url"

    cfg= {
        "url"  : data,
        "type" : "audio",
        "auto" : auto,
        "io" : transport
    }

    track = window.MM.prepare(data, json.dumps(cfg))

    if track.error:
        pdb("ERROR: on track",cfg)
        # TODO stub track
        return "stub track"

    tracks[data] = track.trackid
    tracks[track.trackid] = track
    window.MM.load(track.trackid)
    return track

BUFFERSIZE = 2048

# 0.1.6 force soundpatch
if 0:
    def patch_pygame_mixer_SoundPatch():
        print("pygame mixer SFX patch is already active you can remove this call")

else:

    def patch_pygame_mixer_SoundPatch():
        pygame.mixer.Sound = patch_pygame_mixer_sound
        print("pygame mixer SFX patch is now active")


    __pygame_mixer_init = pygame.mixer.init

    def patch_pygame_mixer_init(frequency=44100, size=-16, channels=2, buffer=512, devicename=None, allowedchanges=0) -> None:
        global BUFFERSIZE
        buffer = BUFFERSIZE
        print("\n"*4)
        print("@"*60)
        print(f"pygame mixer init {frequency=}, {size=}, {channels=}, {buffer=}" )

        __pygame_mixer_init(frequency, size, channels, buffer)


    pygame.mixer.init = patch_pygame_mixer_init


pygame.mixer.SoundPatch = patch_pygame_mixer_SoundPatch


def patch_pygame_mixer_music_play(loops=0, start=0.0, fade_ms=0):
    trackid = tracks["current"]
    if trackid:
        window.MM.stop(trackid)
        window.MM.play(trackid, loops )
    else:
        pdb(__file__, "ERROR 156: no track is loaded")

pygame.mixer.music.play = patch_pygame_mixer_music_play


pygame.mixer.pre_init(buffer = BUFFERSIZE)















# ====================================================================
print("\n\n")
print(open("/data/data/org.python/assets/pygame.six").read())
