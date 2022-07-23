import sys

import logging

from .settings import LOGGING_LEVEL

logger = logging.Logger("readme_compiler", LOGGING_LEVEL)
logger.addHandler(logging.StreamHandler(sys.stdout))