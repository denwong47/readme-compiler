import functools
import inspect
import re

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
        return self.obj.__qualname__

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