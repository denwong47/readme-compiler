import contextlib

from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type, Union

import black
import black.mode
import black.report


from ..classes.io import SpoofedStdoutIO

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