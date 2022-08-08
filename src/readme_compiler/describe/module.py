import os, sys

import inspect
import re
from types import ModuleType, MethodType, FunctionType, TracebackType, FrameType, CodeType
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type, Union


from .json_elements import JSONDescriptionCachedProperty, JSONDescriptionLRUCache, JSONDescriptionProperty
from .object import ObjectDescription

class ModuleDescription(ObjectDescription):
    """
    Describe a module.
    """
    obj:ModuleType

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
        if (not self.is_init):
            return os.path.join(
                self.folder_path,
                f".readme/submodule.{self.name}.md",
            )
        else:
            return os.path.join(
                self.folder_path,
                f"README.md",
            )

    @JSONDescriptionCachedProperty
    def readme_exists(self) -> str:
        return os.path.exists(self.readme_path)