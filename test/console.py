import os, sys
os.chdir(os.path.dirname(__file__))

import traceback

import test_repo
from readme_compiler import stdout
from readme_compiler import describe

_module = describe.module(test_repo)

while (True):
    try:
        _command = input(">>> ")

        _result = None
        exec("_result = "+_command, globals(), locals())

        if (_result is not None): print (stdout.green(_result))

    except KeyboardInterrupt as e:
        break

    except Exception as e:
        print (stdout.red(traceback.format_exc()))


print ("Done.")