"""
Markdown and Python source code formatting.
"""

import contextlib
import inspect
import re

from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type, Union

import black
import black.mode
import black.report


from .classes.io import SpoofedStdoutIO

def format_source_code(
    source_code:str,
    *,
    write_back:black.WriteBack  = black.WriteBack.YES,
    mode:black.mode.Mode        = black.FileMode(),
) -> str:
    """
    Use `black` to format the code of object.
    """
    with    SpoofedStdoutIO() as _io, \
            contextlib.redirect_stdout(_io) as context:

        _report = black.report.Report(quiet=True)

        black.reformat_code(
            content     = source_code,
            fast        = False,
            write_back  = write_back,
            mode        = mode,
            report      = _report,
        )

        _io.seek(0)
        _return = _io.getvalue()

        return _return.decode("utf-8") if _return else None
    
source_code = format_source_code

def prefix(
    source_code:str,
    lead:str,
)->str:
    """
    Add leading characters to each line.
    """

    return "\n".join(
        [
            (lead+_line) for _line in source_code.split("\n")
        ]
    )

def quote(
    source_code:str,
)->str:
    """
    Add leading > to each line.
    """
    return prefix(source_code=source_code, lead="> ")

def remarks(
    source_code:str,
)->str:
    """
    Add leading # to each line.
    """
    return prefix(source_code=source_code, lead="# ")

def reindent(
    source_code:str,
    indent:int=0,
)->str:
    """
    Re-write all indents of lines to the desired amount.
    """
    _code = inspect.cleandoc(source_code)

    # Skip this part for optimisation if indent is not needed
    if (indent >0):
        _code = "\n".join(
            [
                (" "*indent+_line) for _line in _code.split("\n")
            ]
        )

    return _code

def remove_remarks(
    source_code:str,
)->str:
    """
    Remove all lines with leading #s.
    """
    REMARKS_PATTERN = re.compile(r"^(?P<preceding_spaces>\s*)#\s?[\w\W]+", re.MULTILINE) # Remove up to one space after the # as most IDE does it that way

    return "\n".join(
        filter(
            lambda line: not REMARKS_PATTERN.match(line),
            source_code.split("\n"),
        )
    )

def unremark(
    source_code:str,
)->str:
    """
    Remove all leading #s from lines.
    """
    REMARKS_PATTERN = re.compile(r"^(?P<preceding_spaces>\s*)#\s?", re.MULTILINE) # Remove up to one space after the # as most IDE does it that way

    source_code = REMARKS_PATTERN.sub(
        "\g<preceding_spaces>",
        source_code
    )

    return source_code

def code(
    source_code:str,
    *,
    format:bool=True,
    **kwargs,
)->str:
    """
    Format the code with `black`, and wraps code around in `python` code block.
    """
    if (format): source_code = format_source_code(source_code=source_code, **kwargs)

    return f"```python\n{source_code}\n```"

def split_title(
    markdown:str,
)->Dict[str, str]:
    """
    Attempt to Parse the markdown into title and text.
    """
    TITLE_PATTERN = re.compile(r"^\s*(?P<title_wrapper>(?:#{1,5})|(?:[*_]{1,2}))\s*(?P<title>.+?)\s*(?:(?P=title_wrapper))?$", re.MULTILINE )
    
    if (not isinstance(markdown, str)):
        _title = None
        _body = markdown
        _level = None
    elif (markdown.strip()):
        # Ensure there is something in the string
        _lines = markdown.split("\n")

        for _id, _line in enumerate(_lines):
            if (_match := TITLE_PATTERN.match(_line)):
                _title = _match.group("title")
                _body = "\n".join(_lines[_id+1:])
                _level = _match.group("title_wrapper")
                break
    else:
        _title = None
        _body = ""
        _level = None

    return {
        "title":_title,
        "body":_body,
        "level":_level,
    }