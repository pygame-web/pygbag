plan = []


def register(func, *args, **kwargs):
    global plan
    plan.append(
        (
            func,
            arg,
            kwargs,
        )
    )


def unregister(func):
    global plan
    todel = []
    for i, elem in enumerate(plan):
        if elem[0] is func:
            todel.append(i)

    while len(todel):
        plan.pop(todel.pop())


def exiting():
    global plan
    while len(plan):
        f, argv, kw = plan.pop()
        f(argv, kw)


# replace stock one
import sys

sys.modules["atexit"] = sys.modules["aio.atexit"]
