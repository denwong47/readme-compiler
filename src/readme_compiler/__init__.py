# Set up django first
from . import django_setup

from . import bin
from . import log
from . import classes
from . import settings
from . import templatetags

from .describe._mapper import describe
from .describe._mapper import annotation

from .django_setup import   register
from .classes import        RepositoryDirectory, \
                            MarkdownTemplate
