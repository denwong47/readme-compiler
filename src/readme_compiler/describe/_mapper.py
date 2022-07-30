"""
## _mapper Module

This is the actual interface that will be imported into `readme_compiler.__init__.py`.
"""

from types import SimpleNamespace

from .              import annotation   # For annotation.types

from .object        import ObjectDescription
from .annotation    import AnnotationDescription
from .function      import FunctionDescription
from .parameter     import ParameterDescription
from .cls           import ClassDescription
from .attribute     import AttributeDescription
from .module        import ModuleDescription

describe = SimpleNamespace(
    object      =   ObjectDescription,
    annotation  =   AnnotationDescription,
    function    =   FunctionDescription,
    parameter   =   ParameterDescription,
    type        =   ClassDescription,
    attribute   =   AttributeDescription,
    module      =   ModuleDescription,
)