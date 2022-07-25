import inspect
import re
from types import ModuleType, MethodType, FunctionType, TracebackType, FrameType, CodeType
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type, Union

from .. import stdout

from .json_elements import JSONDescriptionCachedProperty, JSONDescriptionLRUCache, JSONDescriptionProperty
from .object import ObjectDescription
from . import format

class ParameterDescription(ObjectDescription):
    """
    Describe a parameter of a `function` or `method`.
    """
    obj:inspect.Parameter

    @JSONDescriptionCachedProperty
    def name(self) -> str:
        return self.obj.name
    
    @property
    def qualname(self) -> str:
        raise AttributeError(f"Parameter '{self.name}' does not have a qualified name.")