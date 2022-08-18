import os
import functools
import inspect
import json

import typing
from typing import Any, Callable, Dict, Iterable, Optional


import readme_compiler.stdout as stdout


import readme_compiler.describe as describe
import readme_compiler.describe.exceptions as exceptions


class JSONDescriptionElement():
    """
    Superclass to contain all elements to be exported in the JSON.
    """
    metadata_override:bool   = False

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
            if (not isinstance(_metadata, dict)): _metadata = {}

            _return = func(self, *args, **kwargs)
                
            if (func.__name__ in _metadata):

                _metadata_for_attr = _metadata.get(func.__name__, None)
                
                if (
                    isinstance(_return, Iterable) and \
                    not isinstance(_return, str) and \
                    (
                        any(
                            [
                                isinstance(_item, describe.object.ObjectDescription) \
                                    for _item in _return
                            ]
                        ) or \
                        len(_return) <= 0 # This is important - otherwise empty properties like `methods_descriptions` will get replaced by the `dict` in metadata!
                    )
                ):
                    # [ ObjectDescription(...), ObjectDescription(...), ... ]
                    for _item in _return:
                        if (isinstance(_item, describe.object.ObjectDescription)):
                            if (isinstance(_metadata_for_attr, dict)):
                                _item.metadata = _metadata_for_attr.get(_item.name, None)
                            else:
                                _item.metadata = _metadata_for_attr

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
        _property = cls(_wrapper)
        _property.metadata_override = True

        return _property

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
        
class DescriptionMetadata(dict):
    """
    ### Subclass of `dict` to store metadata for `Description` classes
    
    It knows of its own parent, so it knows where the metadata path etc is.
    The main purpose is to export and import metadata.
    """
    __parent__:"describe.object.ObjectDescription"

    def __init__(
        self,
        *args,
        parent:"describe.object.ObjectDescription" = None,
        skip_load:bool = False,
        **kwargs,
    ) -> None:
        """
        ### Initialise a `DescriptionMetadata` instance
        ...linking it to a `parent` object of `ObjectDescription` type.
        """
        self.parent = parent
        
        super().__init__(*args, **kwargs)

        # Load JSON sidecar only if we need to.
        # We'll leave it to the parent to decide if metadata is
        # - contained in sidecar, or
        # - deliberately empty
        if (not skip_load): self.load()

    def __repr__(self) -> str:
        return f"{type(self).__name__}({super().__repr__()}, parent={type(self.parent).__name__}({self.parent.qualname}))"
    
    @classmethod
    def empty(
        cls,
        parent:"describe.object.ObjectDescription" = None,
    ) -> "DescriptionMetadata":
        """
        ### Initialise an empty `DescriptionMetadata` instance.

        This will NOT load the sidecar JSON file.
        """
        return cls(
            parent      = parent,
            skip_load   = True,
        )

    @property
    def parent(self) -> "describe.object.ObjectDescription":
        return self.__parent__
    
    @parent.setter
    def parent(self, value:"describe.object.ObjectDescription") -> None:
        if (isinstance(value, describe.object.ObjectDescription)):
            self.__parent__ = value
        else:
            raise exceptions.ObjectDescriptionRequired(
                f"'ObjectDescription' instance expected for parent of 'DescriptionMetadata'; {repr(value)} found."
            )
        

    def from_parent(self) -> "DescriptionMetadata":
        """
        Update all attributes of the metadata from the parent object.
        """
        self.update(
            self.parent.as_export_dict
        )
        return self


    # ## This is not actually necessary - `with_metadata_override` already 
    # def merge_parent(self) -> "DescriptionMetadata":
    #     """
    #     Update this metadata with the parent's metadata, while not overriding any existing data.
    #     """
    #     _data = self.parent.as_export_dict

    #     _data.update(self)

    #     self.update(_data)

    #     return self

    def copy(self) -> "DescriptionMetadata":
        return type(self)(super().copy(), parent=self.parent)

    def export(
        self,
        store_external:Iterable[str] = ["classes_descriptions", "modules_descriptions"],
        *,
        merge:bool = True,
    ) -> None:
        """
        Export the current metadata to a file.
        """
        _return = self.copy()

        if (merge): _return.from_parent()

        def _export_items(obj:Any):
            if (isinstance(obj, describe.object.ObjectDescription)):
                if (merge): obj.metadata.from_parent()
                
                obj.metadata.export(store_external=store_external, merge=merge)
            elif (isinstance(obj, Iterable) and not isinstance(obj, str)):
                # dict check is correct here. as_export_dict converts all the lists into dicts.
                for _value in obj:
                    _export_items(_value)
            else:
                pass

        if (store_external):
            # Deal with all the attributes that are to be stored externally.
            # Typically specified for the "*_descriptions" properties, this allows modules and classes to have their own sidecar json metadata files in the correct folder.
            if (isinstance(store_external, str)): store_external = [store_external, ]

            for _external_attr in store_external:
                _external_obj = getattr(self.parent, _external_attr, None)
                
                if (_external_obj):
                    _export_items(_external_obj)
                    del _return[_external_attr]

        try:
            os.makedirs(os.path.dirname(self.parent.metadata_path), exist_ok=True)
            with open(self.parent.metadata_path, "w") as _f:
                json.dump(_return, _f, default=str, indent=4)

        except (TypeError, ) as e:
            # TypeError: Object of type ### is not JSON serializable
            # We can't do this Exception any better, it does not actually tell us what that object actually is
            raise e
        
        except (IOError, OSError, RuntimeError, IsADirectoryError) as e:
            print (stdout.red(f"### {type(e).__name__}: {str(e)}"))

        return None

    def load(
        self,
    ) -> Dict[str, Any]:
        """
        Import the metadata from the sidecar JSON.
        This is called automatically after a DescriptionMetadata instance is initialised.
        """
        if (self.parent.metadata_path):
            try:
                with open(self.parent.metadata_path, "r") as _f:
                    _data = json.load(_f)
                    
                self.update(_data)

            except (json.JSONDecodeError, ) as e:
                # TypeError: Object of type ### is not JSON serializable
                # We can't do this Exception any better, it does not actually tell us what that object actually is
                print (stdout.red(f"### Metadata file for {self.parent.qualname} is not well formatted JSON."))
                raise e
            
            except (IOError, OSError, RuntimeError, IsADirectoryError) as e:
                # print (stdout.yellow(f">>> No metadata file found for {self.parent.qualname}."))
                pass

        return self