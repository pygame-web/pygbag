# https://emscripten.org/docs/porting/networking.html
# idea : Katie Bell ( https://github.com/katharosada ) on WebAssembly/Python discord


# possible client part : https://github.com/Anorov/PySocks
# this code : Han You : https://github.com/sqd/pysocks5-async


import asyncio
import errno
import ipaddress
import logging
import sys

logging.basicConfig(level=logging.INFO)
from typing import Union

_BUF_LEN = 64

_ACCEPTED_VERSION = b"\x05"
_NO_AUTH = b"\x00"

_NO_SUPPORTED_AUTH_RESP = b"\x05\xff"
_USE_NO_AUTH_RESP = b"\x05\x00"


def _status_code_resp(code):
    return b"\x05" + code + b"\x00\x01\x00\x00\x00\x00\x00\x00"


_GENERAL_FAILURE_RESP = _status_code_resp(b"\x01")
_NOT_SUPPORTED_CMD_RESP = _status_code_resp(b"\x07")
_NOT_SUPPORTED_ADDR_RESP = _status_code_resp(b"\x08")

_ADDR_TYPE_IPV4 = b"\x01"
_ADDR_TYPE_DOMAIN = b"\x03"
_ADDR_TYPE_IPV6 = b"\x04"
_ACCEPTED_ADDR_TYPES = (_ADDR_TYPE_IPV4, _ADDR_TYPE_DOMAIN, _ADDR_TYPE_IPV6)

_CMD_TCP_OPEN = b"\x01"
_CMD_TCP_BIND = b"\x02"
_CMD_UDP_ASSOC = b"\x03"
_ACCEPTED_CMDS = (_CMD_TCP_OPEN, _CMD_TCP_BIND, _CMD_UDP_ASSOC)


class SOCKS5Server:
    def __init__(self, host, port, handler_cls):
        self.host = host
        self.port = port
        self.handler_cls = handler_cls

    async def start_server(self):
        logging.info("Start listening at %s:%s", self.host, self.port)
        await asyncio.start_server(self._handle_conn, host=self.host, port=self.port)

    async def _handle_conn(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        def close_conn(resp):
            writer.write(resp)
            writer.close()

        version = await reader.read(1)
        if version != _ACCEPTED_VERSION:
            return close_conn(_GENERAL_FAILURE_RESP)

        n_methods = (await reader.read(1))[0]
        auth_methods = await reader.read(n_methods)
        if _NO_AUTH not in auth_methods:
            return close_conn(_NO_SUPPORTED_AUTH_RESP)
        else:
            writer.write(_USE_NO_AUTH_RESP)

        try:
            version = await reader.read(1)
            if version != _ACCEPTED_VERSION:
                return close_conn(_GENERAL_FAILURE_RESP)

            cmd = await reader.read(1)
            if cmd not in _ACCEPTED_CMDS:
                return close_conn(_NOT_SUPPORTED_CMD_RESP)

            reserve_zero = await reader.read(1)
            if reserve_zero != b"\x00":
                return close_conn(_GENERAL_FAILURE_RESP)

            addr_type = await reader.read(1)
            if addr_type not in _ACCEPTED_ADDR_TYPES:
                return close_conn(_NOT_SUPPORTED_ADDR_RESP)

            if addr_type == _ADDR_TYPE_IPV4:
                host = ipaddress.IPv4Address((await reader.read(4)))
            elif addr_type == _ADDR_TYPE_DOMAIN:
                domain_len = (await reader.read(1))[0]
                host = (await reader.read(domain_len)).decode("ascii")
            elif addr_type == _ADDR_TYPE_IPV6:
                host = ipaddress.IPv6Address((await reader.read(16)))

            port = int.from_bytes((await reader.read(2)), "big")

            handler: BaseSOCKS5Handler = self.handler_cls(reader, writer, host, port)
        except ConnectionError:
            return close_conn(_GENERAL_FAILURE_RESP)

        if cmd == _CMD_TCP_OPEN:
            await handler.do_TCP_open()
        elif cmd == _CMD_TCP_BIND:
            await handler.do_TCP_bind()
        elif cmd == _CMD_UDP_ASSOC:
            await handler.do_UDP_assoc()


class SOCKS5Status:
    OK = b"\x00"
    GENERAL_FAILURE = b"\x01"
    NOT_ALLOWED = b"\x02"
    NETWORK_UNREACHABLE = b"\x03"
    HOST_UNREACHABLE = b"\x04"
    CONN_REFUSED = b"\x05"
    TTL_EXPIRED = b"\x06"
    PROTO_ERR = b"\x07"
    ADDR_NOT_SUPPORTED = b"\x08"


class BaseSOCKS5Handler:
    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        host: Union[str, ipaddress.IPv4Address, ipaddress.IPv6Address],
        port: int,
    ):
        self.client_reader = reader
        self.client_writer = writer
        self.dest_host = host
        self.dest_port = port
        self.client_host, self.client_port = writer.get_extra_info("peername")

    def dest_host_str(self):
        if isinstance(self.dest_host, (ipaddress.IPv4Address, ipaddress.IPv6Address)):
            return self.dest_host.exploded
        elif isinstance(self.dest_host, str):
            return self.dest_host

    async def do_TCP_open(self):
        pass

    async def do_TCP_bind(self):
        pass

    async def do_UDP_assoc(self):
        pass

    def response_status(self, status):
        resp = b"\x05"
        resp += status
        resp += b"\x00"
        if isinstance(self.dest_host, ipaddress.IPv4Address):
            resp += b"\x01" + self.dest_host.packed
        elif isinstance(self.dest_host, str):
            resp += b"\x03" + len(self.dest_host).to_bytes(1, "big") + self.dest_host.encode("ascii")
        elif isinstance(self.dest_host, ipaddress.IPv6Address):
            resp += b"\x04" + self.dest_host.packed
        resp += self.dest_port.to_bytes(2, "big")
        self.client_writer.write(resp)

    def close(self):
        self.client_writer.close()


