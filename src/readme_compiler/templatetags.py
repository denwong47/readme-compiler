"""
DO NOT RENAME THIS FILE - THIS NAME IS THE DEFAULT GIVEN BY DJANGO
"""

from typing import Any, Callable, Dict, Iterable, List, Tuple, Type, Union

from django.template import Context as  DjangoContext, \
                            Template as DjangoTemplate

from . import django_setup
from .django_setup import register  # Required to avoid django.template.library.InvalidTemplateLibrary Exception

import readme_compiler.classes as classes

@django_setup.register.simple_tag(
    takes_context=True,
)
def embed(
    context:DjangoContext,
    path:Union[
        str,
        "classes.MarkdownTemplate",
    ],
)->str:
    """
    
    """
    return django_setup.mark_safe(
        f"Embedding path {repr(path)}."
    )