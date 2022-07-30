import functools
import inspect

import typing
from typing import Any, Callable, Iterable, Optional



import readme_compiler.describe as describe

class JSONDescriptionElement():
    """
    Superclass to contain all elements to be exported in the JSON.
    """
    @classmethod
    def with_metadata_override(
        cls,
        func:Callable,
    )->Callable:
        """
        Decorator allowing method to overwrite data extracted from object with those provided in the JSON metadata.
        """
        @functools.wraps(func)
        def _wrapper(
            self:"describe.object.ObjectDescription",
            *args,
            **kwargs,
        )->Any:
            _metadata = getattr(self, "metadata", None)
            if (_metadata is None): _metadata = {}

            _return = func(self, *args, **kwargs)
                
            # we use hasattr here so that we allow None and "" overrides from metadata.
            if (func.__name__ in _metadata):
                _metadata_for_attr = _metadata.get(func.__name__, None)
                
                if (
                    isinstance(_return, Iterable) and \
                    not isinstance(_return, str) and \
                    any(
                        [
                            isinstance(_item, describe.object.ObjectDescription) \
                                for _item in _return
                        ]
                    )
                ):
                    # [ ObjectDescription(...), ObjectDescription(...), ... ]
                    for _item in _return:
                        if (isinstance(_item, describe.object.ObjectDescription)):
                            _item.metadata = _metadata_for_attr.get(_item.name, None)

                elif (isinstance(_return, describe.object.ObjectDescription)):
                    # 
                    _return.metadata = _metadata_for_attr
                else:
                    # Metadata exists, and return is scalar, then use the metadata instead.
                    if (isinstance(_metadata_for_attr, str)):
                        _return = inspect.cleandoc(_metadata_for_attr)
                    else:
                        _return = _metadata_for_attr

                    
                
            return _return

        # Remember to decorate the _wrapper with itself too! Otherwise no property for you.
        return cls(_wrapper)

class JSONDescriptionProperty(property, JSONDescriptionElement):
    """
    Wrapper around `property`.
    """

    @classmethod
    def as_stored_attribute(
        cls:"JSONDescriptionProperty",
        name:str,
        *,
        annotation:typing._GenericAlias = Optional[Any],
        default:Any = None,
        transform_fget:Callable[[Any, Optional[Any]], Any] = None,
        transform_fset:Callable[[Any, Optional[Any]], Any] = None,
    )->"JSONDescriptionProperty":
        """
        Create a new property with `fget`, `fset` and `fdel` setup to reference a hidden attribute.
        
        For example:
        ```python
        class MyClass():
            my_attr = JSONDescriptionProperty.as_stored_attribute("my_attr")
        ```
        will result in a hidden property called `MyClass._my_attr`, which stores the value of `my_attr`.

        NOT A DECORATOR.
        """
        _attr_name = "_"+str(name)
        def _fget(self)->annotation:
            _value = getattr(self, _attr_name, default)

            # Transform if specified
            if (callable(transform_fget)):
                _value = transform_fget(self, _value)

            return _value
        
        def _fset(self, value:annotation)->None:
            # Transform if specified
            if (callable(transform_fset)):
                value = transform_fset(self, value)

            setattr(self, _attr_name, value)

        def _fdel(self)->None:
            delattr(self, _attr_name)

        return cls(
            fget=_fget,
            fset=_fset,
            fdel=_fdel,
        )

class JSONDescriptionCachedProperty(functools.cached_property, JSONDescriptionElement):
    """
    Wrapper around `functools.cached_property`.
    """

class JSONDescriptionLRUCache(JSONDescriptionElement):
    """
    Wrapper around `functools.lru_cache`.

    Because `functools.lru_cache` is in fact a function, and `JSONDescriptionLRUCache` is a class, we have to do some massaging to make `JSONDescriptionLRUCache` behave like a function.
    This is further complicated by the fact that `functools.lru_cache` is in itself a direct decorator, able to overload with
    - a callable, decorating it, or
    - parameters like `maxsize` etc, which then generates  `lru_cache.<locals>.decorating_function` instance, which is then the decorator function.

    `JSONDescriptionLRUCache` addresses this by checking if the wrapped function it contains is fom the module functools, and is a local function from `lru_cache`.
    Then __call__ will decide whether it will wrap `*args` or call `_wrapped` directly.
    """
    _wrapped = None

    def __init__(
        self,
        *args,
        **kwargs,
    ) -> None:
        self._wrapped = functools.lru_cache(*args, **kwargs)

    @property
    def is_decorator(self) -> bool:
        return (
            inspect.getmodule(self._wrapped) is functools and \
            self._wrapped.__qualname__.startswith("lru_cache")
        ) # if the wrapped function remained a `lru_cache.<locals>.decorating_function`, that means it hasn't be called yet; flag it so `__call__` know what to do.

    def __get__(
        self,
        obj:Any,
        objtype:type=None,
        *args,
        **kwargs,
    ) -> Any:
        """
        Bound method mode.
        Triggered when:
        ```
        @JSONDescriptionLRUCache    # No args
        def decorated():
            ...
        ```
        In this context, `JSONDescriptionLRUCache` will
        - first use `__init__` to wrap around `decorated`; then
        - my_instance.decorated will be an `JSONDescriptionLRUCache` instance.
        - when myinstance.decorated is retrieved, `__get__` will trigger, and we return a decorated BOUND to myinstance.
        - then myinstance.decorated(*args, **kwargs) will pass the parameters into the resultant bound method.
        """
        if (obj is not None):
            # If this is an instance call
            return self._wrapped.__get__(obj)
        else:
            # If this is a class call
            return self

    def __call__(
        self,
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """
        Decorator mode.
        Triggered when:
        ```
        @JSONDescriptionLRUCache(some_args...)
        def decorated():
            ...
        ```
        In this context, `JSONDescriptionLRUCache` does not have a parent, so `__get__` won't trigger.
        """
        
        if (self.is_decorator):
            self._wrapped = self._wrapped(*args, **kwargs) # This returned the wrapped function without any reference to this `JSONDescriptionLRUCache` instance. This doesn't matter as we check `JSONDescriptionLRUCache` on the class, not instance.
            return self
        