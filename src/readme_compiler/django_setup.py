from django.conf import             settings
from django import                  template

from django.utils.safestring import mark_safe   # Imported by other modules, do not remove

# Start a register
# This HAS to be named register in templatetags.py
register = template.Library()

# Avoid django.core.exceptions.ImproperlyConfigured Exception.
settings.configure(
    DEBUG=False,
)