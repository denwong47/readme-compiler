import abc
import builtins
import inspect
import re
from types import SimpleNamespace, ModuleType, MethodType, FunctionType, TracebackType, FrameType, CodeType, GenericAlias 
import typing
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type, Union, ForwardRef, get_origin, get_args

from .. import stdout

from . import exceptions
from .json_elements import JSONDescriptionCachedProperty, JSONDescriptionLRUCache, JSONDescriptionProperty
from .object import ObjectDescription

ANNOTATION_TYPES = (
    typing._GenericAlias,
    str,
    type,
)

_AnnotationAlias = Union.__getitem__(ANNOTATION_TYPES)

class PseudoAliasMeta(abc.ABCMeta):
    """
    Metaclass to remember all subclasses of PseudoAlias declared.
    """
    _members:List[typing._GenericAlias] = {}

    def __init__(self, *args, **kwargs):
        super().__init__(self)
        
        if (not inspect.isabstract(self)):
            # Only append class if its not abstract: we don't want `PseudoAlias` in there.
            type(self)._members[self.name] = self

    @classmethod
    def types(cls) -> SimpleNamespace:
        return SimpleNamespace(
            **cls._members
        )

class PseudoAlias(abc.ABC, metaclass=PseudoAliasMeta): # we cannot subclass typing._GenericAlias - which is a shame.
    """
    A proxy class to group together all custom Aliases.

    Custom Aliases won't be usable as type hints - they are merely for `AnnotationDescription` to distinguish non-standard annotations.
    """
    args:List[typing._GenericAlias]

    def __init__(
        self,
        *aliases:typing._GenericAlias,
    ) -> None:
        self.args   =   aliases

    @abc.abstractproperty
    def name(self) -> str:
        pass
    
    @abc.abstractproperty
    def markdown(self) -> str:
        pass

    def __str__(self) -> str:
        return self.type_hint

    @abc.abstractproperty
    def type_hint(self) -> str:
        pass


class PropertyType(PseudoAlias):
    """
    A `PseudoAlias` class that stores the annotations of `property` objects.
    """
    def __init__(
        self,
        fget_annotation: _AnnotationAlias,
        fset_annotation: _AnnotationAlias,
    ) -> None:
        super().__init__(
            fget_annotation,
            fset_annotation,
        )

        self.fget_annotation = fget_annotation
        self.fset_annotation = fset_annotation

    @property
    def name(self) -> str:
        return "property"
    
    @property
    def type_hint(self) -> str:
        return f"{type(self).__name__}[{str(self.fget_annotation)}, {str(self.fset_annotation)}]"
    
    @property
    def markdown(self) -> str:
        _annotations = []
        
        if (self.fget_annotation): _annotations.append(f"Get: {AnnotationDescription(self.fget_annotation).markdown}")
        if (self.fset_annotation): _annotations.append(f"Set: {AnnotationDescription(self.fset_annotation).markdown}")

        return "; ".join(_annotations)

    @classmethod
    def from_property(
        cls,
        obj:property,
    ) -> "PropertyType":
        if (not isinstance(obj, property)):
            raise exceptions.ObjectNotDescribable(
                f"{type(cls).__name__}.from_property only accepts 'property' objects; '{type(obj).__name__}' found."
            )
    
        return cls(
            inspect.signature(obj.fget).return_annotation,
            list(inspect.signature(obj.fset).parameters.values())[1].annotation \
                if callable(obj.fset) \
                    else None,
        )


types = PseudoAliasMeta.types

class AnnotationDescription(ObjectDescription):
    """
    Describe an Annotation with simplified language.
    """
    wrapper:Type[GenericAlias]
    args:List[str]

    def __repr__(self) -> str:
        return f"{type(self).__name__}({str(self.obj)})"

    def __init__(
        self,
        annotation:GenericAlias,
    ) -> None:
        """
        Initialise an Annotation object 
        """
        self.parse(annotation)

    def parse(
        self,
        annotation:GenericAlias,
    ):
        # Make sure we still store it - `PseudoAlias` relies on this!
        self.obj = annotation
        
        if (self.obj is None or \
            self.obj is type(None)
        ):
            # NoneType
            self.wrapper = None
            self.args = [ "None", ]

        elif (self.obj is inspect._empty):
            # Type Hinting not specified
            self.wrapper = None
            self.args = [ "Any", ]

        elif (isinstance(self.obj, ForwardRef)):
            # ForwardRef('classes.MarkdownTemplate')
            self.wrapper = None
            self.args = [self.obj.__forward_arg__, ]

        elif (isinstance(self.obj, PseudoAlias)):
            # Custom Alias
            self.wrapper = type(self.obj)
            self.args = self.obj.args   # Not really used

        elif (isinstance(self.obj, (typing._GenericAlias, typing.Callable))):
            # Union/Iterable/Callable[] etc
            self.wrapper = get_origin(self.obj)

            self.args = list(
                map(
                    type(self),
                    get_args(self.obj),
                )
            )

        elif (self.obj is typing.Type):
            # Type[]
            self.wrapper = type   # pass as str            
            self.args = get_args(self.obj)
        
        elif (self.obj is typing.Any):
            # Type[]
            self.wrapper = "Any"   # pass as str            
            self.args = []

        elif (isinstance(self.obj, str)):
            # Straight up a string. This should have been a ForwardRef, but lets not question it
            self.wrapper = None
            self.args = [self.obj, ]

        elif (isinstance(self.obj, Iterable)):
            # Could be the first arg of Callable etc.
            self.wrapper = None

            self.args = list(
                map(
                    type(self),
                    self.obj,
                )
            )
    
        elif (isinstance(self.obj, type)):
            # a Class object.
            self.wrapper = None

            if (inspect.getmodule(self.obj) is builtins):
                # Built-in types - name will do
                self.args = [ self.obj.__name__ ]
            else:
                # Otherwise, give it the qualified name
                self.args = [ ObjectDescription(self.obj).qualname ]

    @JSONDescriptionCachedProperty
    def markdown(self) -> str:
        """
        Generate a Markdown string describing the annotation.
        The generated string is not Python language; but instead more language neutral.

        e.g.
        ```python
        Union[
            List[Union[str, int]],
            Tuple[Union[str, "typing.Callable"]],
            Callable[[describe.function.FunctionDescription, float], None],
        ]
        ```
        will become:

        `List`[ `str` | `int` ] | `Tuple`[ `str` | `typing.Callable` ] | `Callable`[ [ `readme_compiler.describe.function.FunctionDescription`, `float` ], `None` ] | `None`
        """

        if (self.wrapper is Union):
            return " | ".join(
                map(
                    lambda arg: f"{arg.markdown if isinstance(arg, AnnotationDescription) else arg}",
                    self.args
                )
            )
        elif (
            isinstance(self.wrapper, PseudoAliasMeta)
        ):
            # PseudoAlias - we just ask the class to explain itself.
            return self.obj.markdown
        elif (
            len(self.args) <= 1 and \
            self.wrapper is None
        ):
            # A singular annotation class, or object.
            # Put the quotes on.
            return '`' + ', '.join(map(
                lambda arg: f"{arg.markdown if isinstance(arg, AnnotationDescription) else arg}",
                self.args
            )) + '`'
        else:
            _return = ", ".join(
                map(
                    lambda arg: f"{arg.markdown if isinstance(arg, AnnotationDescription) else arg}",
                    self.args
                )
            )
            
            if (self.wrapper):
                _return = f"`{self.wrapper.__name__.title() if not isinstance(self.wrapper, str) else self.wrapper}`[ {_return} ]"
            else:
                _return = f"[ {_return} ]"

            return _return
