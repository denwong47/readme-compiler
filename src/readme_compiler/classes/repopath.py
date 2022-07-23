import os
import re

from types import SimpleNamespace

import readme_compiler.classes as classes
import readme_compiler.bin as bin

from .. import stdout

LINKS_PATTERN = re.compile(r"\[(?P<link_text>[^]]+)\]\((?P<link_href>[^\)\s]+)\)")


def resolve_repo_to_abspath(
    path:str,
    *,
    repo_root:str="./",
)->str:
    """
    Resolve root paths e.g. /README.md in repos into local paths, using the provided repo_root as reference.
    """
    if (path[0] == "/"):
        # Absolute path alert!
        path = os.path.join(
            repo_root,
            path[1:],
        )
    else:
        # Relative path Nothing to see here.
        pass

    return os.path.abspath(
        path
    )

class RepositoryPath():
    """
    A component of `RepositoryDirectory`, for manipulation of paths according to the repository root.
    """
    def __init__(
        self,
        repository:"classes.RepositoryDirectory",
    ) -> None:
        self.repository = repository

    @property
    def repository(
        self,
    )->"classes.RepositoryDirectory":
        return self._repository

    @repository.setter
    def repository(
        self,
        value:"classes.RepositoryDirectory",
    ):
        assert isinstance(value, classes.RepositoryDirectory), f"{type(self).__name__} requires repository of `RepositoryDirectory` type, but `{repr(value)}` found."
        
        self._repository = value
        
    @property
    def root(self):
        return self.repository.git.path

    def abspath(
        self,
        path:str,
    )->str:
        """
        Resolve root paths e.g. /README.md in repos into local paths, using the provided self.root as reference.
        """
        return resolve_repo_to_abspath(
            path,
            repo_root=self.root,
        )

    def rendered(
        self,
        path:str,
    )->str:
        """
        Change any repo path pointing to source index/folders to rendered equivalents.
        """
        _dest_url = path

        if (self.repository.settings.paths.folder.source in path.split("/")):
            # This is pointing to ./GIT_DIR/.readme/something.md
            _dest_url = path.replace(
                f"/{self.repository.settings.paths.folder.source}/", 
                f"/{self.repository.settings.paths.folder.rendered}/",
                1,
            )

        elif (self.repository.settings.paths.index.source in path.split("#")[0].split("/")):
            # This is pointing to ./GIT_DIR/.README.source.md
            _dest_url = path.replace(
                f"{self.repository.settings.paths.index.source}", 
                f"{self.repository.settings.paths.index.rendered}",
                1,
            )
            
        return _dest_url

    def parse(
        self,
        path:str,
    )->SimpleNamespace:
        """
        Proxy to bin.parse_markdown_path().
        """
        return bin.parse_markdown_path(
            path=path,
            rendered_index      = self.repository.settings.paths.index.rendered,
            rendered_folder     = self.repository.settings.paths.folder.rendered,
            source_index        = self.repository.settings.paths.index.source,
            source_folder       = self.repository.settings.paths.folder.source,
        )
    
    def prepare(
        self,
        path:str,
    )->SimpleNamespace:
        """
        Proxy to bin.prepare_markdown_path().
        """
        return bin.prepare_markdown_path(
            path=path,
            rendered_index      = self.repository.settings.paths.index.rendered,
            rendered_folder     = self.repository.settings.paths.folder.rendered,
            source_index        = self.repository.settings.paths.index.source,
            source_folder       = self.repository.settings.paths.folder.source,
        )
