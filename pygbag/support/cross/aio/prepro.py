import builtins

DEBUG = False

defines = {}


def defined(plat):
    try:
        return eval(plat) or True
    except:
        return False


def define(tag, value):
    global defines, DEBUG
    if DEBUG:
        import inspect

        lf = inspect.currentframe().f_back
        fn = inspect.getframeinfo(lf).filename.rsplit("/assets/", 1)[-1]
        ln = lf.f_lineno
        info = f"{fn}:{ln}"
        defines.setdefault(tag, info)
    else:
        info = "?:?"

    redef = defined(tag)
    if redef:
        if redef is value:
            pdb(f"INFO: {tag} redefined from {defines.get(tag)} at {info}")
            pass
        else:
            pdb(
                f"""\
WARNING: {tag} was already defined
    previous {defines.get(tag)} value {redef}
    new {info} value {value}

"""
            )

    setattr(builtins, tag, value)


builtins.define = define
builtins.defined = defined
