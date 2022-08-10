import os, sys

import abc
import functools
import inspect
import re

from types import ModuleType, MethodType, MethodWrapperType, FunctionType, TracebackType, FrameType, CodeType
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type, Union, get_origin, get_args, get_type_hints
import typing

from .. import settings
from .. import stdout
from .. import format

from ..log import logger

from . import exceptions
from .json_elements import  JSONDescriptionElement, \
                            JSONDescriptionCachedProperty, \
                            JSONDescriptionLRUCache, \
                            JSONDescriptionProperty

import readme_compiler.describe as describe

print = logger.debug

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

    @JSONDescriptionProperty
    def descriptor(self) -> str:
        """
        A lower case string for the current class of `Description`.

        This will be used:
        - as prefix of the metadata JSONs (cls.forestreet_job_monitoring.Job.metadata.json)
        - as the name of the principle variable inside the matching template (template.cls.md)

        This gives a baseline property that works for most of the `Description` classes, except `ClassDescription` that has to use `cls` to avoid using keyword `class`.
        """
        return type(self).__name__.lower().replace("description", "")

    @property
    def metadata(self) -> dict:
        return self._metadata
    
    @metadata.setter
    def metadata(self, value:dict):
        if (value):
            self._metadata = value
        else:
            self._metadata = {}

    @JSONDescriptionProperty
    def metadata_path(self) -> str:
        """
        Return the DEFAULT path of the metadata for this object.
        If `metadata` is supplied at `__init__` stage, then this property is used for saving metadata only.
        """
        try:
            return os.path.abspath(os.path.join(
                self.folder_path,
                f"./{settings.README_SOURCE_DIRECTORY}/"+\
                     settings.README_METADATA_DIRECTORY.format(
                        descriptor  = self.descriptor,
                        qualname    = self.qualname,
                    )
            ))
        except exceptions.AttributeNotApplicable as e:
            return None

    @JSONDescriptionCachedProperty
    def path(self) -> str:
        return inspect.getfile(self.obj)

    @JSONDescriptionCachedProperty
    def folder_path(self) -> str:
        if (os.path.isdir(self.path)):
            return self.path
        else:
            return os.path.dirname(self.path)

    @JSONDescriptionCachedProperty
    def name(self) -> str:
        return self.obj.__name__
    
    @JSONDescriptionCachedProperty
    def qualname(self) -> str:
        IGNORE_PREFIXES = (
            "__main__",
            "builtins"
        )

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

        if (
            isinstance(_return, str) and \
            (_split_return := _return.split(".", 1))[0] in IGNORE_PREFIXES and \
            len(_split_return) > 1
        ):
            # Remove __main__. and builtins. from qualname - those are not necessary.
            _return = _split_return[1]

        return _return

    @JSONDescriptionCachedProperty.with_metadata_override
    def doc(self) -> Union[str, None]:
        _doc = self.parsed_doc.get("body", None)

        if (_doc):
            _doc = inspect.cleandoc(_doc)

        return _doc

    @JSONDescriptionCachedProperty.with_metadata_override
    def title(self) -> Union[str, None]:
        return self.parsed_doc.get("title", None)

    @JSONDescriptionProperty
    def kind_description(self) -> str:
        return "Object"

    @JSONDescriptionCachedProperty
    def menu_item(self) -> str:
        return f"{self.kind_description} `{self.qualname}`"

    @JSONDescriptionCachedProperty
    def menu_anchor(self) -> str:
        return format.link_anchor(self.menu_item)

    @JSONDescriptionCachedProperty
    def parsed_doc(self) -> Dict[str, Union[str, None]]:
        return format.split_title(
            inspect.getdoc(self.obj)
        )

    @JSONDescriptionCachedProperty.with_metadata_override
    def comments(self) -> Union[str, None]:
        return inspect.getcomments(self.obj)

    @JSONDescriptionCachedProperty
    def source(self) -> str:
        return inspect.getsource(self.obj)

    @JSONDescriptionProperty
    def isabstract(self) -> bool:
        """
        Return `True` if the object is markes as abstract by `abc`.
        """
        return \
            inspect.isabstract(self.obj) or \
            isinstance(self.obj, (
                abc.abstractclassmethod,
                abc.abstractproperty,
                abc.abstractstaticmethod,
                abc.ABCMeta,
            )) or \
            getattr(self.obj, "__isabstractmethod__", False) # check if @abc.abstractmethod has done something to the function.

    @property
    def json(self) -> Dict[str, str]:      
        return {
            _key:(getattr(self, _key) if (not isinstance(_construct, JSONDescriptionLRUCache)) else getattr(self, _key)()) \
                for _key in dir(self) \
                    if (isinstance(_construct := getattr(type(self), _key, None), JSONDescriptionElement)) # Make sure to getattr from type(self) - otherwise we `property`s would have returned the VALUE instead of itself!
        }

    @property
    def caption(self) -> str:
        return f"{stdout.cyan(type(self).__name__)}{stdout.blue(' of ')}{stdout.cyan(self.obj)}{stdout.blue(' from module ')}{stdout.cyan(ObjectDescription(self.module).qualname)}"

    @JSONDescriptionProperty
    def type(self) -> Type:
        return type(self.obj)

    @JSONDescriptionProperty
    def type_description(self) -> Type:
        return describe.cls.ClassDescription(self.type)

    def explain(self, *, indent:int=0) -> None:
        print = logger.info

        print (" "*indent + self.caption)
        print ("")
        for _key, _value in zip(self.json, self.json.values()):
            print (" "*indent + "- " +stdout.blue(_key) + ":")

            # Expand generators
            if (
                isinstance(
                    _value, 
                    (map, filter,)
                ) or \
                inspect.isgenerator(_value)
            ):
                _expanded_value = list(_value)
            else:
                _expanded_value = _value

            if (
                isinstance(_expanded_value, (list, tuple, set)) and \
                all(map(
                    lambda obj: isinstance(obj, ObjectDescription),
                    _expanded_value
                ))
            ):
                print ("")
                for _id, _obj in enumerate(_expanded_value):
                    _title = (" " + stdout.blue(_key) + "[] " + stdout.white(f"Element #{_id:,} ")).center(120, "-")
                    
                    print (" "*(indent+4)+_title+"\n"*2)

                    _obj.explain(indent=indent+4)
                    print ("\n")
            elif (
                isinstance(_expanded_value, (str, list, dict, tuple, set, int, float,))
            ):
                print (
                    " "*(indent+2) +\
                    str(
                        _expanded_value
                    ).replace(
                        "\n",
                        "\n"+" "*(indent+2) # Add our own indentation
                    )
                )

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
        classes:Tuple[Type]=None,
        modules:Tuple[ModuleType]=None,
    ) -> Iterable[Any]:
        """
        Get children of the object, filtered by the parameters specified.
        """

        for _attr in filter(
            # Filter
            lambda name: (
                # Double Underscores
                not (
                    name.startswith("__") and \
                    name.endswith("__") and \
                    len(name)>4
                ) \
                    if (not dunder) else True
            ) and (
                # Single Underscores
                not (
                    name.startswith("_") and \
                    len(name)>1 and \
                    name[1]!="_"
                ) \
                    if (not sunder) else True
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
    def modules_descriptions(self):
        """
        Return an Iterator of descriptions of all children modules of object
        """
        return list(
            map(
                describe.module.ModuleDescription,
                self.modules
            )
        )

    @JSONDescriptionCachedProperty
    def classes(self):
        """
        Return an Iterator of all children classes of object
        """
        return self.children(
            dunder=False,
            sunder=False,
            classes=(type, ),
            modules=[self.obj, ] if (isinstance(self.obj, ModuleType)) else None,   # Only search submodules of itself if its a module
        )
    
    @JSONDescriptionCachedProperty.with_metadata_override
    def classes_descriptions(self):
        """
        Return an Iterator of descriptions of all children classes of object
        """
        return list(
            map(
                describe.cls.ClassDescription,
                self.classes
            )
        )

    @JSONDescriptionCachedProperty
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

    @JSONDescriptionCachedProperty.with_metadata_override
    def functions_descriptions(self):
        """
        Return an Iterator of descriptions of all children modules of object
        """
        return list(
            map(
                describe.function.FunctionDescription,
                self.functions
            )
        )
     
    # Don't cache this - its a map object. If you cache it, it will returned the last exhausted Generator!
    @JSONDescriptionProperty.with_metadata_override
    def attributes_descriptions(self):
        """
        Return an Iterator of all children attributes which are not modules, classes and functions.
        """

        REMOVE_TYPES = (
            ModuleType,
            type,
            FunctionType,
            MethodType,
            MethodWrapperType,
        )

        dunder:bool = False
        sunder:bool = False

        def _valid_attributes(name:str):
            # dunder
            if (not dunder and (
                name.startswith("__") and \
                name.endswith("__") and \
                len(name)>4
            )): return False
            
            # sunder
            if (not sunder and (
                name.startswith("_") and \
                len(name)>1 and \
                name[1] != "_"
            )): return False

            # REMOVE_TYPES
            if (
                # Make sure it has the attribute - otherwise we might get all the type_hints out
                hasattr(self.obj, name) and \
                isinstance(
                    getattr(self.obj, name, inspect._empty),
                    REMOVE_TYPES
                )
            ): return False

            # Belongs to module if self.obj is a module
            if (
                # Make sure it has the attribute - otherwise we might get all the type_hints out
                hasattr(self.obj, name) and \
                isinstance(self.obj, ModuleType)
            ):
                if (
                    inspect.getmodule(
                        getattr(self.obj, name)
                    ) is not \
                    self.obj
                ):
                    return False

            return True

        _attrs = set(
            dir(self.obj) + list(get_type_hints(self.obj).keys())
        )

        _metadata = self.metadata if (self.metadata) else {}

        return list(map(
            lambda attr: describe.attribute.AttributeDescription.getattr(
                parent      =   self.obj,
                name        =   attr,
                # comments    =   _metadata.get(attr, {}).get("comments", None),
                # doc         =   _metadata.get(attr, {}).get("doc", None),
                # annotation  =   get_type_hints(self).get(attr, inspect._empty),
                metadata    =   _metadata.get(attr, None)
            ),
            filter(
                _valid_attributes,
                _attrs,
            )
        ))

    