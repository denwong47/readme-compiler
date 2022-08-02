import builtins
import inspect
import re
from types import ModuleType, MethodType, FunctionType, TracebackType, FrameType, CodeType, GenericAlias 
import typing
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type, Union, ForwardRef, get_origin, get_args

from .. import stdout
from . import exceptions

from .json_elements import JSONDescriptionCachedProperty, JSONDescriptionLRUCache, JSONDescriptionProperty
from .object import ObjectDescription
from .annotation import AnnotationDescription


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
        raise exceptions.AttributeNotApplicable(f"Parameter '{self.name}' does not have a qualified name.")

    @JSONDescriptionCachedProperty.with_metadata_override
    def doc(self) -> Union[str, None]:
        return f"{self.kind_description} of type: {self.annotation_markdown}."

    @JSONDescriptionCachedProperty
    def parsed_doc(self) -> Dict[str, Union[str, None]]:
        return {}

    @property
    def source(self) -> str:
        raise exceptions.AttributeNotApplicable(f"Parameter '{self.name}' does not have a source code.")

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

    @property
    def modules_descriptions(self):
        raise exceptions.AttributeNotApplicable(
            f"{type(self).__name__} type objects cannot have their attributes described."
        )

    @property
    def functions_descriptions(self):
        raise exceptions.AttributeNotApplicable(
            f"{type(self).__name__} type objects cannot have their attributes described."
        )

    @property
    def classes_descriptions(self):
        raise exceptions.AttributeNotApplicable(
            f"{type(self).__name__} type objects cannot have their attributes described."
        )

    @property
    def attributes_descriptions(self) -> str:
        raise exceptions.AttributeNotApplicable(f"Parameter '{self.name}' does not have attributes.")