import os, sys

import dataclasses
import re
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type, Union

from .. import bin
from .. import settings
from ..settings.enums import RenderPurpose
from .. import fetchers
from .. import exceptions

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

    parent:Any = dataclasses.field(default=None, hash=False, compare=True)
    
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

    @property
    def url(self)->str:
        return f'https://{self.hook_parsed["domain"]}/{self.owner}/{self.repo}'
    
    @property
    def clone_comannd(self)->str:
        return f"git clone --branch {self.branch} {self.hook}"

    @property
    def branch_escaped(self)->str:
        _branch = self.branch.lower()

        _branch = re.sub(
            r"[^a-z0-9]",
            "_",
            _branch,
        )

        return _branch

    @property
    def branch_description_path(self)->str:
        if (not hasattr(self.parent, "settings")):
            raise ValueError(f"Orphaned {type(self).__name__} having no RepositoryDirectory parent cannot use `branch_description_path`.")

        else:
            return os.path.join(
                self.path,
                self.parent.settings.paths.folder.source,
                settings.README_BRANCH_DESCRIPTION_TEMPLATE.format(
                    branch = self.branch_escaped
                ),
            )

    @property
    def branch_description(self)->str:
        if (not hasattr(self.parent, "render")):
            raise ValueError(f"Orphaned {type(self).__name__} having no RepositoryDirectory parent cannot use `branch_description`.")

        else:
            try:
                return self.parent.render(
                    self.branch_description_path,
                    purpose=RenderPurpose.EMBED,
                )
            except FileNotFoundError as e:
                return "(No branch information available.)"
    
    @classmethod
    def from_path(
        cls:Type["GitProperties"],
        path:str = "./",
        *,
        parent:Any = None,
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

            if (isinstance(_branch, exceptions.ShellReturnError)):
                if (_branch.returncode == 128):
                    # This means a remote branch had not been setup;
                    # this repo is probably local at this point.
                    # This will not happen after the first commit.
                    # 
                    # <CalledProcessError> occured during call of ['git', 'rev-parse', '--abbrev-ref', 'HEAD']: Command '['git', 'rev-parse', '--abbrev-ref', 'HEAD']' returned non-zero exit status 128. 
                    _branch =   "main"

            _path           =   fetchers.shell_output([ "git",
                                                        "rev-parse",
                                                        "--show-toplevel"])

            return cls(
                hook    = _hook,
                branch  = _branch,
                path    = _path,
                parent  = parent,
            )

    def add(
        self:"GitProperties",
        path:str,
    )->bool:
        """
        Use `git add` to add target to the repo.
        """
        with WorkingDirectory(path=self.path) as cwd:
            _return = fetchers.shell_output([   "git",
                                                "add",
                                                path])

        return not _return