import os, sys

from types import TracebackType
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type, Union

class WorkingDirectory():
    """
    Temporarily change the working directory, and reset it upon existing context
    """
    
    cached_cwds = []

    def __init__(
        self,
        path:str="./",
    )->None:
        self.cached_cwds = []

        if (os.path.isdir(path)):
            path = os.path.abspath(path)

            self.path = path
        else:
            raise ValueError(f"{repr(path)} is not a valid, existing directory.")
        
    def __enter__(self)->"WorkingDirectory":
        self.cached_cwds.append(
            os.path.abspath(os.path.curdir)
        )
        
        os.chdir(self.path)

    def __exit__(
        self,
        exception_type:Type[BaseException]  = None,
        exception_message:BaseException     = None,
        exception_traceback:TracebackType   = None,
    )->bool:
        if (self.cached_cwds):
            os.chdir(
                self.cached_cwds.pop(-1)
            )

        return False