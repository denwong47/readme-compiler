import builtins
import inspect
import re
from types import ModuleType, MethodType, FunctionType, TracebackType, FrameType, CodeType, GenericAlias 
import typing
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type, Union, ForwardRef, get_origin, get_args

from .. import stdout

from .json_elements import JSONDescriptionCachedProperty, JSONDescriptionLRUCache, JSONDescriptionProperty
from .object import ObjectDescription
from . import format


class AnnotationDescription(ObjectDescription):
    """
    Describe an Annotation with simplified language.
    """
    wrapper:Type[GenericAlias]
    args:List[str]

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
        self.obj = annotation
        
        if (self.obj is None or self.obj is type(None)):
            self.wrapper = None
            self.args = [ "None", ]

        elif (isinstance(self.obj, ForwardRef)):
            # ForwardRef('classes.MarkdownTemplate')
            self.wrapper = None
            self.args = [self.obj.__forward_arg__, ]

        elif (isinstance(self.obj, typing._GenericAlias)):
            # Union/Iterable/Callable[] etc
            self.wrapper = get_origin(self.obj)

            self.args = list(
                map(
                    type(self),
                    get_args(self.obj),
                )
            )

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
                _return = f"`{self.wrapper.__name__.title()}`[ {_return} ]"
            else:
                _return = f"[ {_return} ]"

            return _return


class ParameterDescription(ObjectDescription):
    """
    Describe a parameter of a `function` or `method`.
    """
    obj:inspect.Parameter

    def __repr__(self) -> str:
        return f"{type(self).__name__}(<{self.kind_description} '{self.name}'>)"

    @JSONDescriptionCachedProperty
    def name(self) -> str:
        return self.obj.name
    
    @property
    def qualname(self) -> str:
        raise AttributeError(f"Parameter '{self.name}' does not have a qualified name.")

    @JSONDescriptionCachedProperty.with_metadata_override
    def doc(self) -> Union[str, None]:
        return f"{self.kind_description} of type: {self.annotation_markdown}."

    @property
    def source(self) -> str:
        raise AttributeError(f"Parameter '{self.name}' does not have a source code.")

    @JSONDescriptionCachedProperty
    def kind(self) -> inspect._ParameterKind:
        return self.obj.kind
    
    @JSONDescriptionCachedProperty
    def kind_description(self) -> str:
        _descriptors = []

        _descriptors.append("Optional" if (self.optional) else "Mandatory")
        if (self.position_description): _descriptors.append(self.position_description)
        _descriptors.append("Parameter")

        return " ".join(_descriptors)

    @JSONDescriptionCachedProperty
    def optional(self) -> bool:
        return not (self.obj.default is inspect.Parameter.empty)

    @JSONDescriptionCachedProperty.with_metadata_override
    def position_description(self) -> str:
        if (self.kind is inspect.Parameter.VAR_POSITIONAL):
            return "Positional-Only"
        elif (self.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD):
            return None
        elif (self.kind is inspect.Parameter.VAR_POSITIONAL):
            return "Collection of Positsional"
        elif (self.kind is inspect.Parameter.VAR_KEYWORD):
            return "Collection of Named"
        elif (self.kind is inspect.Parameter.VAR_POSITIONAL):
            return "Named"
    
    @JSONDescriptionCachedProperty
    def annotation(self) -> str:
        return self.obj.annotation

    @JSONDescriptionCachedProperty
    def annotation_description(self) -> AnnotationDescription:
        return AnnotationDescription(self.annotation)

    @JSONDescriptionCachedProperty.with_metadata_override
    def annotation_markdown(self) -> str:
        return self.annotation_description.markdown