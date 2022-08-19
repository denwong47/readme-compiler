"""
DO NOT RENAME THIS FILE - THIS NAME IS THE DEFAULT GIVEN BY DJANGO
"""

from datetime import datetime
import importlib
import pytz
from typing import Any, Callable, Dict, Iterable, List, Tuple, Type, Union

from django.template import Context as  DjangoContext, \
                            Template as DjangoTemplate

from . import django_setup
from .django_setup import register  # Required to avoid django.template.library.InvalidTemplateLibrary Exception

import readme_compiler

from . import bin, classes, settings, stdout
from .settings.enums import RenderPurpose

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
    if (isinstance(_repository := context.get("repository_object", None), classes.RepositoryDirectory)):
        # Make sure we are pointing to the rendered path (not very crucial)
        path = _repository.repopath.parse(path).source

        # This is always a dry_run because we are returning the value
        _return = _repository.render(path, dry_run = True, purpose=RenderPurpose.EMBED)
    
    else:
        _return = "# * readme-compiler error: cannot embed without `RepositoryDirectory` instance * #"

    return django_setup.mark_safe(
        _return
    )

@django_setup.register.simple_tag(
    takes_context=True,
)
def current_time(
    context:DjangoContext,
    format_string:str="%Y-%m-%d %I:%M %p",
    timezone:str="UTC"
):
    tz = pytz.timezone(timezone)
    return f"{datetime.now(tz=tz).strftime(format_string)} {tz.zone}"

@django_setup.register.simple_tag(
    takes_context=True,
)
def logo(
    context:DjangoContext,
    alt_text:str="Logo",
    **kwargs,
):
    """
    Insert a logo.
    """
    if (isinstance(_repository := context.get("repository_object", None), classes.RepositoryDirectory)):
        path = _repository.repopath.abspath(_repository.repopath.parse(settings.LOGO_URL).source)
        
        with open(path, "r") as _f:
            _url = _f.read().format(**kwargs)
        
        return django_setup.mark_safe(f"![{alt_text}]({_url})")


@django_setup.register.simple_tag(
    takes_context=True,
)
def describe(
    context:DjangoContext,
    template:str,
    *,
    obj:str,
    source:str=None,
    metadata:Dict[str, Any]=None,
):
    """
    ### `describe` an object using a template.

    This template tag can dynamically import modules and their attributes, then describe it.

    Usage:
    ```
    {% describe 'module' obj='MyClass' source='test_repo' %}
    ```
    """

    # print (stdout.blue(
    #     [template,
    #     obj,
    #     source,
    #     metadata]
    # ))

    if (not isinstance(obj, readme_compiler.describe.object)):
        obj = bin.get_object(
            obj     = obj,
            source  = source,
            globals = globals(),
            locals  = context,
        )

        # `template` here is:
        # - 'module'
        # - 'cls'
        # - 'method'
        # etc.
        # 
        # This HAS to be the same as
        # - the template file name i.e. template.*.md, AND
        # - the object name being used INSIDE the template.
        # 
        # i.e. do not reinvent them.
        context[template] = readme_compiler.describe(
            obj,
            metadata=metadata,
        )   # Add the Description object to the context.
    else:
        # We already have a description object - save some trouble
        context[template] = obj

    if (isinstance(_repository := context.get("repository_object", None), classes.RepositoryDirectory)):
        _template = _repository.template(
            template    = template,
        )
        _return = _template.render(
            context,
            purpose = RenderPurpose.EMBED,
        )
    else:
        _return = f"# * readme-compiler error: cannot render template `{template}` without `RepositoryDirectory` instance * #"

    return django_setup.mark_safe(
        _return
    )