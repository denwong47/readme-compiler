"""
# Transformers

Transfromers are string processors that are applied after django.template had rendered the text.
Most Transformers are for changing where links point to, adding header/footer and the likes.

Transformers can be called as functions, with or without initialising an instance.
Instances however can have `RepositoryDirectory` attached to them, greatly increasing their awareness of the context.
"""

import abc
import inspect
import re
from types import SimpleNamespace
from typing import Any, List

from django.utils.safestring import SafeString

from ..log import logger
from .. import settings
from .repopath import LINKS_PATTERN

print = logger.debug



class TransformerMeta(abc.ABCMeta):
    """
    Metaclass for Transformers.
    
    Two functions:
    1. allow Transformer(text=text) to work the same way as Transformer()(text=text); and
    2. keep a list of all concrete Transformers declared.
    """
    declared:List["Transformer"] = []

    def __repr__(self)->str:
        return self.__name__

    def __new__(
        cls,
        *args: Any,
        **kwargs: Any
    ) -> Any:
        if (
            (len(args)==1 and isinstance(args[0], str) and not kwargs) or \
            (len(kwargs)==1 and ("text" in kwargs) and not args)
        ):
            # If the Transformer class is called with a `str` argument (i.e. clearly not a type() declaration),
            # then treat it just like Transformer()(text=text).
            return cls()(*args, **kwargs)
        else:
            _type = super().__new__(cls, *args, **kwargs)

            # Add all the declared concrete transformers in to a universal list.
            
            cls.register(_type)

            return _type

    @classmethod
    def register(
        cls,
        transformer:"TransformerMeta",
    ):
        """
        Add any declared concrete transformers in to a universal list.
        """
        print(inspect.isabstract(transformer))
        if (not inspect.isabstract(transformer)):
            cls.declared.append(transformer)
            
# This will be imported by other modules.
transformers = TransformerMeta.declared

class Transformer(abc.ABC, metaclass=TransformerMeta):
    """
    Abstract base class for all string Transformers
    """
    def __init__(
        self,
        repository:Any = None,
        # template:Any   = None,
    )->None:
        self.repository = repository
        # self.template   = template


    @abc.abstractmethod
    def transform(
        self,
        text:SafeString,
    )->SafeString:
        pass

    def __call__(self, text:SafeString):
        # Cannot just __call__ = transform:
        # transform will be REDECLARED by the subclass!
        return self.transform(text=text)

    def __repr__(self)->str:
        return type(self).__name__ + \
            "(" + \
                ', '.join([f'{_key}={repr(_value)}' for _key, _value in ( \
                    ('repository', f"<{type(self.repository).__name__} instance at {id(self.repository):x}>"),\
                )]) + \
            ")"


class SourceLinkTransformer(Transformer):
    """
    Replace all links pointing to sources to rendered.
    """
    def transform(
        self,
        text:SafeString,
    )->SafeString:

        _substitutions = []
        
        for _match in LINKS_PATTERN.finditer(text):
            
            if ("://" not in _match.group("link_href")):
                _dest_url = _match.group("link_href")

                if (self.repository is not None):
                    _dest_url = self.repository.repopath.rendered(_match.group("link_href"))

                # link_href needs to change
                if (_dest_url != _match.group("link_href")):
                    print (f"Phrase [{_match.group(0)}] points to a source link - replacing with [[{_match.group('link_text')}]({_dest_url})].")

                    # Put substitution operation in a list, last item to come first.
                    # This is because changing the earlier spans will result in later spans shifting positions - so later spans had to be done first.
                    _substitutions.insert(0, 
                        SimpleNamespace(
                            span = _match.span("link_href"),
                            replacement = _dest_url,
                        )
                    )
            else:
                # If schema is specified, this will be disregarded
                print (f"Phrase [{_match.group(0)}] is ignored as it points to a URL with schema/protocol.")
            
        for _substitution in _substitutions:
            # Make actual subtitution, later spans first.
            text =  text[:_substitution.span[0]] + \
                    _substitution.replacement + \
                    text[_substitution.span[1]:]

        return text

# class FooterTransformer(Transformer):
#     """
#     Add a footer to all Readme files
#     """
#     def transform(
#         self,
#         text:str,
#     )->str:
#         pass
