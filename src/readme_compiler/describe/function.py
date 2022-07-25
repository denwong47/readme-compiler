import inspect
import re
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type, Union

from . import format

def parameters(
    obj:Callable,
    *,
    remove_self_cls:bool=False,
    omit:Tuple[str]=None,
)->List[inspect.Parameter]:
    """
    Get the parameters of a callable in a list, with option to remove items if required.
    """
    if (not isinstance(omit, Iterable)):
        omit = ()
    elif (isinstance(omit, str)):
        omit = (omit, )

    _signature = inspect.signature(obj=obj)
    _parameters = list(_signature.parameters.values())

    if (len(_parameters)):
        # We have some _parameters to play with
        if (remove_self_cls):
            if (_parameters[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD and \
                _parameters[0].name in ("self", "cls", "self_cls", "cls_self", "selfcls", "clsself") and \
                _parameters[0].default is inspect._empty):

                # remove any `self`, `cls` and the likes from `_parameters`, then replace it in `_signature`.
                _parameters.pop(0)

        # remove parameters in omit list
        _parameters = list(
            filter(
                lambda param: param.name not in omit,
                _parameters
            )
        )

    return _parameters

def signature(
    obj:Callable,
    *,
    remove_self_cls:bool=False,
    omit:Tuple[str]=None,
)->inspect.Signature:
    """
    Get the signature of a callable, with option to remove items if required.

    For documentation purposes:
    - bound methods of classes should not show `self` as first parameter; and
    - `__init__` methods should show the name of the class instead, i.e. how to create an instance.
    """
    _signature = inspect.signature(obj=obj)
    
    # Get rid of self/cls/self_cls/cls_self etc
    _signature = _signature.replace(
        parameters = parameters(
            obj=obj,
            remove_self_cls=remove_self_cls,
            omit=omit,
        )
    )

    return _signature

def signature_source_code(
    obj:Callable,
)->str:
    """
    Get the signature of a callable as a formatted `str`.
    """
    PLACEHOLDER_CODE    = "__VOID_FUNCTION__()"
    PLACEHOLDER_PATTERN = re.compile(r":\s+"+re.escape(PLACEHOLDER_CODE)+r"\s*$", re.MULTILINE)

    DUNDER_INIT_NAME    = "__init__"

    _signature = signature(
        obj=obj,
        remove_self_cls=True
    )

    _formatted_code = format.source_code(
        f"def {obj.__name__}{_signature}: {PLACEHOLDER_CODE}"
    )

    # Further transformations:

    # Changing the name of the declaration.
    if (obj.__name__ == DUNDER_INIT_NAME):
        # subsitute __init__ with the class name
        _formatted_code = _formatted_code.replace(
            f"def {obj.__name__}",
            obj.__qualname__.split(".")[-2], # Get only the Class name
        )
    else:
        # subsitute name with full qualified name
        _formatted_code = _formatted_code.replace(
            obj.__name__,
            obj.__qualname__,
            1,
        )

    _formatted_code = PLACEHOLDER_PATTERN.sub(
        "",
        _formatted_code,
        1,
    )

    return _formatted_code