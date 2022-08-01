# Set up django first
from . import django_setup

from . import bin
from . import log
from . import classes
from . import filters
from . import format
from . import settings
from . import templatetags


from .describe._mapper import   annotation, \
                                describe

from . import django_setup
from .django_setup import   register
from .classes import        RepositoryDirectory, \
                            MarkdownTemplate

