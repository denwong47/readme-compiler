import os, sys

import dataclasses
import enum
import re
from types import SimpleNamespace
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type, Union

from django.template import Context as  DjangoContext, \
                            Engine as DjangoEngine, \
                            Origin as DjangoOrigin, \
                            Template as DjangoTemplate

from ..django_setup import register

from .. import bin
from .. import settings
from .. import fetchers

from .properties import GitProperties

from .cwd import WorkingDirectory

class MarkdownTemplateMode(enum.Enum):
    INDEX   =   0
    LEAF    =   1
    BRANCH  =   2

class RepositoryDirectory():
    """
    A directory containing a respository and the README structure.
    """
    def __init__(
        self,
        path:str="./",
        *,
        rendered_index:str  = settings.README_RENDERED_INDEX,
        rendered_folder:str = settings.README_RENDERED_DIRECTORY,
        source_index:str    = settings.README_SOURCE_INDEX,
        source_folder:str   = settings.README_SOURCE_DIRECTORY,
    ) -> None:
        """
        Initialise a `RepositoryDirectory` at the given location.
        """
        if (os.path.isdir(path)):
            path = os.path.abspath(path)
        else:
            raise FileNotFoundError(
                f"{repr(path)} is not a valid path to an existing folder."
            )

        self.settings   =   SimpleNamespace(
            root = path,
            paths = SimpleNamespace(
                index = SimpleNamespace(
                    source      = source_index,
                    rendered    = rendered_index,
                ),
                folder = SimpleNamespace(
                    source      = source_folder,
                    rendered    = rendered_folder,
                )
            )
        )

        self.git        =   GitProperties.from_path(path=self.path, parent=self)

    def __repr__(self) -> str:
        return type(self).__name__ + \
            "(" + \
                ', '.join([f'{_key}={repr(_value)}' for _key, _value in ( \
                    ('path', self.path),\
                    ('rendered_index', self.settings.paths.index.rendered),\
                    ('rendered_folder', self.settings.paths.folder.rendered),\
                    ('source_index', self.settings.paths.index.source),\
                    ('source_folder', self.settings.paths.folder.source),\
                )]) + \
            ")"

    @property
    def path(self)->str: return self.settings.root

    @path.setter
    def path(self, value:str): self.settings.root = value

    def context(
        self,
    )->DjangoContext:
        """
        Generate a DjangoContext from this `RepositoryDirectory`.
        """
        return DjangoContext({
            "git": self.git,
        })

    def render(
        self,
        path:str            = "./",
    )->str:
        """
        Render the template using Django Template API.
        """
        _template = MarkdownTemplate.from_file(path, index=self.settings.paths.index.source)

        return _template.render(self.context())


    def compile(
        self,
    )->bool:
        """
        Render all readme files in this `RepositoryDirectory`.
        """

class MarkdownTemplate(DjangoTemplate):
    """
    A template file for Markdown language.
    """
    def __init__(
        self,
        template_string: Union[DjangoTemplate, str],
        origin: Optional[DjangoOrigin]                  = None,
        name: Optional[str]                             = None,
        engine: Optional[DjangoEngine]                  = None,
    ) -> None:
        """
        """
        # Since we are not using any of the rest of Django, we need to create arbitrary engines for the Template.
        engine = engine or DjangoEngine(
            builtins=["readme_compiler.templatetags"],
        )

        # Add our library with template tags to the engine
        engine.builtins.append(register)

        super().__init__(template_string, origin, name, engine)

    @classmethod
    def from_file(
        cls:"MarkdownTemplate",
        path:str,
        *,
        index:str    = settings.README_SOURCE_INDEX,
    )->"MarkdownTemplate":
        """
        Initialise a `MarkdownTemplate` instance from an existing template file.
        """
        # Breaddown `path` to see what exactly we are supposed to do
        _parsed = bin.prepare_markdown_path(path)

        if (_parsed.mode is MarkdownTemplateMode.BRANCH):
           raise ValueError(
                f"{repr(path)} is a BRANCH; please specify the name of the template to load."
            )
        else:
            # Get the source path.
            # If this does not exists, but destination exists, then `prepare_markdown_path` would have copied it.
            path = _parsed.source

            if (os.path.isfile(path)):
                # File exists
                path = os.path.abspath(path)

                with open(path, "r") as _f:
                    return cls(_f.read())

            else:
                # File does not exists
                raise FileNotFoundError(
                    f"{repr(path)} not found."
                )