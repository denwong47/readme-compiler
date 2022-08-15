import os, sys
os.chdir(os.path.dirname(__file__))

import importlib
import traceback

import test_repo
import readme_compiler
from readme_compiler import stdout

_module = None
while (True):
    if (not _module): _module = readme_compiler.describe.module(test_repo)

    try:

        _command = input(">>> ")

        if (_command.strip()):
            _result = None
            
            if (not any(
                map(
                    lambda _word:_command.startswith(_word),
                    (
                        "from",
                        "import",
                        "assert",
                    )
                )
            )):
                _command = "_result = "+_command

            exec(_command, globals(), locals())

            if (_result is not None): print (stdout.green(_result))
        
        else:
            print(stdout.blue("Reloading modules..."))
            
            importlib.reload(readme_compiler)
            importlib.reload(stdout)
            importlib.reload(test_repo)

            _module = None

    except KeyboardInterrupt as e:
        break

    except Exception as e:
        print (stdout.red(traceback.format_exc()))


print ("Done.")