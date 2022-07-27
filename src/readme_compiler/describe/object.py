import functools
import inspect
import re

from types import ModuleType, MethodType, MethodWrapperType, FunctionType, TracebackType, FrameType, CodeType
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type, Union, get_origin, get_args
import typing

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

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.qualname})"

    def __init__(
        self,
        obj:Callable,
        metadata: Dict[str, Any] = None,
    ) -> None:
        self.obj = obj
        self.metadata = metadata
    
    @JSONDescriptionCachedProperty
    def name(self) -> str:
        return self.obj.__name__
    
    @JSONDescriptionCachedProperty
    def qualname(self) -> str:
        if (_return := getattr(self.obj, "__qualname__", None)):
            if (getattr(self.obj, "__module__", None) and \
                self.obj.__module__ not in self.obj.__qualname__):

                _return = ".".join([
                    self.obj.__module__,
                    self.obj.__qualname__
                ])

        elif (_return := getattr(self.obj, "__name__", None)):
            pass
        elif (isinstance(self.obj, typing._GenericAlias)):
            _return = f"{get_origin(self.obj).__name__.title()}[{', '.join(map(str, get_args(self.obj)))}]"
        else:
            _return = None

        return _return

    @JSONDescriptionCachedProperty.with_metadata_override
    def doc(self) -> Union[str, None]:
        _doc = inspect.getdoc(self.obj)

        if (_doc):
            _doc = inspect.cleandoc(_doc)

        return _doc

    @JSONDescriptionCachedProperty.with_metadata_override
    def comments(self) -> Union[str, None]:
        return inspect.getcomments(self.obj)

    @JSONDescriptionCachedProperty
    def source(self) -> str:
        return inspect.getsource(self.obj)

    @property
    def json(self) -> Dict[str, str]:      
        return {
            _key:(getattr(self, _key) if (not isinstance(_construct, JSONDescriptionLRUCache)) else getattr(self, _key)()) \
                for _key in dir(self) \
                    if (isinstance(_construct := getattr(type(self), _key, None), JSONDescriptionElement)) # Make sure to getattr from type(self) - otherwise we `property`s would have returned the VALUE instead of itself!
        }

    @property
    def title(self) -> str:
        return f"{stdout.cyan(type(self).__name__)}{stdout.blue(' of ')}{stdout.cyan(self.obj)}{stdout.blue(' from module ')}{stdout.cyan(ObjectDescription(self.module).qualname)}"

    def explain(self, *, indent:int=0) -> None:
        print (" "*indent + self.title)
        print ("")
        for _key, _value in zip(self.json, self.json.values()):
            print (" "*indent + "- " +stdout.blue(_key) + ":")

            if (
                isinstance(_value, (list, tuple, set)) and \
                all(map(
                    lambda obj: isinstance(obj, ObjectDescription),
                    _value
                ))
            ):
                print ("")
                for _id, _obj in enumerate(_value):
                    _title = (" " + stdout.blue(_key) + "[] " + stdout.white(f"Element #{_id:,} ")).center(120, "-")
                    
                    print (" "*(indent+4)+_title+"\n"*2)

                    _obj.explain(indent=indent+4)
                    print ("\n")
            elif isinstance(_value, (str, list, dict, tuple, set, int, float)):
                print (" "*(indent+2) +str(_value).replace("\n", "\n"+" "*(indent+2)))
            elif (_value is None):
                print (" "*(indent+2) +stdout.magenta("None"))
            elif (isinstance(_value, type)):
                print (" "*(indent+2) +f"{stdout.yellow(_value.__name__)} class")
            else:
                print (" "*(indent+2) +f"{stdout.yellow(type(_value).__name__)} instance: {stdout.white(str(_value))}")
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
    def module(self)->ModuleType:
        """
        Guess the module where the object came from.
        """
        return inspect.getmodule(self.obj)
            
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

    @JSONDescriptionCachedProperty.with_metadata_override
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

    @JSONDescriptionCachedProperty.with_metadata_override
    def functions(self):
        """
        Return an Iterator of all children modules of object
        """
        return self.children(
            dunder=False,
            sunder=False,
            classes=(FunctionType, MethodType, MethodWrapperType, ),
            modules=[self.obj, ] if (isinstance(self.obj, ModuleType)) else None,   # Only search submodules of itself if its a module
        )
    