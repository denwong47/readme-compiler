import abc
import inspect
import re
from types import SimpleNamespace
from typing import Any, List

from django.utils.safestring import SafeString

from ..log import logger
from .. import settings

print = logger.debug

LINKS_PATTERN = re.compile(r"\[(?P<link_text>[^]]+)\]\((?P<link_href>[^\)\s]+)\)")

class TransformerMeta(abc.ABCMeta):
    """
    Metaclass for Transformers.
    
    Two functions:
    1. allow Transformer(text=text) to work the same way as Transformer()(text=text); and
    2. keep a list of all concrete Transformers declared.
    """
    declared:List["Transformer"] = []

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
                _dest_url = None

                if (self.repository is not None):

                    if (self.repository.settings.paths.folder.source in _match.group("link_href").split("/")):
                        # This is pointing to ./GIT_DIR/.readme/something.md
                        _dest_url = _match.group("link_href").replace(
                            f"/{self.repository.settings.paths.folder.source}/", 
                            f"/{self.repository.settings.paths.folder.rendered}/",
                            1,
                        )

                    elif (self.repository.settings.paths.index.source in _match.group("link_href").split("#")[0].split("/")):
                        # This is pointing to ./GIT_DIR/.README.source.md
                        _dest_url = _match.group("link_href").replace(
                            f"{self.repository.settings.paths.index.source}", 
                            f"{self.repository.settings.paths.index.rendered}",
                            1,
                        )
                        
                    if (_dest_url):
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
