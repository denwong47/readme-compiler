"""
# Test Repo Name

This is a Test Python Module that does nothing.
It is simply for:
    - testing `readme_compiler.describe` module
    - testing python code formatting
    - testing markdown formatting
"""

import abc

from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type, Union, ForwardRef, get_origin, get_args, get_type_hints

from . import submodule_1
from . import submodule_2

my_attribute:int

def my_function()->str:
    """
    ### Demo Function

    This is a descriptino for Demo Function.
    - so function
    - much method
        - wow
    """
    return None

# My COmments
class MyClass(abc.ABC):
    """
    **Introduction to MyClass**
    
    Its not immensely useful.
    """

    my_attribute:str

    @abc.abstractproperty
    def my_abstract_property(self)->None:
        """
        Introducing:
        ## MY ABSTRACT PROPERTY!!!!!
        """
        pass

    @property
    def my_property(self)-> Union[List[str], Callable[["MyClass", int], property]]:
        pass

    @my_property.setter
    def my_property(self, weird_name:Union[float, map]):
        pass

    @abc.abstractmethod
    def my_abstract_method(self)->None:
        """
        ##### My Abstract Method

        I am useless
        """

    @classmethod
    def my_class_method(cls:Type["MyClass"], param_1:str)->"MyClass":
        """
        Call me a class method
        """
        return MyClass()

    def my_method(self:"MyClass", param_1:int, param_2:Union[float, Type["MyClass"]]):
        print (param_1, param_2)
        return "My Returned Value"