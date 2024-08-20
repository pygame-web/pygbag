from transitions import Machine
from dataclasses import dataclass
import textwrap

index = {}


class State(object): ...


class Draft(object): ...


@dataclass
class FSM(Machine):
    states: tuple
    initial: str

    def __init__(self, *argv, **kw):
        Machine.__init__(self, states=self.states, initial=self.initial)


# TODO move the wrap out of there.


def state_refs(*argv):
    global index
    # tw = textwrap.TextWrapper(width=78)
    tw = None
    states = []
    maxchapters = len(argv)
    for chapter, component in enumerate(argv):
        source = component.script
        block = source.strip().split("\n", 1)[0]
        states.append(block)
        lines = []
        cmds = []
        for i, line in enumerate(source.split("\n")):
            if i:
                if line:
                    if line[0] != ":":
                        # markdown eats space at § begin
                        # line = line.replace('    ','\u2002\u2002')
                        if tw:
                            lines.extend(tw.wrap(line))
                        else:
                            lines.append(line)
                    else:
                        cmds.append(line[1:])
                else:
                    lines.append("")
        while len(lines) and not lines[-1]:
            lines.pop()
        lines.append("")
        lines.append("")
        lines.pop(0)
        index[block] = {
            "heading": f"Chapter {chapter+1}/{maxchapters} : {block}               ",
            "body": "\n".join(lines),
            "logic": cmds,
        }

    return tuple(states)


def build(pkg, **kw):
    global story
    steps = []

    for k, v in vars(pkg).items():
        if v in [State, Draft]:
            continue

        if isinstance(v, type):
            if issubclass(
                v,
                (
                    State,
                    Draft,
                ),
            ):
                print(k, v)
                steps.append(v)

    class Story(FSM):
        states: tuple = state_refs(*steps)
        initial: str = states[0]
        index = index

        def setup(self, pkg, **kw):
            global index
            self.name = kw.get("name", pkg.__name__)

            for state in self.states:
                store = index[state]
                store["choices"] = {}

                for cmd in store["logic"]:
                    if cmd.find(":") > 0:
                        rel, tail = cmd.split(":")
                        if rel == "?":
                            continue
                        if rel.find("->") >= 0:
                            trigger, dest = map(str.strip, rel.split("->", 1))
                            if trigger == "-":
                                trigger = dest
                            else:
                                if not trigger:
                                    trigger = dest
                                store["choices"][trigger] = tail

                            self.add_transition(trigger=trigger, source=state, dest=dest)
            return self

    story = Story()
    return story.setup(pkg, **kw)
