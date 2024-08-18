import sys
import os

# this aio is the support/cross one, not the current file.
import aio

# to allow "import pygbag.aio as asyncio"
sys.modules["pygbag.aio"] = aio

if hasattr(os, "uname") and not os.uname().machine.startswith("wasm"):
    import time
    from pathlib import Path

    try:
        # import aioconsole, aiohttp
        import aiohttp
    except Exception as e:
        pkglist = "aiohttp asyncio_socks_server token_utils"
        print(
            e,
            f"""

pygbag simulator rely on : {pkglist}
please use :

    MULTIDICT_NO_EXTENSIONS=1 {sys.executable} -m pip install {pkglist}

""",
        )
        raise SystemExit

    import aio.pep0723

    if aio.pep0723.Config.dev_mode:
        aio.pep0723.Config.PKG_INDEXES.extend(["http://localhost:8000/archives/repo/"])
    else:
        aio.pep0723.Config.PKG_INDEXES.extend(
            [
                os.environ.get("PYGPY", "https://pygame-web.github.io/archives/repo/"),
            ]
        )

    import pygbag.__main__

    #
    #    async def custom_async_input():
    #        import platform
    #        if platform.window.RAW_MODE:
    ## TODO: FIXME: implement embed.os_read and debug focus handler
    #            #return await asyncio.sleep(0)
    #            ...
    #        return await aioconsole.ainput("››› ")

    aio.loop.create_task(
        pygbag.__main__.import_site(
            sourcefile=sys.argv[0],
            simulator=True,
            #            async_input=custom_async_input,
            async_input=None,
            async_pkg=aio.pep0723.check_list(filename=sys.argv[0]),
        )
    )

    # todo use a thread for watchdog.

    # simulate .requestAnimationFrame() infinite loop

    # make aiohttp happy
    aio.started = True

    while not aio.exit:
        next = time.time() + 0.016
        try:
            aio.loop._run_once()
        except KeyboardInterrupt:
            print("45: KeyboardInterrupt")

        dt = next - time.time()
        if dt < 0:
            past = int(-dt * 1000)
            # do not spam for <5 ms late (50Hz vs 60Hz)
            if past > 5:
                print(f"\raio: violation frame is {past} ms late")
            # too late do not sleep at all
        else:
            time.sleep(dt)
    print("sim loop exited")
    sys.stdout.flush()
