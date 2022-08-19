import os, sys

import abc
import builtins
import functools
import inspect
import re

from types import ModuleType, MethodType, MethodWrapperType, FunctionType, TracebackType, FrameType, CodeType, SimpleNamespace
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type, Union, get_origin, get_args
import typing

from .. import settings
from .. import stdout
from .. import format

from ..log import logger

from . import exceptions
from .json_elements import  JSONDescriptionElement, \
                            JSONDescriptionCachedProperty, \
                            JSONDescriptionLRUCache, \
                            JSONDescriptionProperty, \
                            DescriptionMetadata

import readme_compiler.describe as describe

print = logger.debug

ATTRIBUTE_BLACKLIST = (
    "do_not_call_in_templates",
)

def tidy_annotations(obj:Any):
    """
    This aims to fix `|` in annotations that are not resolved.
    The object is changed in place.

    This enables get_type_hints to not error against 'bool | None' etc.
    """
    _annotations = getattr(obj, "__annotations__", None)

    if (_annotations is None): return

    _substitutes = {}

    def _try_load(type_hint:str):
        try:
            eval(type_hint, globals(), locals())
            return True
        except NameError as e:
            return False

    if (_annotations):
        for _key, _value in zip(_annotations.keys(), _annotations.values()):
            if (isinstance(_value, str)):
                if ("|" in _value):
                    _type_hints = tuple([ _type_hint.strip() for _type_hint in _value.split("|") ])

                    # After all that, there could still be weird type references further up the MRO that we do not have access to. In that case, make them `Any`.
                    if (
                        all(
                            map(
                                _try_load,
                                _type_hints,
                            )
                        )
                    ):
                        _substitutes[_key] = Union.__getitem__(
                            _type_hints
                        )
                    else:
                        _substitutes[_key] = Any
                else:
                    if (not _try_load(_value)):
                        _substitutes[_key] = Any

    if (_substitutes):
        _annotations.update(_substitutes)

def get_type_hints(obj:Any):
    """
    Wrapper around `typing.get_type_hints` to get around "|" in type hints causing `TypeError`.
    """
    tidy_annotations(obj)

    if (isinstance(obj, type)):
        for base in reversed(obj.__mro__):
            tidy_annotations(base)
            
    return typing.get_type_hints(obj)
    

