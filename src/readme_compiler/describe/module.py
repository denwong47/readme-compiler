import os, sys

import inspect
import re
from types import ModuleType
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type, Union


from .json_elements import JSONDescriptionCachedProperty, JSONDescriptionLRUCache, JSONDescriptionProperty
from .object import ObjectDescription

MODULE_TYPES = (ModuleType, )

# importing one level up - be careful with this!
import readme_compiler.settings as settings
class ModuleDescription(ObjectDescription):
    """
    Describe a module.
    """
    obj:MODULE_TYPES

    @JSONDescriptionProperty
    def kind_description(self) -> str:
        return "Module"

    @JSONDescriptionCachedProperty
    def is_init(self) -> str:
        return self.path.endswith("/__init__.py")
    
    @JSONDescriptionCachedProperty
    def is_main(self) -> str:
        return self.path.endswith("/__main__.py")

    @JSONDescriptionCachedProperty
    def readme_path(self) -> str:
        return os.path.abspath(os.path.join(
            self.folder_path,
            self.readme_link,
        ))
    
    @JSONDescriptionCachedProperty
    def readme_exists(self) -> str:
        return os.path.exists(self.readme_path)

    @JSONDescriptionCachedProperty
    def readme_link(self) -> str:
        """
        
        """
        if (not self.is_init):
            return f"./{settings.README_RENDERED_DIRECTORY}/submodule.{self.name}.md"
        else:
            return f"./{settings.README_RENDERED_INDEX}"

    @JSONDescriptionProperty
    def metadata_path(self) -> str:
        """
        Return the DEFAULT path of the metadata for this object.
        If `metadata` is supplied at `__init__` stage, then this property is used for saving metadata only.
        """
        if (not self.is_init):
            return super().metadata_path
        else:
            return os.path.abspath(os.path.join(
                self.folder_path,
                "./"+settings.README_METADATA_INDEX,
            ))