import os

from django.template import Context as  DjangoContext, \
                            Template as DjangoTemplate

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
    @classmethod
    def from_file(
        cls:"MarkdownTemplate",
        path:str,
    )->"MarkdownTemplate":
        """
        Initialise a `MarkdownTemplate` instance from an existing template file.
        """