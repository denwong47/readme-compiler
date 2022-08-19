import os, sys

import contextvars
from datetime import datetime
import enum
import functools
import random
from types import SimpleNamespace
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type, Union

from django.template import Context as  DjangoContext, \
                            Engine as DjangoEngine, \
                            Origin as DjangoOrigin, \
                            Template as DjangoTemplate

from ..django_setup import register

from .. import bin
from .. import settings
from .. import stdout
from ..settings.enums import MarkdownTemplateMode, \
                             RenderPurpose

from ..log import logger
from .cwd import WorkingDirectory
from .properties import GitProperties
from .repopath import RepositoryPath
from .transformers import   transformers, \
                            Transformer, \
                            TransformerMeta, \
                            SINGLE_LINE_SPACER



class RepositoryDirectory():
    """
    A directory containing a respository and the README structure.
    """
    def __init__(
        self,
        path:str="./",
        *,
        transformers:List[Transformer]  = transformers,
        rendered_index:str              = settings.README_RENDERED_INDEX,
        rendered_folder:str             = settings.README_RENDERED_DIRECTORY,
        source_index:str                = settings.README_SOURCE_INDEX,
        source_folder:str               = settings.README_SOURCE_DIRECTORY,
        template_folder:str             = settings.TEMPLATE_LOCATION,
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
                ),
                template = template_folder,
            )
        )

        self.repopath   =   RepositoryPath(repository=self)
        self.git        =   GitProperties.from_path(path=self.path, parent=self)

        # If the transformers had not initialised, __init__() it with self as respository.
        self.transformers = list(map(
            lambda transformer: transformer(self) \
                                    if (isinstance(transformer, TransformerMeta)) \
                                        else transformer,
            transformers
        ))

    def __repr__(self) -> str:
        return type(self).__name__ + \
            "(" + \
                ', '.join([f'{_key}={repr(_value)}' for _key, _value in ( \
                    ('path', self.path),\
                    ('transformers', self.transformers),\
                    ('rendered_index', self.settings.paths.index.rendered),\
                    ('rendered_folder', self.settings.paths.folder.rendered),\
                    ('source_index', self.settings.paths.index.source),\
                    ('source_folder', self.settings.paths.folder.source),\
                    ('template_folder', self.settings.paths.template),\
                )]) + \
            ")"

    @property
    def path(self)->str:
        """
        Return the local path of the git repository.
        """
        return self.settings.root

    @path.setter
    def path(self, value:str): self.settings.root = value

    def context(
        self,
    )->DjangoContext:
        """
        Generate a DjangoContext from this `RepositoryDirectory`.
        """
        return DjangoContext({
            "spacer": SINGLE_LINE_SPACER,
            "repository_object": self,  # This is not for Template syntax use - more for Template tags.
            "repository_path": self.repopath, # This is not for Template syntax use - more for Template tags.
            "git": self.git,
            "globals": bin.map_unders(globals()),
        })

    # Cache the output - in case we repeat stuff because of embed etc.
    @functools.lru_cache()
    def render(
        self,
        path:str                = "./",
        *,
        purpose:RenderPurpose   = RenderPurpose.STANDARD,
        dry_run:bool            = False,
    )->str:
        """
        Render the template using Django Template API.
        """
        _template = MarkdownTemplate.from_file(
            path,
            rendered_index      = self.settings.paths.index.rendered,
            rendered_folder     = self.settings.paths.folder.rendered,
            source_index        = self.settings.paths.index.source,
            source_folder       = self.settings.paths.folder.source,

            transformers        = self.transformers,
        )

        # Render the text
        _rendered = _template.render(self.context(), purpose=purpose)

        # Get the destination path
        _rendered_path = self.repopath.parse(path).rendered

        if (not dry_run):
            # If this is not a dry run, save the compiled file to the rendered location.
            try:
                with open(_rendered_path, "w") as _f:
                    _f.write(_rendered)

                # Add file to repository
                if (self.git.add(path) and \
                    self.git.add(_rendered_path)):
            
                    logger.info(
                        " - "+stdout.green("SUCCESS: ")+f"Saved {self.colour_path(path.ljust(120))} at {self.colour_path(_rendered_path)} containing {len(_rendered):,} bytes of data."
                    )
                else:
                    logger.info(
                        " - "+stdout.yellow("WARNING: ")+f"Saved {self.colour_path(path.ljust(120))} at {self.colour_path(_rendered_path)} containing {len(_rendered):,} bytes of data, but {stdout.red('git add command had failed')}."
                    )
            except (
                OSError,
                RuntimeError,
                PermissionError,
            ) as e: 
                logger.error(
                     " - "+stdout.red("ERROR  : ")+f"Failed to save {self.colour_path(path.ljust(120))} at {self.colour_path(_rendered_path)}: {type(e).__name__} occured: {str(e)}"
                )

        else:
            logger.info(
                " - "+stdout.yellow("DRY RUN: ")+f"Did not save {self.colour_path(path.ljust(120))} at {self.colour_path(_rendered_path)} with {len(_rendered):,} bytes of data."
            )

        return _rendered

    def template(
        self,
        template:str,
        *,
        template_path:str       = None, # None is correct here, see doc string below.
        template_filename:str   = settings.TEMPLATE_FILE_NAME,
    ) -> "MarkdownTemplate":
        """
        ### Get a `MarkdownTemplate` instance

        The `MarkdownTemplate` object will be local to this `RepositoryDirectory`, and of the type `template`.

        This works slightly differently to the underlying `MarkdownTemplate.from_template()` - if `template_path` is provided, then the path will be treated as absolute; otherwise this will be loaded from settings as repopath.

        Raises a `FileNotFoundError` if the template is not found.
        """
        if (not isinstance(template_path, str)):
            return MarkdownTemplate.from_template(
                template            = template,
                transformers        = self.transformers,
                repopath            = self.repopath,
                template_path       = settings.TEMPLATE_LOCATION,
                template_filename   = template_filename,
            )
        else:
            return MarkdownTemplate.from_template(
                template            = template,
                transformers        = self.transformers,
                repopath            = None,
                template_path       = template_path,
                template_filename   = template_filename,
            )

    def list_markdowns(
        self,
        *,
        subdirectories:List[str]=[],
        recursive:bool=True,
    )->List[str]:
        """
        Return a list of all markdown files found, recursively searched in the folder.
        """
        _return_list = []

        path = os.path.join(
            self.git.path,
            *subdirectories,
        )
        
        _blacklist = [
            self.repopath.abspath(settings.ENV_PATH),
            self.repopath.abspath(self.settings.paths.template),
            self.repopath.abspath(settings.TEMPLATE_LOCATION),
        ]

        with WorkingDirectory(path=path) as cwd:
            for _file in os.listdir(path):

                if (recursive and \
                    os.path.isdir(_file) and \
                    os.path.abspath(_file) not in _blacklist and \
                    not settings.TEMPLATE_LOCATION in os.path.abspath(_file)
                ):
                    # If its a directory, and we are doing it recursively, then recursively call this method
                    _return_list += self.list_markdowns(
                        subdirectories = subdirectories + [_file],
                        recursive=recursive,
                    )
                elif (bin.is_markdown(_file)):
                    # If its a .md, add it to the list
                    _abspath = os.path.abspath(_file)

                    _return_list.append(
                        _abspath
                    )

        return _return_list

    def list_sources(
        self,
        *,
        recursive:bool=True,
    )->List[str]:
        """
        Return a list of all markdowns that are classifed as "sources".
        """

        _return_list = []

        for _file in self.list_markdowns(
            subdirectories=[],
            recursive=recursive,
        ):
            _parsed = self.repopath.prepare(_file)

            # If its not a branch (it won't, because these are files)
            if (_parsed.mode is not MarkdownTemplateMode.BRANCH):
                # If the source is not already on the list, append it
                if (_parsed.source not in _return_list): _return_list.append(_parsed.source)

        return _return_list

    def colour_path(
        self,
        path:str,
    )->str:
        """
        Add ANSI colours to specific terms to make the path more readable.
        """
        # Replace file name with cyan
        path = path.replace(os.path.basename(path), stdout.cyan(os.path.basename(path)))
        path = path.replace(self.git.repo, stdout.blue(self.git.repo))
        if (self.settings.paths.folder.source in path):
            path = path.replace(self.settings.paths.folder.source, stdout.red(self.settings.paths.folder.source))
        else:
            path = path.replace(self.settings.paths.folder.rendered, stdout.yellow(self.settings.paths.folder.rendered))

        return path

    def compile(
        self,
        *,
        dry_run:bool        = False,
    )->bool:
        """
        Render all readme files in this `RepositoryDirectory`.
        """
        logger.info("")
        logger.info(stdout.blue("readme-compiler"))
        logger.info(stdout.white("https://www.github.com/denwong47/readme-compiler"))
        logger.info(f"A markdown formatter using {stdout.white('django Template API')}.")
        logger.info("")
        logger.info("Compiling git repository at "+stdout.white(self.path)+"...")
        logger.info("")
        for _attr in ("repo", "hook", "branch", "owner", "path"):
            logger.info(f"- {_attr:24s}: {stdout.cyan(getattr(self.git, _attr))}")
        logger.info("")

        _sources = self.list_sources()

        logger.info(f'Found {stdout.cyan(len(_sources))} Markdown source files, including:')
        for _file in random.sample(_sources, min(8, len(_sources))):
            logger.info(f"- {self.colour_path(_file)}")

        logger.info("")

        logger.info(stdout.blue("readme-compiler") + " is now renderingd Markdown files...")
        # Actually starts rendering
        for _file in _sources:
            self.render(_file, dry_run=dry_run)

        logger.info("")

        logger.info(stdout.blue("readme-compiler") + " completed.")
        logger.info("")

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
        *,
        path: str                                       = None,
        transformers: Iterable[Callable[[str], str]]    = None,
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

        self.transformers = transformers if (isinstance(transformers, Iterable)) else []
        self.path         = path

    @classmethod
    def from_file(
        cls:"MarkdownTemplate",
        path:str,
        *,
        transformers: Iterable[Callable[[str], str]]    = None,

        rendered_index:str  = settings.README_RENDERED_INDEX,
        rendered_folder:str = settings.README_RENDERED_DIRECTORY,
        source_index:str    = settings.README_SOURCE_INDEX,
        source_folder:str   = settings.README_SOURCE_DIRECTORY,
    )->"MarkdownTemplate":
        """
        Initialise a `MarkdownTemplate` instance from an existing template file.
        """
        # Breaddown `path` to see what exactly we are supposed to do
        _parsed = bin.prepare_markdown_path(
            path,
            rendered_index  = rendered_index,
            rendered_folder = rendered_folder,
            source_index    = source_index,
            source_folder   = source_folder,
        )

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
                    return cls(
                        _f.read(),
                        transformers    = transformers,
                        path            = path,
                    )

            else:
                # File does not exists
                raise FileNotFoundError(
                    f"{repr(path)} not found."
                )

    @classmethod
    def from_template(
        cls:"MarkdownTemplate",
        template:str,
        *,
        transformers: Iterable[Callable[[str], str]]    = None,
        repopath:Union[
            RepositoryPath,
            RepositoryDirectory,
        ] = None,
        template_path:str       = settings.TEMPLATE_LOCATION,
        template_filename:str   = settings.TEMPLATE_FILE_NAME,
    )->"MarkdownTemplate":
        """
        ### Loads a markdown template

        Loads a markdown template from 

        If `repopath` is specified as a `RepositoryPath` or `RepositoryDirectory`, then `settings.TEMPLATE_LOCATION` will be treated as a RepositoryPath (i.e. root directory pointed to the RepositoryPath).
        Otherwise `settings.TEMPLATE_LOCATION` will be treated as an absolute system path.
        """
        if (isinstance(repopath, RepositoryDirectory)):
            repopath = repopath.repopath

        if (not isinstance(repopath, RepositoryPath)):
            repopath = None
            
        if (repopath):
            _filepath = repopath.abspath(
                template_path
            )
        else:
            _filepath = template_path

        _abspath = os.path.join(
            _filepath,
            template_filename.format(
                template    = template,
            )
        )

        if (os.path.isfile(_abspath)):
            # File exists
            _abspath = os.path.abspath(_abspath)

            with open(_abspath, "r") as _f:
                return cls(
                    _f.read(),
                    transformers    = transformers,
                    path            = _abspath,
                )

        else:
            # File does not exists
            raise FileNotFoundError(
                f"{repr(_abspath)} not found."
            )

        

    def render(
        self:"MarkdownTemplate",
        context: Optional[
            Union[
                DjangoContext,
                Dict[str, Any]
            ]
        ],
        *,
        purpose:RenderPurpose = RenderPurpose.NORMAL,
    ) -> str:
        """
        After Rendering with the Template, pass the result through any transformers specified.
        """

        # Switch cwd to the path of the file before we render.
        with WorkingDirectory(path=self.path) as cwd:

            _rendered = super().render(context)

            for _transformer in filter(callable, self.transformers):
                if (_transformer.should_transform(
                    self.path,
                    purpose=purpose,
                )):
                    _rendered = _transformer(_rendered)

            return _rendered