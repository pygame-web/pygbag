import sys
import aio

# import textwrap

# https://bugs.python.org/issue34616
# https://github.com/ipython/ipython/blob/320d21bf56804541b27deb488871e488eb96929f/IPython/core/interactiveshell.py#L121-L150

async_skeleton = """
#==========================================
async def retry_async_wrap():
    __snapshot = list( locals().keys() )
{}
    maybe_new = list( locals().keys() )
    while len(__snapshot):
        try:maybe_new.remove( __snapshot.pop() )
        except:pass
    maybe_new.remove('__snapshot')
    while len(maybe_new):
        new_one = maybe_new.pop(0)
        print(new_one , ':=', locals()[new_one])
        setattr(__import__('__main__'), new_one , locals()[new_one] )
#==========================================
"""


async def retry(code, sysinfo ):
    global may_have_value
    may_have_value = code.startswith('await ') # will display value
    try:
        code = 'builtins._ = {}'.format(code)
        code = async_skeleton.format(" " * 4 + code)
        bytecode = compile(code, "<asyncify>", "exec")
        #sys.stdout.write(f':async:  asyncify "[code stack rewritten]"\n')

        exec(bytecode, vars(__import__('__main__')), globals())
        await retry_async_wrap()

        # success ? clear all previous failures
        if may_have_value:
            if builtins._ is not None:
                sys.stdout.write('%r\n' % builtins._)



    except Exception as e:
        # FIXME: raise old exception
        sys.__excepthook__(*sysinfo)
        sys.stdout.write(f":async: can't use code : {e}\n~~> ")
        sys.print_exception(e)
    finally:
        #sys.ps1 = __ps1__
        aio.prompt_request()
