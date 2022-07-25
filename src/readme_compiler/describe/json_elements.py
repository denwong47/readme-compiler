import functools
import inspect

from typing import Any, Callable

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
        