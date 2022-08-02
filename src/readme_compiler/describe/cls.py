import builtins
import inspect
import re
from types import   SimpleNamespace, \
                    ModuleType, \
                    MethodType, \
                    FunctionType, \
                    TracebackType, \
                    FrameType, \
                    CodeType, \
                    WrapperDescriptorType, \
                    MethodWrapperType, \
                    MethodDescriptorType
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type, Union

from .. import stdout

from .json_elements import JSONDescriptionCachedProperty, JSONDescriptionLRUCache, JSONDescriptionProperty
from .object import ObjectDescription
from .function import FunctionDescription

import readme_compiler.format as format

BuiltInMethodTypes = (
    WrapperDescriptorType,
    MethodWrapperType,
    MethodDescriptorType,
)
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
        _init_method = self.obj.__init__

        if (not isinstance(_init_method, BuiltInMethodTypes)):
            return _init_method
        else:
            # This means that __init__ is an inherited method from a built-in type,
            # e.g. `object.__init__`
            # This is not going to incredibly useful; so lets return `None`.
            return None
    
    @JSONDescriptionCachedProperty.with_metadata_override
    def init_description(self) -> FunctionDescription:
        if (callable(self.init)):
            # We have a valid __init__
            return FunctionDescription(self.init)
        else:
            # Fake __init__
            def __init__(self, *args, **kwargs)->None: return super().__init__(*args, **kwargs)
            __init__ = __init__.__get__(self.obj) # Manually bind the method to `obj`

            return FunctionDescription(__init__)
    
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

    @JSONDescriptionProperty.with_metadata_override
    def context_code(self) -> str:
        """
        By default there is no context_code - the only thing that can populate this is the metadata.
        """
        return None

    @JSONDescriptionProperty.with_metadata_override
    def context_doc(self) -> str:
        """
        By default there is no context_doc - the only thing that can populate this is the metadata.
        """
        return None


    @JSONDescriptionCachedProperty
    def call(self) -> Callable[[Any, Optional[Any]], Any]:
        return self.obj.__call__
    
    @JSONDescriptionCachedProperty.with_metadata_override
    def call_description(self) -> FunctionDescription:
        return FunctionDescription(self.call)

    @JSONDescriptionCachedProperty.with_metadata_override
    def kind_description(self) -> str:
        _describers = []

        if (self.isabstract):
            _describers.append("Abstract Base")
        
        if (issubclass(self.obj, type)):
            _describers.append( "Metaclass")
        else:
            _describers.append( "Class")

        return " ".join(_describers)


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