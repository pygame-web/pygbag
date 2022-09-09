import sys
import io
import socket
socket.setdefaulttimeout(0.0)

import aio



async def aio_sock_open(sock,host,port):
    while True:
        try:
            sock.connect( (host,port,) )
        except BlockingIOError:
            await aio.sleep(0)
        except OSError as e:
            # 30 emsdk, 106 linux
            if e.errno in (30,106):
                return sock
            sys.print_exception(e)



class open:

    def __init__(self,url, mode, tmout):
        self.host, port = url.rsplit(':',1)
        self.port = int(port)
        if __WASM__ and __import__('platform').is_browser:
            if not url.startswith('ws'):
                pdb(f"switching to {self.port}+20000 as websocket")
                self.port += 20000

        self.sock = socket.socket()
        #self.sock.setblocking(0)

# overload socket ?

    def fileno(self):
        return self.sock.fileno()

    def send(self,*argv,**kw):
        self.sock.send(*argv,**kw)

    def recv(self, *argv):
        return self.sock.recv(*argv)

# ============== specific ===========================

    async def __aenter__(self):
        # use async
        await aio_sock_open(self.sock, self.host, self.port)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        aio.protect.append(self)
        aio.defer(self.sock.close, (),{} )
        del self.port, self.host, self.sock

    def read(self, size=-1):
        return self.recv(0)


    def write(self, data):
        if isinstance(data, str):
            return self.sock.send(data.encode())
        return self.sock.send(data)

    def print(self,*argv,**kw):
        # use EOL
        #kw.setdefault("end","\r\n")
        kw['file']=io.StringIO(newline="\r\n")
        print(*argv,**kw)
        self.write( kw['file'].getvalue() )

    def  __enter__(url, mode, tmout):
        # use softrt (wapy)
        return aio.await_for( self.__aenter__())

    def __exit__(self, exc_type, exc, tb):
        #self.sock.close()
        pass