class ObjectDescription():
    """
    Base Class for all Description classes.
    """
    obj:object

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.qualname})"

    def __init__(
        self,
        obj:Any,
        metadata: Dict[str, Any] = None,
    ) -> None:
        """
        ### Describe an `object`

        This is the most generic form of all Description objects, so if a more specific subclass is available, then that should be used instead.
        
        If `metadata` is a dict, it will take it as the `metadata` attribute, even if its empty.
        Otherwise, this will tell `DescriptionMetadata` to look for the sidecar JSON file and load it as metadata.

        """
        self.obj = obj
        
        # Weird thing in django.template.base:
        # - if your object is callable, it will attempt to call it witout any arguments.
        # - there is this hidden flag in the source code that allows you to skip it.
        try:
            self.obj.do_not_call_in_templates = True
        except AttributeError as e:
            pass
        
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
    def metadata(self) -> DescriptionMetadata:
        return self._metadata
    
    @metadata.setter
    def metadata(self, value:Union[dict, DescriptionMetadata]):
        if (isinstance(value, dict)):
            # If we already have a dict, then don't bother loading
            self._metadata = DescriptionMetadata(value, parent=self, skip_load=True)
        else:
            self._metadata = DescriptionMetadata({}, parent=self, skip_load=False)

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
        try:
            return inspect.getfile(self.obj)
        except (TypeError, ) as e:
            # TypeError: <class 'module'> is a built-in class
            # This will happen because `.type_description` exists, and `builtins.module` will be queried sooner or later.
            return ""

    @JSONDescriptionCachedProperty
    def folder_path(self) -> str:
        if (os.path.isdir(self.path)):
            return self.path
        else:
            return os.path.dirname(self.path)

    # This states metadata_override but it doesn't work.
    # This is added so that the dictionary knows the name of the key when exporting JSON.
    @JSONDescriptionCachedProperty.with_metadata_override
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
        return f"*{self.kind_description}* `{self.qualname}`"

    @JSONDescriptionCachedProperty
    def menu_anchor(self) -> str:
        return format.link_anchor(self.menu_item)

    @JSONDescriptionCachedProperty
    def parsed_doc(self) -> Dict[str, Union[str, None]]:
        if (not isinstance(
                _doc := self.metadata.get("doc", None),
                str
            )
        ):
            _doc = inspect.getdoc(self.obj)

        return format.split_title(
            _doc
        )

    @JSONDescriptionCachedProperty.with_metadata_override
    def comments(self) -> Union[str, None]:
        return inspect.getcomments(self.obj)

    @JSONDescriptionCachedProperty
    def source(self) -> str:
        try:
            return inspect.getsource(self.obj)
        except (OSError, ) as e:
            # OSError: could not find class definition
            return "**No Source Code Available**"

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
    def as_dict(self) -> Dict[str, str]:
        """
        Return all representations of this object as a dictionary.
        """
        return {
            _key:(getattr(self, _key) if (not isinstance(_construct, JSONDescriptionLRUCache)) else getattr(self, _key)()) \
                for _key in dir(self) \
                    if (isinstance(_construct := getattr(type(self), _key, None), JSONDescriptionElement)) # Make sure to getattr from type(self) - otherwise we `property`s would have returned the VALUE instead of itself!
        }
    
    @property
    def as_export_dict(self) -> Dict[str, str]:
        """
        Return the representation of this object 
        """
        def _nested_export(key_obj:Union[str, Any]) -> Any:
            if (isinstance(key_obj, str)):
                construct   = getattr(type(self), key_obj, None)
                obj         = getattr(self, key_obj, None)
                key         = key_obj
            else:
                construct   = None
                obj         = key_obj
                key         = None


            if (isinstance(construct, JSONDescriptionLRUCache)):
                return obj()
            elif (isinstance(obj, ObjectDescription)):
                return obj.as_export_dict
            elif (isinstance(obj, Iterable) and not isinstance(obj, str)):
                if (key.endswith("_descriptions")):
                    # This is for all the "attribute_scriptions", "parameters_descriptions" etc.
                    # In the metadata, these lists need to be converted into `dict`s with the name of the attribute as key.
                    return {
                        _item.name if (isinstance(_item, ObjectDescription)) else _item:_nested_export(_item) \
                            for _item in obj
                    }
                else:
                    return [ _nested_export(_item) for _item in obj ]
            else:
                return obj

        return {
            _key:_nested_export(_key) \
                for _key in dir(self) \
                    if (
                        isinstance(_construct := getattr(type(self), _key, None), JSONDescriptionElement) and \
                        _construct.metadata_override
                    ) # Make sure to getattr from type(self) - otherwise we `property`s would have returned the VALUE instead of itself!
        }

    @property
    def caption(self) -> str:
        """
        For printing only - used in `.explain()`.
        """
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
        for _key, _value in zip(self.as_dict, self.as_dict.values()):
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
            ) and (
                # Django callable override
                not name in ATTRIBUTE_BLACKLIST
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
        
            else:
                # if no modules are provided, at least remove the builtins.
                if (inspect.getmodule(_value) is builtins): continue


            # Switch lambda function names with their attribute names
            if (callable(_value) and _value.__name__ in ("<lambda>", "<locals>")):
                _value.__name__ = _attr
            
            yield _value

    @JSONDescriptionCachedProperty
    def module(self)->ModuleType:
        """
        Guess the module where the object came from.
        """
        return inspect.getmodule(self.obj)
            
    @JSONDescriptionProperty
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
            filter(
                lambda description: not isinstance(
                                        self.metadata.get(
                                            "modules_descriptions",
                                            None
                                        ),
                                        dict,
                                    ) or \
                                    description.name in self.metadata.get(
                                        "modules_descriptions",
                                        []
                                    ),
                map(
                    describe.module.ModuleDescription,
                    self.modules
                )
            )
        )

    @JSONDescriptionProperty
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

    @JSONDescriptionProperty
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
                lambda func: describe.function.FunctionDescription(
                    func,
                    parent = self,
                ),
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
            # attribute blacklist; to do with django built in attributes.
            if (name in ATTRIBUTE_BLACKLIST): return False

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
            try:
                if (
                    # Make sure it has the attribute - otherwise we might get all the type_hints out
                    hasattr(self.obj, name) and \
                    isinstance(
                        getattr(self.obj, name, inspect._empty),
                        REMOVE_TYPES
                    )
                ): return False
            except KeyboardInterrupt as e:
                return input(f"Include {self.qualname}.{name} as attribute? [Y/N] ").lower().startswith("Y")

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

        try:
            _attrs = set(
                dir(self.obj) + list(get_type_hints(self.obj).keys())
            )
        except (TypeError, ) as e:
            if ("unsupported operand type(s)" in str(e)):
                raise exceptions.ObjectNotDescribable(f"{self.obj} have incompatible Type hints: {str(e)}")
            else:
                raise e

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

    