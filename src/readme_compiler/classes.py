import os

from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type, Union

from django.template import Context as  DjangoContext, \
                            Engine as DjangoEngine, \
                            Origin as DjangoOrigin, \
                            Template as DjangoTemplate

from .django_setup import register

from . import bin
from . import settings

class RepositoryDirectory():
    """
    A directory containing a respository and the README structure.
    """
    def __init__(
        self,
        path:str="./",
        *,
        echo:bool           = True,
        rendered_index:str  = settings.README_RENDERED_INDEX,
        rendered_folder:str = settings.README_RENDERED_DIRECTORY,
        source_index:str    = settings.README_SOURCE_INDEX,
        source_folder:str   = settings.README_SOURCE_DIRECTORY,
    ) -> None:
        """
        Initialise a `RepositoryDirectory` at the given location.
        """

    def context(
        self,
    )->DjangoContext:
        """
        Generate a DjangoContext from this `RepositoryDirectory`.
        """

    def render(
        self,
        path:str            = "./",
    )->str:
        """
        Render the template using Django Template API.
        """

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
        engine: Optional[DjangoEngine]                  = None
    ) -> None:
        """
        """
        # Since we are not using any of the rest of Django, we need to create arbitrary engines for the Template.
        engine = engine or DjangoEngine(
            builtins=["readme_compiler.templatetags"],
        )

        # Add our library with template tags to the engine
        engine.builtins.append(register)

        print (engine.builtins)

        super().__init__(template_string, origin, name, engine)

    @classmethod
    def from_file(
        cls:"MarkdownTemplate",
        path:str,
    )->"MarkdownTemplate":
        """
        Initialise a `MarkdownTemplate` instance from an existing template file.
        """