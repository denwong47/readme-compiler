"""

"""

import os
from distutils import dir_util, file_util
import logging
from pathlib import Path
from types import SimpleNamespace
from typing import List

from .classes import MarkdownTemplateMode
from . import settings
from .log import logger

print = logger.debug

def is_markdown(filename:str)->bool:
    if (isinstance(settings.FILE_EXTENSION_MARKDOWN, str)): settings.FILE_EXTENSION_MARKDOWN = (settings.FILE_EXTENSION_MARKDOWN, )

    for _extension in settings.FILE_EXTENSION_MARKDOWN:
        if (_extension[0] != "."): _extension = "."+_extension

        # If the last bit of file name matches the extension
        if (filename[-len(_extension):].lower() == _extension.lower()):
            return True
    
    return False

def split_abspath(path:str)->SimpleNamespace:
    """
    Fully split a path down into elements.
    """
    if (os.path.isdir(path)):
        _dir, _file = path, None
    else:
        _dir, _file = os.path.split(path)

    _dir = os.path.abspath(_dir).split("/")
    if (not _file): _file = None
    
    return SimpleNamespace(
        dir = _dir,
        file = _file,
    )

def parse_markdown_path(
    path:str,
    *,
    rendered_index:str  = settings.README_RENDERED_INDEX,
    rendered_folder:str = settings.README_RENDERED_DIRECTORY,
    source_index:str    = settings.README_SOURCE_INDEX,
    source_folder:str   = settings.README_SOURCE_DIRECTORY,
)->SimpleNamespace:
    """
    Figure out what the path is, and how we should deal with it.
    """
    _mode = None

    print (f"Analysing {repr(path)}.")
    
    if (os.path.isdir(path)):
        print (f"{repr(path)} is a directory.")

        if (split_abspath(path).dir[-1] == source_folder):
            # This is a ./GITDIR/.readme.source folder
            print (f"{repr(path)} appears to be a source readme folder.")

            _source_path        = path
            _rendered_path      = os.path.join(
                os.path.dirname(path),   # This means that source and rendered MUST live in the same dir,
                rendered_folder,
            )
            _mode               = MarkdownTemplateMode.BRANCH
            
        elif (split_abspath(path).dir[-1] == rendered_folder):
            # This is a ./GITDIR/.readme folder
            print (f"{repr(path)} appears to be a rendered readme folder.")

            _source_path        = os.path.join(
                os.path.dirname(path),   # This means that source and rendered MUST live in the same dir,
                source_folder
            )
            _rendered_path      = path
            _mode               = MarkdownTemplateMode.BRANCH

        else:
            # This is a plain ./GITDIR folder, treat it as index
            print (f"{repr(path)} appears to imply an index {rendered_index}.")

            _source_path        = os.path.join(path, source_index)
            _rendered_path      = os.path.join(path, rendered_index)
            _mode               = MarkdownTemplateMode.INDEX

    else:
        print (f"{repr(path)} is NOT a directory.")

        if (source_folder == split_abspath(path).dir[-1]):
            # This is a ./GITDIR/.readme.source/somefile.md
            print (f"{repr(path)} appears to be a template in source readme folder.")

            _source_path        = path
            _rendered_path      = path.replace(source_folder, rendered_folder)
            _mode               = MarkdownTemplateMode.LEAF
            
        elif (rendered_folder == split_abspath(path).dir[-1]):
            # This is a ./GITDIR/.readme/somefile.md
            print (f"{repr(path)} appears to be a template in rendered readme folder.")

            _source_path        = path.replace(rendered_folder, source_folder)
            _rendered_path      = path
            _mode               = MarkdownTemplateMode.LEAF

        elif (rendered_index == split_abspath(path).file):
            # This is a ./GITDIR/README.md
            print (f"{repr(path)} is an absolute path to a {rendered_index}.")

            _source_path        = path.replace(rendered_index, source_index)
            _rendered_path      = path
            _mode               = MarkdownTemplateMode.INDEX

        elif (source_index == split_abspath(path).file):
            # This is a ./GITDIR/.README.source.md
            print (f"{repr(path)} is an absolute path to a {source_index}.")

            _source_path        = path
            _rendered_path      = path.replace(source_index, rendered_index)
            _mode               = MarkdownTemplateMode.INDEX
        # elif (is_markdown(path)):
        #     # This could be a lone .md file like README.md and .README.source.md?
        #     print (f"{repr(path)} appears to be a standaloned Markdown file.")\
            
        #     _source_path        = path + SOME SUFFIX?
        #     _rendered_path      = path
        #     _mode               = MarkdownTemplateMode.INDEX
        else:
            raise ValueError(f"{repr(path)} is not recognised as a valid path for a Markdown.")

    return SimpleNamespace(
        mode        = _mode,
        source      = _source_path,
        rendered    = _rendered_path,
    )

