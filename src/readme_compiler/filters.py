"""
Custom Django Filters
"""
import functools
from typing import Callable

from django.utils.safestring import mark_safe
from django.template.defaultfilters import stringfilter

from . import django_setup
from . import format

def safe_string_filter(func:Callable)->Callable:
    """
    Decorator function marking the return of a function as safestring.
    """
    @functools.wraps(func)
    def _wrapper(
        *args,
        **kwargs,
    )->str:
        return mark_safe(
            func(*args, **kwargs)
        )
    
    return _wrapper

# Force all filters to be string filters
def register_string_filter(*args, **kwargs):
    return django_setup.register.filter(
        stringfilter(
            safe_string_filter(*args, **kwargs)
        ),
        is_safe=True, # This doesn't really work - use safe_string_filter above
    )

# Wrap around built-in functions
def register_builtin_filter(func:Callable):
    @functools.wraps(func)
    def _wrapper(*args, **kwargs)->str:
        _return = func(*args, **kwargs)

        if (isinstance(_return, str)):
            _return = mark_safe(_return)

        return _return

    return django_setup.register.filter(
        name = func.__name__,
        filter_func = _wrapper,
    )

# Register filters from existing functions
register_string_filter(format.format_source_code)
register_string_filter(format.prefix)
register_string_filter(format.quote)
register_string_filter(format.reindent)
register_string_filter(format.remarks)
register_string_filter(format.unremark)
register_string_filter(format.code)
register_string_filter(format.remove_remarks)

register_builtin_filter(repr)