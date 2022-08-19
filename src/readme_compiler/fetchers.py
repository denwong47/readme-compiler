import abc
import re
import subprocess
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type, Union

import readme_compiler.exceptions as exceptions

from .log import logger


print = logger.debug


    

def shell_output(command:List[str])->str:
    try:    
        print(f"Calling {repr(command)}...")

        _return = subprocess.check_output(command)

        if (isinstance(_return, bytes)):
            _return = _return.decode("utf-8")
        
        if (isinstance(_return, str)):
            return _return.strip()
        else:
            # What is this???
            return _return

    except Exception as e:
        print (f"<{type(e).__name__}> occured during call of {repr(command)}: {e} ")
        
        if (isinstance(e, subprocess.CalledProcessError)):
            return exceptions.ShellReturnError(e)
        else:
            return exceptions.ShellRuntimeError(str(e))

def regex_output(
    source:str,
    pattern:re.Pattern,
)->Dict[str, str]:
    if (source and \
        (_match := pattern.match(source))):
        return _match.groupdict()
    else:
        # Return a complete collection of groups, but all None in values
        return {
            _group:None for _group in pattern.groupindex
        }