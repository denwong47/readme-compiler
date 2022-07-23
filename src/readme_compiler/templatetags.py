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
    if (isinstance(_respository := context.get("repository_object", None), classes.RepositoryDirectory)):
        # Make sure we are pointing to the rendered path (not very crucial)
        path = _respository.repopath.parse(path).source

        # This is always a dry_run because we are returning the value
        _return = _respository.render(path, dry_run = True)
    
    else:
        _return = "# * readme-compiler error: cannot embed without `RepositoryDirectory` instance * #"

    return django_setup.mark_safe(
        _return
    )