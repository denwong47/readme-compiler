from django.conf import             settings
from django import                  template

from django.utils.safestring import mark_safe

# Start a register
register = template.Library()

# Avoid django.core.exceptions.ImproperlyConfigured Exception.
settings.configure(
    DEBUG=False,
)