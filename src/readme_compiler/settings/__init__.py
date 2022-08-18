import logging

FILE_EXTENSION_MARKDOWN                 =   (".md",)

LOGGING_LEVEL                           =   logging.INFO

README_RENDERED_INDEX                   =   "README.md"
README_SOURCE_INDEX                     =   ".README.source.md"
README_RENDERED_DIRECTORY               =   ".readme"
README_SOURCE_DIRECTORY                 =   ".readme.source"

README_METADATA_INDEX                   =   ".README.metadata.json"
README_METADATA_DIRECTORY               =   "{descriptor}.{qualname}.metadata.json"    # this does not include path

README_BRANCH_DESCRIPTION_TEMPLATE      =   "branch.{branch}.md"

ENV_PATH                                =   "/env"

TEMPLATE_LOCATION                       =   f"/.readme.templates"

LOGO_URL                                =   f"/{README_SOURCE_DIRECTORY}/.logo"
FOOTER_LOCATION                         =   f"/{README_SOURCE_DIRECTORY}/.footer"