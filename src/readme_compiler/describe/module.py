import inspect
import re
from types import ModuleType, MethodType, FunctionType, TracebackType, FrameType, CodeType
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type, Union

from .. import stdout

from .json_elements import JSONDescriptionCachedProperty, JSONDescriptionLRUCache, JSONDescriptionProperty
from .object import ObjectDescription
from . import format

class ModuleDescription(ObjectDescription):
    """
    Describe a module.
    """
    obj:ModuleType

    # .modules() already work 