class SimpleSOCKS5Handler(BaseSOCKS5Handler):
    async def do_TCP_open(self):
        logging.info(
            "TCP OPEN %s:%s -> %s:%s",
            self.client_host,
            self.client_port,
            self.dest_host_str(),
            self.dest_port,
        )
        self.response_status(SOCKS5Status.OK)
        try:
            server_reader, server_writer = await asyncio.open_connection(self.dest_host_str(), self.dest_port)
        except ConnectionRefusedError:
            self.response_status(SOCKS5Status.CONN_REFUSED)
            return self.close()
        except TimeoutError:
            self.response_status(SOCKS5Status.GENERAL_FAILURE)
            return self.close()
        except OSError as e:
            status = {
                errno.ENETUNREACH: SOCKS5Status.NETWORK_UNREACHABLE,
                errno.EHOSTUNREACH: SOCKS5Status.HOST_UNREACHABLE,
            }.get(e.errno, SOCKS5Status.GENERAL_FAILURE)
            self.response_status(status)
            return self.close()
        await SimpleSOCKS5Handler._bridge(self.client_reader, self.client_writer, server_reader, server_writer)

    async def do_TCP_bind(self):
        async def on_conn(server_reader: asyncio.StreamReader, server_writer: asyncio.StreamWriter):
            await self._bridge(self.client_reader, self.client_writer, server_reader, server_writer)
            srv.close()
            logging.info(
                "TCP UNBOUND %s:%s == %s:%s",
                self.client_host,
                self.client_port,
                self.dest_host_str(),
                self.dest_port,
            )

        logging.info(
            "TCP BIND %s:%s == %s:%s",
            self.client_host,
            self.client_port,
            self.dest_host_str(),
            self.dest_port,
        )
        try:
            srv = await asyncio.start_server(on_conn, self.dest_host_str(), self.dest_port)
            self.dest_host, self.dest_port = srv.sockets[0].getsockname()
            logging.info(
                "TCP BOUND %s:%s == %s:%s",
                self.client_host,
                self.client_port,
                self.dest_host_str(),
                self.dest_port,
            )
            self.response_status(SOCKS5Status.OK)
        except OSError as e:
            self.response_status(SOCKS5Status.GENERAL_FAILURE)
            self.close()

    async def do_UDP_assoc(self):
        class UDPClientProto(asyncio.DatagramProtocol):
            handler = self

            def datagram_received(self, data, addr):
                UDPClientProto.handler.client_writer.write(data)

        logging.info(
            "UDP ASOC %s:%s == %s:%s",
            self.client_host,
            self.client_port,
            self.dest_host_str(),
            self.dest_port,
        )

        transport: asyncio.DatagramTransport
        proto: asyncio.DatagramProtocol
        (transport, proto) = await asyncio.get_running_loop().create_datagram_endpoint(
            UDPClientProto, remote_addr=(self.dest_host_str(), self.dest_port)
        )
        self.dest_host, self.dest_port = transport.get_extra_info("sockname")
        self.response_status(SOCKS5Status.OK)

        try:
            await self.client_reader.read()
        except:
            pass
        finally:
            transport.close()

    @staticmethod
    async def _bridge(
        active_reader: asyncio.StreamReader,
        active_writer: asyncio.StreamWriter,
        passive_reader: asyncio.StreamReader,
        passive_writer: asyncio.StreamWriter,
    ):
        """
        Cut the passive reader/writer if the active ones disconnect.
        """

        async def pipe(
            from_: asyncio.StreamReader,
            to: asyncio.StreamWriter,
            cut: asyncio.StreamWriter,
        ):
            try:
                buf = await from_.read(_BUF_LEN)
                while buf:
                    to.write(buf)
                    buf = await from_.read(_BUF_LEN)
            except ConnectionResetError:
                if cut:
                    cut.close()
            finally:
                to.close()

        t1 = asyncio.create_task(pipe(active_reader, passive_writer, passive_writer))
        t2 = asyncio.create_task(pipe(passive_reader, active_writer, None))
        await asyncio.gather(t1, t2)


if __name__ == "__main__":
    try:
        port = int(sys.argv[1])
    except (IndexError, ValueError):
        print(f"Usage: {sys.argv[0]} [port]")
        print("Han You (me@hanyou.dev) 2019")
        sys.exit(1)
    socks5d = SOCKS5Server("localhost", port, SimpleSOCKS5Handler)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(socks5d.start_server())
    loop.run_forever()
