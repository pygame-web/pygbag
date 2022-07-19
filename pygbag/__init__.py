__version__ = "0.1.2"

try:
    sched_yield
except:
    __import__("builtins").sched_yield = lambda : None
