import builtins
import inspect
import re
from types import ModuleType 
import typing
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type, Union, ForwardRef, get_origin, get_args, get_type_hints

from .. import stdout

from .json_elements import JSONDescriptionCachedProperty, JSONDescriptionLRUCache, JSONDescriptionProperty
from .object import ObjectDescription
from .annotation import PropertyType
from .parameter import AnnotationDescription
from . import format

from . import exceptions

class AttributeDescription(ObjectDescription):
    """
    Description object for an attribute, or anything really.

    This class does not do any inspection or fetching - 
    this is basically a `SimpleNamespace` class with a bunch of passthrough properties, which can be set to anything.

    To be called by `ClassDescription` in particular, so that the attributes of a class can be queried at `class` level,
    before initialising `AttributeDescription`s to record them.
    """
    @property
    def obj(self)->Any:
        """
        `obj` for AttributeDescription is read-only.
        This is just the value of the target, retrieved using `getattr(self.parent, self.name)`.

        In a way, this is the least interesting aspect when describing an attribute.
        """
        return self.default

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join([ f'{_attr}={repr(getattr(self, _attr))}' for _attr in ('name', 'parent', 'comments', 'doc', 'annotation', 'metadata', ) ])})"

    name        = JSONDescriptionProperty.as_stored_attribute("name",       annotation=str)
    parent      = JSONDescriptionProperty.as_stored_attribute("parent",     annotation=Union[ModuleType, type])
    comments    = JSONDescriptionProperty.as_stored_attribute("comments",   annotation=str)
    doc         = JSONDescriptionProperty.as_stored_attribute("doc",        annotation=str)
    annotation  = JSONDescriptionProperty.as_stored_attribute("annotation", annotation=typing._GenericAlias)

    isproperty:bool =    False

    def __init__(
        self,
        parent:Union[type, ModuleType],
        name:str,
        comments:str                    = "",
        doc:str                         = "",
        annotation:typing._GenericAlias = Any,
        *,
        metadata: Dict[str, Any] = None
    ) -> None:
        """
        Initialise a Description object for an attribute.
        
        Fields are not automatic - these need to be provided by the caller, probably using `typing.get_type_hints()`.
        """
        self._name      =   name
        self._parent    =   parent
        self._comments  =   comments
        self._doc       =   doc
        self._annotation=   annotation      # This is not that simple - we have to look at @property as well

        self.metadata   =   metadata

        # Do not `super().__init__()` - `.obj` is read-only here!

    # Make sure AttributeDescription does not have attributes_description... this is especially true for PropertyDescriptions, as we can't really describe fget, fset and fdel.
    @property
    def attributes_descriptions(self):
        raise exceptions.AttributeNotApplicable(
            f"{type(self).__name__} type objects cannot have their attributes described."
        )

    @classmethod
    def getattr(
        cls:Type["AttributeDescription"],
        parent:Union[type, ModuleType],
        name:str,
        *,
        metadata: Dict[str, Any] = None,
    ) -> "AttributeDescription":
        """
        Get attribute from a parent object.
        Instead of calling `AttributeDescription` directly, which will require attribute values to be provided,
        `getattr` attempts to get the properties from its parent automatically instead.

        The attributes are stored - they will not update.

        Returns 
        - `PropertyDescription` instance if attribute is a property, and
        - `AttributeDescription` instance if otherwise.
        """
        if (not hasattr(parent, name)):
            raise exceptions.AttributeNotFound(
                f"Attribute '{name}' not found on parent object {repr(parent)} of type `{type(parent).__name__}`."
            )
        else:
            # This is just to find out if its a `property` - and you can't get that from instances.
            # So if parent is not a `class`, we have to look at the class.
            _constructor = getattr(
                parent if isinstance(parent, type) else type(parent),
                name
            )

            if (isinstance(_constructor, property)):
                # Ensure property get the PropertyDescription class
                if (not issubclass(cls, PropertyDescription)): cls = PropertyDescription
                _kwargs = {
                    "property": _constructor,
                }
            else:
                # ...while non-properties get the AttributeDescription class
                if (issubclass(cls, PropertyDescription)): cls = AttributeDescription
                _kwargs = {
                    "annotation": get_type_hints(parent).get(name, inspect._empty)
                }

            return cls(
                parent=parent,
                name=name,
                metadata=metadata,
                **_kwargs,
            )

    @JSONDescriptionCachedProperty
    def default(self)->Any:
        """
        Get the default value
        """

        if (not isinstance(self.parent, type)):
            _cls = type(self.parent)
        else:
            _cls = self.parent

        _has_type_hint  = get_type_hints(_cls).get(
                            self.name,
                            inspect._empty,
                          )
        _has_attr       = getattr(
                            _cls,
                            self.name,
                            
                          )

        if (not isinstance(_has_attr, exceptions.AttributeNotFound)):
            return _has_attr
        elif (_has_type_hint):
            return exceptions.AttributeTypeHintOnly(
                f"Attribute '{self.name}' exists only as a type hint in {repr(self.parent)}; it has no default value."
            )
        else:
            return exceptions.AttributeNotFound(
                f"Attribute '{self.name}' not found on parent object {repr(self.parent)} of type `{type(self.parent).__name__}`."
            )

    @JSONDescriptionCachedProperty
    def istypehint(self) -> bool:
        """
        Return `True` if the attribute only exists as a type hint.
        """
        return isinstance(
            self.default,
            exceptions.AttributeTypeHintOnly,
        )
    
    @JSONDescriptionProperty
    def source(self)->str:
        return f"{self.parent.__name__}.{self.name}:{self.annotation_description} = {repr(self.obj)}"

    @JSONDescriptionCachedProperty
    def annotation_description(self) -> AnnotationDescription:
        return AnnotationDescription(self.annotation)

    @JSONDescriptionCachedProperty.with_metadata_override
    def annotation_markdown(self) -> str:
        return self.annotation_description.markdown

