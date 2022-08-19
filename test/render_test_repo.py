import os

import readme_compiler

import django.template

django.template.base

_abspath    = os.path.abspath(__file__)
_dirpath    = os.path.dirname(_abspath)

os.chdir(
    os.path.join(_dirpath, "./test_repo")
)

_repository = readme_compiler.RepositoryDirectory()

_repository.render()