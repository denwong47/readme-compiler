"""
DO NOT RENAME THIS FILE - THIS NAME IS THE DEFAULT GIVEN BY DJANGO
"""

from datetime import datetime
import pytz
from typing import Any, Callable, Dict, Iterable, List, Tuple, Type, Union

from django.template import Context as  DjangoContext, \
                            Template as DjangoTemplate

from . import django_setup
from .django_setup import register  # Required to avoid django.template.library.InvalidTemplateLibrary Exception

import readme_compiler.classes as classes

from . import settings
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