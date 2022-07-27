import builtins
import inspect
import re
from types import SimpleNamespace, ModuleType, MethodType, FunctionType, TracebackType, FrameType, CodeType
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type, Union

from .. import stdout

from .json_elements import JSONDescriptionCachedProperty, JSONDescriptionLRUCache, JSONDescriptionProperty
from .object import ObjectDescription
from .function import FunctionDescription
from . import format

class ClassDescription(ObjectDescription):
    """
    An object representing the various properties of a class.
    """
    obj:type

    def __init__(
        self,
        obj: Callable,
        metadata: Dict[str, Any] = None,
        *,
        named_methods_only: bool = None,
    ) -> None:

        assert isinstance(obj, type), f"Cannot describe '{stdout.red(type(obj).__name__)}' - has to be a class object."

        super().__init__(obj, metadata)

        self.named_methods_only = named_methods_only

    @JSONDescriptionCachedProperty
    def ancestry(self) -> List[type]:
        return self.obj.__mro__

    @JSONDescriptionCachedProperty
    def init(self) -> Callable[[Any], None]:
        return self.obj.__init__
    
    @JSONDescriptionCachedProperty.with_metadata_override
    def init_description(self) -> FunctionDescription:
        return FunctionDescription(self.init)
    
    @JSONDescriptionCachedProperty
    def context(self) -> Tuple[
        Callable[[Any, Optional[Any]], None],  # __enter__
        Callable[[Any, Optional[Type[BaseException]], BaseException, TracebackType], bool],
    ]:
        return (getattr(self.obj, "__enter__", None), \
                getattr(self.obj, "__exit__", None), )

    @JSONDescriptionCachedProperty
    def iscontext(self) -> bool:
        """
        Return `True` if the class can act as a context manager.
        """
        return all(self.context)
    
    @JSONDescriptionCachedProperty.with_metadata_override
    def context_descriptions(self) -> FunctionDescription:
        _context_functions = self.context

        if (self.iscontext):
            return SimpleNamespace(
                enter = FunctionDescription(_context_functions[0]),
                exit = FunctionDescription(_context_functions[1]),
            )
        else:
            return SimpleNamespace(
                enter = None,
                exit = None,
            )

    @JSONDescriptionCachedProperty
    def call(self) -> Callable[[Any, Optional[Any]], Any]:
        return self.obj.__call__
    
    @JSONDescriptionCachedProperty.with_metadata_override
    def call_description(self) -> FunctionDescription:
        return FunctionDescription(self.call)

    @JSONDescriptionCachedProperty.with_metadata_override
    def methods_descriptions(self) -> List[FunctionDescription]:

        # By default, show all methods unless:
        # - metadata is provided and at least one member exists in `methods_descriptions`.
        named_methods_only = bool(self.metadata.get("methods_descriptions", {})) \
                                if (self.named_methods_only is None) \
                                else False

        _method_descriptions = map(
            FunctionDescription,
            self.functions
        )

        if (named_methods_only):
            _method_descriptions = filter(
                lambda _method_description: _method_description.name in self.metadata.get("methods_descriptions", {}),
                _method_descriptions
            )
        
        return list(_method_descriptions)