import io
from typing import Any

class SpoofedStdoutIO():
    """
    A class for `contextlib.redirect_stdout` to redirect to.
    `sys.__stdout__` is not an `IOBase` itself - the actual io object is at `sys.__stdout__.buffer`.

    So this class creates instances a `.buffer` attribute.
    """
    buffer = None

    def __init__(self, *args, **kwargs,)->None:
        self.buffer = io.BytesIO(*args, **kwargs)

    def __enter__(self):
        self.buffer.__enter__()
        return self

    def __exit__(
        self,
        *args,
        **kwargs,
    )->bool:
        return self.buffer.__exit__(
            *args,
            **kwargs,
        )

    def __getattr__(self, name:str)->Any:
        """
        If there's attribute it doesn't recognise - then pass it to the underlying `buffer`.
        """
        return getattr(self.buffer, name)
