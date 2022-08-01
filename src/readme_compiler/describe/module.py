import inspect
import re
from types import ModuleType, MethodType, FunctionType, TracebackType, FrameType, CodeType
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type, Union


from .json_elements import JSONDescriptionCachedProperty, JSONDescriptionLRUCache, JSONDescriptionProperty
from .object import ObjectDescription

class ModuleDescription(ObjectDescription):
    """
    Describe a module.
    """
    obj:ModuleType

    