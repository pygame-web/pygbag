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

    if '.-X.dev.' in '.'.join(sys.orig_argv):
        aio.pep0722.Config.PKG_INDEXES.extend( ["http://localhost:8000/archives/repo/"] )
    else:
        aio.pep0722.Config.PKG_INDEXES.extend( ["https://pygame-web.github.io/archives/repo/"] )

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


"""

typing-extensions

    route = PathRoute(root=tmp_path, to="{project}")
    resp = await route.get_page({"project": "my-package"})
    assert resp.status_code == 200

    links = mousebender.simple.parse_archive_links(resp.text)
    assert [link.filename for link in links] == project_files
    assert [link.url for link in links] == [f"./{n}" for n in project_files]



"""

