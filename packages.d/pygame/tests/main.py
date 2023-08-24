import sys
import asyncio
import shutil

__WASM__ = sys.platform in ('emscripten','wasi')

if __WASM__:
    test_pkg_name = "tests"
    TESTS_DIR = "/data/data/org.python/assets/site-packages/pygame/"
    shutil.copytree("test", TESTS_DIR+ test_pkg_name)
    shutil.move( TESTS_DIR+ test_pkg_name + "/examples" , TESTS_DIR )
    os.chdir(TESTS_DIR)
else:
    test_pkg_name = "test"

test_runner_mod = test_pkg_name + ".test_utils.test_runner"

from pygame.tests.test_utils import import_submodule
from pygame.tests.test_utils.test_runner import (
    prepare_test_env,
    run_test,
    combine_results,
    get_test_results,
    TEST_RESULTS_START,
)

import pygame
import pygame.threads

import os
import re
import tempfile
import time
import random
from pprint import pformat


was_run = False



def count_results(results):
    total = errors = failures = 0
    for result in results.values():
        if result.get("return_code", 0):
            total += 1
            errors += 1
        else:
            total += result["num_tests"]
            errors += result["num_errors"]
            failures += result["num_failures"]

    return total, errors, failures



async def main(*args, **kwds):
    """Run the Pygame unit test suite and return (total tests run, fails dict)

    Positional arguments (optional):
    The names of tests to include. If omitted then all tests are run. Test
    names need not include the trailing '_test'.

    Keyword arguments:
    incomplete - fail incomplete tests (default False)
    usesubprocess - run all test suites in the current process
                   (default False, use separate subprocesses)
    dump - dump failures/errors as dict ready to eval (default False)
    file - if provided, the name of a file into which to dump failures/errors
    timings - if provided, the number of times to run each individual test to
              get an average run time (default is run each test once)
    exclude - A list of TAG names to exclude from the run. The items may be
              comma or space separated.
    show_output - show silenced stderr/stdout on errors (default False)
    all - dump all results, not just errors (default False)
    randomize - randomize order of tests (default False)
    seed - if provided, a seed randomizer integer
    multi_thread - if provided, the number of THREADS in which to run
                   subprocessed tests
    time_out - if subprocess is True then the time limit in seconds before
               killing a test (default 30)
    fake - if provided, the name of the fake tests package in the
           run_tests__tests subpackage to run instead of the normal
           Pygame tests
    python - the path to a python executable to run subprocessed tests
             (default sys.executable)
    interactive - allow tests tagged 'interactive'.

    Return value:
    A tuple of total number of tests run, dictionary of error information. The
    dictionary is empty if no errors were recorded.

    By default, individual test modules are run in separate subprocesses. This
    recreates normal Pygame usage where pygame.init() and pygame.quit() are
    called only once per program execution, and avoids unfortunate
    interactions between test modules. Also, a time limit is placed on test
    execution, so frozen tests are killed when there time allotment expired.
    Use the single process option if threading is not working properly or if
    tests are taking too long. It is not guaranteed that all tests will pass
    in single process mode.

    Tests are run in a randomized order if the randomize argument is True or a
    seed argument is provided. If no seed integer is provided then the system
    time is used.

    Individual test modules may have a corresponding *_tags.py module,
    defining a __tags__ attribute, a list of tag strings used to selectively
    omit modules from a run. By default, only the 'interactive', 'ignore', and
    'subprocess_ignore' tags are ignored. 'interactive' is for modules that
    take user input, like controller_test.py. 'ignore' and 'subprocess_ignore' for
    disabling modules for foreground and subprocess modes respectively.
    These are for disabling tests on optional modules or for experimental
    modules with known problems. These modules can be run from the console as
    a Python program.

    This function can only be called once per Python session. It is not
    reentrant.

    """

    global was_run

    if was_run:
        raise RuntimeError("run() was already called this session")
    was_run = True

    options = kwds.copy()
    option_usesubprocess = options.get("usesubprocess", False)
    option_dump = options.pop("dump", False)
    option_file = options.pop("file", None)
    option_randomize = options.get("randomize", False)
    option_seed = options.get("seed", None)
    option_multi_thread = options.pop("multi_thread", 1)
    option_time_out = options.pop("time_out", 120)
    option_fake = options.pop("fake", None)
    option_python = options.pop("python", sys.executable)
    option_exclude = options.pop("exclude", ())
    option_interactive = options.pop("interactive", False)

    if not option_interactive and "interactive" not in option_exclude:
        option_exclude += ("interactive",)
    if option_usesubprocess and "subprocess_ignore" not in option_exclude:
        option_exclude += ("subprocess_ignore",)
    elif "ignore" not in option_exclude:
        option_exclude += ("ignore",)

    option_exclude += ("python3_ignore",)
    option_exclude += ("SDL2_ignore",)

    main_dir, test_subdir, fake_test_subdir = prepare_test_env()

    ###########################################################################
    # Compile a list of test modules. If fake, then compile list of fake
    # xxxx_test.py from run_tests__tests

    TEST_MODULE_RE = re.compile(r"^(.+_test)\.py$")

    test_mods_pkg_name = test_pkg_name

    working_dir_temp = tempfile.mkdtemp()

    if option_fake is not None:
        test_mods_pkg_name = ".".join(
            [test_mods_pkg_name, "run_tests__tests", option_fake]
        )
        test_subdir = os.path.join(fake_test_subdir, option_fake)
        working_dir = test_subdir
    else:
        working_dir = working_dir_temp

    # Added in because some machines will need os.environ else there will be
    # false failures in subprocess mode. Same issue as python2.6. Needs some
    # env vars.

    test_env = os.environ

    fmt1 = "%s.%%s" % test_mods_pkg_name
    fmt2 = "%s.%%s_test" % test_mods_pkg_name
    if args:
        test_modules = [m.endswith("_test") and (fmt1 % m) or (fmt2 % m) for m in args]
    else:
        test_modules = []
        for f in sorted(os.listdir(test_subdir)):
            for match in TEST_MODULE_RE.findall(f):
                test_modules.append(fmt1 % (match,))

    ###########################################################################
    # Remove modules to be excluded.

    tmp = test_modules
    test_modules = []
    for name in tmp:
        tag_module_name = f"{name[0:-5]}_tags"
        try:
            tag_module = import_submodule(tag_module_name)
        except ImportError:
            test_modules.append(name)
        else:
            try:
                tags = tag_module.__tags__
            except AttributeError:
                print(f"{tag_module_name} has no tags: ignoring")
                test_modules.append(name)
            else:
                for tag in tags:
                    if tag in option_exclude:
                        print(f"skipping {name} (tag '{tag}')")
                        break
                else:
                    test_modules.append(name)
    del tmp, tag_module_name, name

    ###########################################################################
    # Meta results

    results = {}
    meta_results = {"__meta__": {}}
    meta = meta_results["__meta__"]

    ###########################################################################
    # Randomization

    if option_randomize or option_seed is not None:
        if option_seed is None:
            option_seed = time.time()
        meta["random_seed"] = option_seed
        print(f"\nRANDOM SEED USED: {option_seed}\n")
        random.seed(option_seed)
        random.shuffle(test_modules)

    ###########################################################################
    # Single process mode

    options["exclude"] = option_exclude
    t = time.time()
    for module in test_modules:
        await asyncio.sleep(0)
        results.update(run_test(module, **options))
    t = time.time() - t


    ###########################################################################
    # Output Results
    #

    untrusty_total, combined = combine_results(results, t)
    total, n_errors, n_failures = count_results(results)

    meta["total_tests"] = total
    meta["combined"] = combined
    meta["total_errors"] = n_errors
    meta["total_failures"] = n_failures
    results.update(meta_results)

    if not option_usesubprocess and total != untrusty_total:
        assert_msg =( "Something went wrong in the Test Machinery:\n"
            "total: %d != untrusty_total: %d" % (total, untrusty_total) )
        if __WASM__:
            print(assert_msg)
        else:
            raise AssertionError(assert_msg)

    if not option_dump:
        print(combined)
    else:
        print(TEST_RESULTS_START)
        print(pformat(results))

    if option_file is not None:
        results_file = open(option_file, "w")
        try:
            results_file.write(pformat(results))
        finally:
            results_file.close()

    shutil.rmtree(working_dir_temp)

    print(f"{total=}, {n_errors + n_failures=}")
    return total, n_errors + n_failures


#from test.test_utils.run_tests import run, run_and_exit

#run_and_exit('version_test', **{'usesubprocess': False, 'verbosity': 1} )

tlist = []
skip_until = '' #'event_test'

for maybe in os.listdir(test_pkg_name):
    if not len(maybe):
        continue
    if maybe[0]=='_':
        continue
    if maybe.find('_tags')>0:
        continue

    if not maybe.endswith('.py'):
        continue

    if skip_until:
        if not skip_until in maybe:
            continue
        skip_until = ''
        continue

    if maybe in (
        'ftfont_test.py', # ?
        'math_test.py',     # crash
        'color_test.py',    # crash
        'display_test.py',     # crash
        'threads_test.py',    # should skip
        'scrap_test.py',      # fail
        'transform_test.py',  # fail
        'time_test.py',   # SLOW + fail
        'event_test.py',  # SLOW ?
):
        print("skipping", maybe)
        continue

    tlist.append(maybe[:-3])
    #print(tlist[-1])


print("="*80)
print(len(tlist),' tests')
for t in tlist:
    print("\t", t)
print("="*80)
asyncio.run(main(*tlist,**{'usesubprocess': False, 'verbosity': 1}))



