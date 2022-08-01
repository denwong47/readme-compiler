"""
## Describe Module

Inspect available objects, functions, classes and modules together with their associated parameters and attributes.

NOTE This module is not directly imported into `readme_compiler.__init__.py`;
see `_mapper.py` for the actual interface.
"""


from . import json_elements

from . import object
from . import annotation
from . import function
from . import parameter
from . import cls
from . import attribute
from . import module