def prepare_markdown_path(
    path:str,
    *,
    rendered_index:str  = settings.README_RENDERED_INDEX,
    rendered_folder:str = settings.README_RENDERED_DIRECTORY,
    source_index:str    = settings.README_SOURCE_INDEX,
    source_folder:str   = settings.README_SOURCE_DIRECTORY,
)->SimpleNamespace:
    """
    If source doesn't exist but rendered does, copy rendered to source.
    """

    _parsed = parse_markdown_path(
        path=path,
        rendered_index=rendered_index,
        rendered_folder=rendered_folder,
        source_index=source_index,
        source_folder=source_folder,
    )

    print (f"{repr(path)} parsed to {repr(_parsed)}.")

    _mode = _parsed.mode
    _source_path = _parsed.source
    _rendered_path = _parsed.rendered
    

    # On to preparing the paths.
    if (_mode in (
        MarkdownTemplateMode.BRANCH,
    )):
        print (f"BRANCH mode engaged.")

        # BRANCH mode - this is ./GITDIR/.readme
        _source_exists          = os.path.isdir(_source_path)
        _rendered_exists        = os.path.isdir(_rendered_path)

        print (f"Source {_source_path} {'exists' if _source_exists else 'does not exist'}.")
        print (f"Destination {_rendered_path} {'exists' if _rendered_exists else 'does not exist'}.")

        if (not _source_exists and not _rendered_exists):
            raise ValueError(f"{repr(path)} has neither '{source_folder}' nor '{rendered_folder}' directories.")
        
        if (_source_exists and not _rendered_exists):
            # This is fine
            pass
        elif (_rendered_exists and not _source_exists):
            # Only destination exists; then clone destination into source.
            print (f"Copying contents of {repr(_rendered_path)} into {repr(_source_path)}...")

            dir_util.copy_tree(
                _rendered_path,
                _source_path,
                preserve_symlinks=0,
                verbose=1 if (settings.LOGGING_LEVEL <= logging.DEBUG) else 0,
            )
        else:
            # This is fine
            pass

        return True
    
    else:
        # INDEX, LEAF mode - this is a single file
        for _path in (
            _source_path,
            _rendered_path,
        ):
            # Make sure all parent directories exist.
            print (f"Ensuring {repr(os.path.dirname(_path))} exists...")

            Path(os.path.dirname(_path)).mkdir(parents=True, exist_ok=True)

            assert os.path.isdir(os.path.dirname(_path)), f"{repr(os.path.dirname(_path))} still not found after creation!"

        _source_exists          = os.path.isfile(_source_path)
        _rendered_exists        = os.path.isfile(_rendered_path)

        print (f"Source {_source_path} {'exists' if _source_exists else 'does not exist'}.")
        print (f"Destination {_rendered_path} {'exists' if _rendered_exists else 'does not exist'}.")

        if (_source_exists and not _rendered_exists):
            # This is fine
            pass
        elif (_rendered_exists and not _source_exists):
            # Only destination exists; then clone destination into source.
            print (f"Copying {repr(_rendered_path)} to {repr(_source_path)}...")

            file_util.copy_file(
                _rendered_path,
                _source_path,
                verbose=1 if (settings.LOGGING_LEVEL <= logging.DEBUG) else 0,
            )
        else:
            # This is fine
            pass

    return _parsed
