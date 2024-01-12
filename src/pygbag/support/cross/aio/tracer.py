STEP_INTO = False


def on():
    global STEP_INTO
    STEP_INTO = True


def off():
    global STEP_INTO
    STEP_INTO = False


def lines(frame, event, arg):
    if event != "line":
        return
    co = frame.f_code
    func_name = co.co_name
    line_no = frame.f_lineno
    filename = co.co_filename
    print(f"  {func_name} line {line_no}")


def calls(frame, event, arg):
    global STEP_INTO

    if event != "call":
        return

    co = frame.f_code
    func_name = co.co_name
    if func_name in ("write", "raw_input", "process"):
        return
    func_line_no = frame.f_lineno
    func_filename = co.co_filename

    if func_filename.startswith("/usr/lib/python3."):
        return

    if func_filename.find("/aio/") > 0:
        return

    caller = frame.f_back
    if caller:
        caller_line_no = caller.f_lineno
        caller_filename = caller.f_code.co_filename
        if caller_filename != func_filename:
            print(
                "%s() on line %s of %s from line %s of %s"
                % (
                    func_name,
                    func_line_no,
                    func_filename,
                    caller_line_no,
                    caller_filename,
                )
            )
        else:
            print(f"{func_name} {func_filename}:{caller_line_no}->{func_line_no}")

    if STEP_INTO:
        return lines
    return


"""

def trace_calls_and_returns(frame, event, arg):
    co = frame.f_code
    func_name = co.co_name
    if func_name == 'write':
        # Ignore write() calls from print statements
        return
    line_no = frame.f_lineno
    filename = co.co_filename
    if event == 'call':
        print 'Call to %s on line %s of %s' % (func_name, line_no, filename)
        return trace_calls_and_returns
    elif event == 'return':
        print '%s => %s' % (func_name, arg)
    return


"""
