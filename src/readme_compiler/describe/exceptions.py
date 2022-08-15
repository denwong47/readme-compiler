from ..exceptions import FalseEvaluatingException

class ObjectNotDescribable(FalseEvaluatingException, ValueError):
    """
    An object cannot be described.
    Typically occurs on special built-in implementations such as `wrapper_descriptor`.
    """

class AttributeNotFound(FalseEvaluatingException, AttributeError):
    """
    Attribute requested is not found on the parent; `hasattr` returned `False`.
    """

class AttributeTypeHintOnly(FalseEvaluatingException, AttributeError):
    """
    Attribute only contains a type hint - it has no default value.
    """

class AttributeNotApplicable(FalseEvaluatingException, AttributeError):
    """
    Attribute requested is not valid on the requested Description type.
    """

class ObjectDescriptionRequired(FalseEvaluatingException, TypeError):
    """
    Used by `DescriptionMetadata`, raised if a non-`ObjectDescription` instance is passed as parent.
    """