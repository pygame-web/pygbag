import token_utils

import uuid


def generate_variable_names():
    """Generator that yields random variable names"""
    while True:
        name = uuid.uuid4()
        yield f"_{name.hex}"


def generate_predictable_names():
    """Generator that yields predictable variable names - useful for testing"""
    index = 0
    while True:
        index += 1
        yield f"_{index}"


def transform_source(source: str) -> str:
    src = transform_source_nobreak(source)
    src = transform_source_repeat(src)
    src = transform_source_switch(src)
    src = transform_source_sched_yield(src)
    return src


def transform_file(filename: str):
    with open("extended_syntax.py", "r") as sourcefile:
        return transform_source(sourcefile.read())


# =============================================================================


def transform_source_nobreak(source, **_kwargs):
    """``nobreak`` is replaced by ``else`` only if it is the first
    non-space token on a line and if its indentation matches
    that of a ``for`` or ``while`` block.
    """
    indentations = {}
    lines = token_utils.get_lines(source)
    new_tokens = []
    # The following is not a proper parser, but it should work
    # well enough in most cases, for well-formatted code.
    for line in lines:
        first = token_utils.get_first(line)
        if first is None:
            new_tokens.extend(line)
            continue
        if first == "nobreak":
            if first.start_col in indentations:
                if indentations[first.start_col] in ["for", "while"]:
                    first.string = "else"
                    del indentations[first.start_col]
        indentations[first.start_col] = first.string
        new_tokens.extend(line)

    return token_utils.untokenize(new_tokens)


# =============================================================================


class RepeatSyntaxError(Exception):
    """Currently, only raised when a repeat statement has a missing colon."""

    pass


def transform_source_repeat(source, callback_params=None, **_kwargs):
    """This function is called by the import hook loader and is used as a
    wrapper for the function where the real transformation is performed.

    It can use an optional parameter, ``callback_params``, which is
    a dict that can contain a key, ``"predictable_names"``, to indicate
    that variables created as loop counters should take a predictable form.
    """
    """Replaces instances of::

        repeat forever: -> while True:
        repeat while condition: -> while  condition:
        repeat until condition: -> while not condition:
        repeat n: -> for _uid in range(n):

    A complete repeat statement is restricted to be on a single line ending
    with a colon (optionally followed by a comment). If the colon is
    missing, a ``RepeatSyntaxError`` is raised.
    """
    if callback_params is None or "predictable_names" not in callback_params:
        predictable_names = False
    else:
        predictable_names = callback_params["predictable_names"]
    new_tokens = []
    if predictable_names:
        variable_name = generate_predictable_names()
    else:
        variable_name = generate_variable_names()

    for tokens in token_utils.get_lines(source):
        # a line of tokens can start with INDENT or DEDENT tokens ...
        first_token = token_utils.get_first(tokens)
        if first_token == "repeat":
            last_token = token_utils.get_last(tokens)
            if last_token != ":":
                raise RepeatSyntaxError(
                    "Missing colon for repeat statement on line "
                    + f"{first_token.start_row}\n    {first_token.line}."
                )

            repeat_index = token_utils.get_first_index(tokens)
            second_token = tokens[repeat_index + 1]
            if second_token == "forever":
                first_token.string = "while"
                second_token.string = "True"
            elif second_token == "while":
                first_token.string = "while"
                second_token.string = ""
            elif second_token == "until":
                first_token.string = "while"
                second_token.string = "not"
            else:
                first_token.string = "for %s in range(" % next(variable_name)
                last_token.string = "):"

        new_tokens.extend(tokens)

    return token_utils.untokenize(new_tokens)


# =============================================================================


def transform_source_switch(source, callback_params=None, **_kwargs):
    """Replaces code like::

        switch EXPR:
            case EXPR_1:
                SUITE
            case EXPR_2:
                SUITE
            case in EXPR_3, EXPR_4, ...:
                SUITE
            ...
            else:
                SUITE

    by::

        var_name = EXPR
        if var_name == EXPR_1:
                SUITE
        elif var_name == EXPR_2:
                SUITE
        elif var_name in EXPR_3, EXPR_4, ...:
                SUITE
        else:
                SUITE
        del var_name

    Limitation: switch blocks cannot be part of a SUITE of another switch block.
    """
    if callback_params is None or "predictable_names" not in callback_params:
        predictable_names = False
    else:
        predictable_names = callback_params["predictable_names"]
    new_tokens = []
    switch_block = False
    first_case = False
    if predictable_names:
        variable_name = generate_predictable_names()
    else:
        variable_name = generate_variable_names()

    for line in token_utils.get_lines(source):
        first_token = token_utils.get_first(line)
        if first_token is None:
            new_tokens.extend(line)
            continue

        if len(line) > 1:
            _index = token_utils.get_first_index(line)
            second_token = line[_index + 1]
        else:
            second_token = None

        if not switch_block:
            if first_token == "switch":
                switch_indent = first_token.start_col
                var_name = next(variable_name)
                first_token.string = f"{var_name} ="
                switch_block = True
                first_case = True
                colon = token_utils.get_last(line)
                colon.string = ""
        else:
            if first_token.start_col == switch_indent:
                switch_block = False
                new_tokens.extend([" " * switch_indent + f"del {var_name}\n"])

            elif first_token == "case" or first_token == "else":
                if first_case and first_token == "case":
                    if second_token == "in":
                        first_token.string = f"if {var_name}"
                    else:
                        first_token.string = f"if {var_name} =="
                    first_case = False
                elif first_token == "case":
                    if second_token == "in":
                        first_token.string = f"elif {var_name}"
                    else:
                        first_token.string = f"elif {var_name} =="
                dedent = first_token.start_col - switch_indent
                line = token_utils.dedent(line, dedent)

        new_tokens.extend(line)
    return token_utils.untokenize(new_tokens)


# =============================================================================


def transform_source_sched_yield(source, **_kwargs):
    """This performs a simple replacement of ``function`` by ``lambda``."""
    new_tokens = []
    skip = 0
    for token in token_utils.tokenize(source):
        skip_now = False
        if skip > 0:
            skip_now = True
            skip -= 1

        # token_utils allows us to easily replace the string content
        # of any token
        if token == "sched_yield":
            token.string = "if aio.sched_yield():await asyncio.sleep(0)"
            skip = 2

        if skip_now:
            print("skipped", token)
            token.string = ""

        new_tokens.append(token)

    return token_utils.untokenize(new_tokens)
