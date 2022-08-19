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
from ..settings.enums import RenderPurpose

from .repopath import LINKS_PATTERN

SINGLE_LINE_SPACER = r"""ㅤ\
ㅤ"""
DOUBLE_LINE_SPACER = r"""ㅤ\
ㅤ\
ㅤ"""

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
        if (not inspect.isabstract(transformer)):
            cls.declared.append(transformer)
            
# This will be imported by other modules.
transformers = TransformerMeta.declared

class Transformer(abc.ABC, metaclass=TransformerMeta):
    """
    Abstract base class for all string Transformers
    """
    skip_paths = []

    def __init__(
        self,
        repository:Any = None,
        *,
        skip_paths:List[str] = None,    # Paths to NOT apply the transformation on. Prevents a footer being added to a footer etc.
    )->None:
        self.repository = repository
        self.skip_paths = skip_paths if skip_paths else []

    @abc.abstractmethod
    def transform(
        self,
        text:SafeString,
    )->SafeString:
        pass

    def should_transform(
        self,
        path:str,
        *,
        purpose:RenderPurpose = RenderPurpose.STANDARD,
    )->bool:
        """
        Check if the path is on its own skip_paths.
        """
        return not path in self.skip_paths

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

class HeadersParagraphTransformer(Transformer):
    """
    Before any headers, add extra empty lines.
    """
    def __init__(
        self,
        repository: Any = None,
        min_level: int = 2,
        spacer: str = DOUBLE_LINE_SPACER,
        *,
        skip_paths: List[str] = None
    ) -> None:
        super().__init__(repository, skip_paths=skip_paths)

        self.min_level = min_level
        self.spacer = spacer

    @property
    def pattern(
        self,
    )->re.Pattern:
        """
        Return a regular expression `Pattern` object 
        """
        return re.compile(
            r"(\n{2,})(\#{1,"+str(self.min_level)+r"} )(?=\S)",
            re.MULTILINE,
        )
    
    def should_transform(
        self,
        path: str,
        *,
        purpose: RenderPurpose = RenderPurpose.STANDARD
    ) -> bool:
        """
        This always applies.
        """
        return True

    def transform(
        self,
        text:str,
    )->str:
        return SafeString(self.pattern.sub(
            fr"\n\n{self.spacer}\n\2",
            text
        ))

class FooterTransformer(Transformer):
    """
    Add a footer to all Readme files
    """
    def __init__(
        self, 
        repository: Any = None,
        template: str = settings.FOOTER_LOCATION,
    ) -> None:

        template = repository.repopath.abspath(
            repository.repopath.parse(template).source
        )

        super().__init__(
            repository,
            skip_paths = [template, ],
        )

        self.template = template

    def transform(
        self,
        text:str,
    )->str:
        if (self.repository is not None and self.template):
            
            try:
                _footer = self.repository.render(self.template, purpose=RenderPurpose.EMBED)
            except FileNotFoundError as e:
                _footer = ""
            
            text += _footer

        return text

    def should_transform(
        self,
        path: str,
        *,
        purpose: RenderPurpose = RenderPurpose.STANDARD
    ) -> bool:
        return \
            super().should_transform(path, purpose=purpose) and \
            purpose not in (
                RenderPurpose.EMBED,
            )
