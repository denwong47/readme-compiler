import os, sys

import dataclasses
import re
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type, Union

from .. import bin
from .. import settings
from .. import fetchers

from .cwd import WorkingDirectory

PATTERN_HOOK    =   re.compile(r"^(?P<schema>\w+)://(?P<domain>[^/]+)/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$")

@dataclasses.dataclass(init=True, repr=True)
class GitProperties():
    """
    Dataclass to read `git` properties from a directory.
    Use classmethod `from_path()`.
    """
    hook:str
    branch:str
    path:str
    
    @property
    def hook_parsed(self)->Dict[str, str]:
        return fetchers.regex_output(
            source=self.hook, 
            pattern=PATTERN_HOOK,
        )

    @property
    def owner(self)->str:
        return self.hook_parsed["owner"]

    @property
    def repo(self)->str:
        return os.path.basename(self.path)

    @classmethod
    def from_path(
        cls:"GitProperties",
        path:str = "./",
    )->"GitProperties":

        with WorkingDirectory(path=path) as cwd:
            _hook           =   fetchers.shell_output([ "git",
                                                    "config",
                                                    "--get",
                                                    "remote.origin.url"])

            _branch         =   fetchers.shell_output([ "git",
                                                        "rev-parse",
                                                        "--abbrev-ref",
                                                        "HEAD"])

            _path           =   fetchers.shell_output([ "git",
                                                        "rev-parse",
                                                        "--show-toplevel"])

            return cls(
                hook    = _hook,
                branch  = _branch,
                path    = _path,
            )
            