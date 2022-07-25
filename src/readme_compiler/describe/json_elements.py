import functools
import inspect

from typing import Any

class JSONDescriptionElement():
    """
    Superclass to contain all elements to be exported in the JSON.
    """

class JSONDescriptionProperty(property, JSONDescriptionElement):
    """
    Wrapper around `property`.
    """

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
        
    def __call__(
        self,
        *args: Any,
        **kwargs: Any
    ) -> Any:

        if (self.is_decorator):
            self._wrapped = self._wrapped(*args, **kwargs)
            return self
        else:
            return self._wrapped(*args, **kwargs)