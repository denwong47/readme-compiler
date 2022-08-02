import inspect
import re
from types import ModuleType, MethodType, MethodWrapperType, FunctionType, TracebackType, FrameType, CodeType
import typing
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type, Union

from .. import stdout

from .json_elements import JSONDescriptionCachedProperty, JSONDescriptionLRUCache, JSONDescriptionProperty
from .object import ObjectDescription
from .parameter import AnnotationDescription, ParameterDescription
from .. import format
from . import exceptions

ALLOWED_TYPES = (ModuleType, MethodType, MethodWrapperType, FunctionType, TracebackType, FrameType, CodeType)

def isbound(func:Callable) -> Union[Any, None]:
    """
    Return the bound object if `func` is a bound method,
    or return None if `func` is unbound.
    """
    return getattr(func, "__self__", None)

def isinstancemethod(method:Callable) -> bool:
    """
    This is a bit of a brute force approach to figure out if something is an instance method:
    i.e. MyClass.method instead of MyClass().method - the latter of which is called a `bound` method.

    This look for the module of the method, and see if `module.method` is identical to method;
    if it's not, and the method is not `bound`, then we know that a class is sitting in between.

    NOTE There is an unsolvable bug in this method:
    ```python
    def my_method(self):
        pass

    class MyClass():
        my_method = my_method
    ```
    In the above structure, `isinstancemethod(MyClass.my_method)` will return `False` while its in fact a valid instance method.
    """
    return not any(
        map(
            lambda check: check(method),
            (
                isbound,
                isfunction,
            )
        )
    )
    # We still don't know what class its attached to, unfortunately.
    
    
def isfunction(method:Callable) -> bool:
    """
    This look for the module of the method, and see if `module.method` is identical to method.
    """
    _module = inspect.getmodule(method)

    if (isinstance(_module, ModuleType)):
        return getattr(_module, method.__name__, None) is method
    else:
        return False

def isclassmethod(method:Callable) -> bool:
    """
    Check if a method is:
    - bound to a type, i.e. `__self__` is a type,
    - looking up the `__mro__` of the method, look for each of the ancestry classes to see if the descriptor that matches the method's name is in fact a `classmethod`.
        - this tells apart descriptors that happen to have the same name.

    See https://stackoverflow.com/questions/19227724/check-if-a-function-uses-classmethod .
    """

    bound_to = getattr(method, '__self__', None)
    if not isinstance(bound_to, type):
        # must be bound to a class
        return False
    name = method.__name__
    for cls in bound_to.__mro__:
        descriptor = vars(cls).get(name)
        if descriptor is not None:
            return isinstance(descriptor, classmethod)

    return False


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
            isinstancemethod(obj) or \
            isbound(obj)
        ):
            _split_qualname = obj.__qualname__.split(".")

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

    def __new__(
        cls: type["FunctionDescription"],
        obj: Callable,
        *args,
        **kwargs,
    ) -> Union[
        exceptions.ObjectNotDescribable,
        "FunctionDescription",
    ]:
        if (not isinstance(obj, ALLOWED_TYPES)):
            return exceptions.ObjectNotDescribable(
                f"Cannot describe '{stdout.red(type(obj).__name__)}' - has to be one of the following types: " + ', '.join(map(lambda t:"'"+stdout.white(t.__name__)+"'", ALLOWED_TYPES))
            )

        return super().__new__(cls)

    def __init__(
        self,
        obj: Callable,
        metadata: Dict[str, Any] = None,
    ) -> None:
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

    @JSONDescriptionCachedProperty
    def type(self) -> Type:
        if (isclassmethod(self.obj)):
            return classmethod
        else:
            return super().type

    @JSONDescriptionCachedProperty.with_metadata_override
    def kind_description(self) -> str:
        _describers = []
        _kind = "Method"

        if (self.isabstract):
            _describers.append("Abstract")

        if (isclassmethod(self.obj)):
            _describers.append("Class")
        elif (self.isbound):    # This doesn't really work - this is only `True` if the method passed to `describe` was bound; but if its just a method in a class, Python can't tell if its related to a class on its own.
            _describers.append("Bound")
        elif (isinstancemethod(self.obj)):
            _describers.append("Bound")
            # _describers.append("Instance")
        elif (isfunction(self.obj)):
            _kind = "Function"

        _describers.append(_kind)

        return " ".join(_describers)

        
    
    @JSONDescriptionCachedProperty
    def return_annotation(self) -> Union[typing._GenericAlias, Type]:
        """
        Return the annotation object for the return value.
        """
        return self.signature().return_annotation

    @JSONDescriptionCachedProperty
    def return_description(self) -> "AnnotationDescription":
        """
        Return the `AnnotationDescription` object for the return value's annotation.
        """
        return AnnotationDescription(
            self.return_annotation
        )
