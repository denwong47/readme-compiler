"""
## _mapper Module

This is the actual interface that will be imported into `readme_compiler.__init__.py`.
"""

import builtins
from typing import Any, Dict

from .              import annotation   # For annotation.types

from .object        import  ObjectDescription
from .annotation    import  AnnotationDescription, \
                            ANNOTATION_TYPES
from .function      import  FunctionDescription, \
                            FUNCTION_TYPES
from .parameter     import  ParameterDescription, \
                            PARAMETER_TYPES
from .cls           import  ClassDescription, \
                            CLASS_TYPES
from .attribute     import  AttributeDescription
from .module        import  ModuleDescription, \
                            MODULE_TYPES

class describe():
    """
    ### Description object collections

    Returns an instance of `ObjectDescription`, or one of its subclasses,
    having analysed its contents.

    This class cannot have any instances.
    Call `describe(obj)` as though its a function.
    """

    object:builtins.type        =   ObjectDescription
    annotation:builtins.type    =   AnnotationDescription
    function:builtins.type      =   FunctionDescription
    parameter:builtins.type     =   ParameterDescription
    type:builtins.type          =   ClassDescription
    attribute:builtins.type     =   AttributeDescription
    module:builtins.type        =   ModuleDescription

    def __new__(
        cls,
        obj:Any,
        metadata: Dict[str, Any] = None,
    )->ObjectDescription:
        """
        ### Describe an object

        Returns an instance of `ObjectDescription`, or one of its subclasses,
        having analysed its contents.
        """
        
        if (isinstance(obj, CLASS_TYPES)):
            return cls.type(obj, metadata=metadata)
        elif (isinstance(obj, FUNCTION_TYPES)):
            return cls.function(obj, metadata=metadata)
        elif (isinstance(obj, MODULE_TYPES)):
            return cls.module(obj, metadata=metadata)
        elif (isinstance(obj, PARAMETER_TYPES)):
            return cls.parameter(obj, metadata=metadata)
        elif (isinstance(obj, ANNOTATION_TYPES)): # This includes `type` - cannot be placed above class.
            return cls.annotation(obj, metadata=metadata)
        else:
            # Fallback
            return cls.object(obj, metadata=metadata)