class PropertyDescription(AttributeDescription):
    """
    """
    # This line is to reset `obj` to writable.
    obj:property    = None

    def __init__(
        self,
        parent:Union[type, ModuleType],
        name:str,
        # annotation:typing._GenericAlias = Any,
        property:property               = None,
        *,
        metadata: Dict[str, Any] = None
    ) -> None:
        """
        Initialise a Description object for a property object.
        
        Fields are not automatic - these need to be provided by the caller, probably using `typing.get_type_hints()`.
        """
        super().__init__(
            parent=parent,
            name=name,
            comments=None,
            doc=None,
            annotation=None,
            metadata=metadata
        )
        
        self.obj = property
    
    @JSONDescriptionProperty
    def fget(self) -> Callable[[Any], Any]:
        """
        Return the `getter` method of the property.
        """
        return self.obj.fget
    
    @JSONDescriptionProperty
    def fset(self) -> Callable[[Any], Any]:
        """
        Return the `setter` method of the property.
        """
        return self.obj.fset
    
    @JSONDescriptionProperty
    def fdel(self) -> Callable[[Any], Any]:
        """
        Return the `deleter` method of the property.
        """
        return self.obj.fdel

    @JSONDescriptionProperty
    def doc(self) -> Union[str, None]:
        return (
            # use self.metadata directly - fget is treated as trasparent
            super(AttributeDescription, self).doc or \
            ObjectDescription(self.fget, metadata=self.metadata).doc or \
            ObjectDescription(self.fset, metadata=self.metadata).doc or \
            ObjectDescription(self.fdel, metadata=self.metadata).doc
        )

    @JSONDescriptionProperty
    def annotation(self) -> PropertyType:
        return PropertyType.from_property(self.obj)

    @JSONDescriptionCachedProperty
    def source(self) -> str:
        _source = []
        if (self.fget): _source.append(inspect.getsource(self.fget))
        if (self.fset): _source.append(inspect.getsource(self.fset))
        if (self.fdel): _source.append(inspect.getsource(self.fdel))

        return "\n\n".join(map(
            inspect.cleandoc,
            _source
        ))

