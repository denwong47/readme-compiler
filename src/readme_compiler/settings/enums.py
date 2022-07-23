import enum

class MarkdownTemplateMode(enum.Enum):
    INDEX   =   0
    LEAF    =   1
    BRANCH  =   2

class RenderPurpose(enum.Enum):
    STANDARD=   enum.auto()
    NORMAL  =   STANDARD
    EMBED   =   enum.auto()   