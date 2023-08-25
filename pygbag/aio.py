import sys

import aio

# to allow "import pygbag.aio as asyncio"
sys.modules["pygbag.aio"] = aio

# if not wasm cpu then run caller in simulator and block.
if not __import__("os").uname().machine.startswith("wasm"):
    import time
    from pathlib import Path

    import aioconsole

    import aio.pep0722

    import pygbag.__main__

    async def custom_async_input():
        return await aioconsole.ainput("››› ")

    aio.loop.create_task(
        pygbag.__main__.import_site(
            sourcefile=sys.argv[-1],
            simulator=True,
            async_input=custom_async_input,
            async_pkg=aio.pep0722.check_list(sys.argv[-1]),
        )
    )

    # todo use a thread for watchdog.

    # simulate .requestAnimationFrame() infinite loop

    while not aio.exit:
        next = time.time() + 0.016
        aio.loop._run_once()

        dt = next - time.time()
        if dt < 0:
            past = int(-dt * 1000)
            if past > 0:
                print(f"aio: violation frame is {past} ms late")
        else:
            time.sleep(dt)
    print("sim loop exited")
