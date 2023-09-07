import sys

import aio

# to allow "import pygbag.aio as asyncio"
sys.modules["pygbag.aio"] = aio

# if not wasm cpu then run caller in simulator and block.
if not __import__("os").uname().machine.startswith("wasm"):
    import time
    from pathlib import Path

    import aioconsole

    import aio.pep0723

    aio.pep0723.Config.dev_mode = ".-X.dev." in ".".join(sys.orig_argv)
    if aio.pep0723.Config.dev_mode:
        aio.pep0723.Config.PKG_INDEXES.extend(["http://localhost:8000/archives/repo/"])
    else:
        aio.pep0723.Config.PKG_INDEXES.extend(["https://pygame-web.github.io/archives/repo/"])

    import pygbag.__main__

    async def custom_async_input():
        return await aioconsole.ainput("››› ")

    aio.loop.create_task(
        pygbag.__main__.import_site(
            sourcefile=sys.argv[-1],
            simulator=True,
            async_input=custom_async_input,
            async_pkg=aio.pep0723.check_list(filename=sys.argv[-1]),
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
            # do not spam for 2 ms late
            if past > 2:
                print(f"aio: violation frame is {past} ms late")
        else:
            time.sleep(dt)
    print("sim loop exited")
