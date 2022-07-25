import functools
import inspect
import re

from types import ModuleType, MethodType, FunctionType, TracebackType, FrameType, CodeType
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type, Union

from .. import stdout

from ..log import logger

from .json_elements import  JSONDescriptionElement, \
                            JSONDescriptionCachedProperty, \
                            JSONDescriptionLRUCache, \
                            JSONDescriptionProperty

print = logger.info

class ObjectDescription():
    """
    Base Class for all Description classes.
    """
    obj:object

    def __init__(
        self,
        obj:Callable,
    ) -> None:
        self.obj = obj
    
    @JSONDescriptionCachedProperty
    def name(self) -> str:
        return self.obj.__name__
    
    @JSONDescriptionCachedProperty
    def qualname(self) -> str:
        if (_return := getattr(self.obj, "__qualname__", None)):
            if (self.obj.__qualname__ == self.obj.__name__ and \
                self.obj.__module__):

                _return = ".".join([
                    self.obj.__module__,
                    self.obj.__qualname__
                ])

        elif (_return := getattr(self.obj, "__name__")):
            pass
        else:
            _return = None

        return _return

    @JSONDescriptionCachedProperty
    def doc(self) -> Union[str, None]:
        _doc = inspect.getdoc(self.obj)

        if (_doc):
            _doc = inspect.cleandoc(_doc)

        return _doc

    @JSONDescriptionCachedProperty
    def comments(self) -> Union[str, None]:
        return inspect.getcomments(self.obj)

    @JSONDescriptionCachedProperty
    def source(self) -> str:
        return inspect.getsource(self.obj)

    @property
    def json(self) -> Dict[str, str]:      
        return {
            _key:(getattr(self, _key) if (not isinstance(_construct, JSONDescriptionLRUCache)) else getattr(self, _key)(self)) \
                for _key in dir(self) \
                    if (isinstance(_construct := getattr(type(self), _key, None), JSONDescriptionElement)) # Make sure to getattr from type(self) - otherwise we `property`s would have returned the VALUE instead of itself!
        }

    def explain(self) -> None:
        for _key, _value in zip(self.json, self.json.values()):
            print (stdout.blue(_key) + ":")

            if isinstance(_value, (str, list, dict, tuple, set, int, float)):
                print (_value)
            elif (_value is None):
                print (stdout.magenta("None"))
            else:
                print (f"{stdout.yellow(type(_value).__name__)} instance: {stdout.white(str(_value))}")
            print ("")

    def children(
        self,
        *,
        dunder:bool=True,
        sunder:bool=True,
        classes:Tuple[type]=None,
        modules:Tuple[ModuleType]=None,
    ) -> Iterable[Any]:
        """
        Get children of the object, filtered by the parameters specified.
        """

        for _attr in filter(
            # Filter
            lambda name: (
                # Double Underscores
                (
                    name.startswith("__") and \
                    name.endswith("__") and \
                    len(name)>4
                ) \
                    if dunder else True
            ) and (
                # Single Underscores
                (
                    name.startswith("_") and \
                    len(name)>1 and \
                    name[1]!="_"
                ) \
                    if sunder else True
            ),
            dir(self.obj)
        ):
            _value = getattr(self.obj, _attr)

            # If the value is not of the right class, skip it
            if (classes):
                if (not isinstance(_value, classes)): continue

            # If the value is not of the right module, skip it
            if (modules):
                
                modules = [ 
                    _module.__name__ if (isinstance(_module, ModuleType)) else _module \
                        for _module in modules
                ]

                if (not any(
                    map(
                        lambda _module_name: inspect.getmodule(_value).__name__.startswith(_module_name),
                        modules
                    )
                )): continue

            yield _value
            
    @JSONDescriptionCachedProperty
    def modules(self):
        """
        Return an Iterator of all children modules of object
        """
        return self.children(
            dunder=False,
            sunder=False,
            classes=(ModuleType, ),
            modules=[self.obj, ] if (isinstance(self.obj, ModuleType)) else None,   # Only search submodules of itself if its a module
        )

    @JSONDescriptionCachedProperty
    def classes(self):
        """
        Return an Iterator of all children modules of object
        """
        return self.children(
            dunder=False,
            sunder=False,
            classes=(type, ),
            modules=[self.obj, ] if (isinstance(self.obj, ModuleType)) else None,   # Only search submodules of itself if its a module
        )

    @JSONDescriptionCachedProperty
    def functions(self):
        """
        Return an Iterator of all children modules of object
        """
        return self.children(
            dunder=False,
            sunder=False,
            classes=(FunctionType, MethodType, ),
            modules=[self.obj, ] if (isinstance(self.obj, ModuleType)) else None,   # Only search submodules of itself if its a module
        )
    