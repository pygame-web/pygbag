import sys
import pygbag
from pathlib import Path

# ======================= network


import pygbag.aio as asyncio

if aio.cross.simulator:
    sys.path.append(str(Path(aio.__file__).parent.parent.parent))

print("   ================ PygBag utilities loaded ================== ")


def host():
    global proxy
    print("serving sockv5 ...")

    from asyncio_socks_server.values import SocksAuthMethod
    from asyncio_socks_server.config import Config
    from asyncio_socks_server.proxyman import ProxyMan

    cfg = Config()

    cfg.update_config(
        {
            "LISTEN_HOST": "127.0.0.1",
            "LISTEN_PORT": 8001,
            "AUTH_METHOD": SocksAuthMethod.NO_AUTH,
            "ACCESS_LOG": False,
            "STRICT": False,
            "DEBUG": False,
            "USERS": {},
        }
    )

    proxy = ProxyMan(cfg)
    aio.create_task(proxy.start_server())


host()


async def connect():
    import aiohttp
    from aiohttp_socks import ProxyType, ProxyConnector, ChainProxyConnector

    async def fetch(url):
        connector = ProxyConnector.from_url("socks5://user:password@127.0.0.1:8001")
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(url) as response:
                return await response.text()

    print(await fetch("https://example.com/"))


# await connect()

if __name__ == "__main__":

    async def main():
        asyncio.run(main())
