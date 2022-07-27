import inspect
import re
from types import ModuleType, MethodType, MethodWrapperType, FunctionType, TracebackType, FrameType, CodeType
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type, Union

from .. import stdout

from .json_elements import JSONDescriptionCachedProperty, JSONDescriptionLRUCache, JSONDescriptionProperty
from .object import ObjectDescription
from .parameter import ParameterDescription
from . import format



ALLOWED_TYPES = (ModuleType, MethodType, MethodWrapperType, FunctionType, TracebackType, FrameType, CodeType)

def isbound(func:Callable) -> Union[Any, None]:
    """
    Return the bound object if `func` is a bound method,
    or return None if `func` is unbound.
    """
    return getattr(func, "__self__", None)

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
    _signature = inspect.Signature.from_callable(
        obj=obj,
        follow_wrapped=True,
    )
    
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
    DUNDER_NEW_NAME    = "__new__"

    _signature = signature(
        obj=obj,
        remove_self_cls=True
    )

    _formatted_code = format.source_code(
        f"def {obj.__name__}{_signature}: {PLACEHOLDER_CODE}"
    )

    # Further transformations:

    # Changing the name of the declaration.
    if (obj.__name__ in (
        DUNDER_INIT_NAME,
        DUNDER_NEW_NAME,
    )):
        # subsitute __init__ with the class name
        _formatted_code = _formatted_code.replace(
            f"def {obj.__name__}",
            obj.__qualname__.split(".")[-2], # Get only the Class name
        )
    elif (isinstance(obj, classmethod)):
        # subsitute __new__ with the class name
        _formatted_code = _formatted_code.replace(
            obj.__name__,
            obj.__qualname__,
            1,
        )
    else:
        # subsitute name with full qualified name
        if (
            len(_split_qualname := obj.__qualname__.split(".")) > 1
        ):
            _split_qualname[-2] += "(...)"

            __qualname__ = ".".join(_split_qualname)
        else:
            __qualname__ = obj.__qualname__

        _formatted_code = _formatted_code.replace(
            obj.__name__,
            __qualname__,
            1,
        )

    _formatted_code = PLACEHOLDER_PATTERN.sub(
        "",
        _formatted_code,
        1,
    )

    return _formatted_code


def raises(obj:Callable)->List[str]:
    """
    Return a list of `str` names of `BaseException`s that are mentioned literally in the source code of the callable.
    """
    RAISES_PATTERN = re.compile(r"(?<=[:\n])\s*raise\s+(?P<exception_type>[A-Z][\w\._]+)\(", re.MULTILINE)
    
    _exceptions = []
    for _raise in RAISES_PATTERN.finditer(inspect.getsource(obj)):
        _type_name = _raise.group("exception_type")

        # We can't actually resolve _type_name into the actual class because of different local and global contextes.
        _exceptions.append(_type_name)

    return _exceptions


class FunctionDescription(ObjectDescription):
    """
    Describe a function/method in `dict` form.
    """
    obj:Union.__getitem__(ALLOWED_TYPES)

    def __init__(
        self,
        obj: Callable,
        metadata: Dict[str, Any] = None,
    ) -> None:
        assert isinstance(obj, ALLOWED_TYPES), f"Cannot describe '{stdout.red(type(obj).__name__)}' - has to be one of the following types: " + ', '.join(map(lambda t:"'"+stdout.white(t.__name__)+"'", ALLOWED_TYPES))

        if (isinstance(obj, type)):
            raise ValueError(f"Ambigious {type(self).__name__} call on class {stdout.red(type(obj).__name__)}: please specify if you want to descirbe {type(self).__name__}.__init__, {type(self).__name__}.__new__ or {type(self).__name__}.__call__.")

        super().__init__(obj, metadata)

    @JSONDescriptionCachedProperty
    def raises(self) -> List[BaseException]:
        return raises(self.obj)

    @JSONDescriptionCachedProperty
    def isbound(self) -> Union[Any, None]:
        return isbound(self.obj)

    @JSONDescriptionLRUCache
    def signature(self, *args, **kwargs) -> inspect.Signature:
        return signature(self.obj, *args, **kwargs)

    @JSONDescriptionLRUCache
    def parameters(self, *args, **kwargs) -> List[inspect.Signature]:
        return parameters(self.obj, *args, **kwargs)

    @JSONDescriptionProperty.with_metadata_override
    def parameters_descriptions(self) -> List[ParameterDescription]:
        return list(
            map(
                ParameterDescription,
                self.parameters()
            )
        )

    @JSONDescriptionCachedProperty
    def signature_source_code(self) -> str:
        return signature_source_code(
            obj=self.obj,
        )
    