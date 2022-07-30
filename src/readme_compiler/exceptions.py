"""
## Exceptions Module

Generic exceptions used in this library.
By default all Exception instances should evaluate to `False`;
this allows `Exceptions` to be returned in functions in place of `None` to indicate failure,
while allowing syntax
```python
_result = func()
if (_result):
    # Success
else:
    # Failure
```
The Exception instance can then be further interrogated to decide if it should be raised or handled.
"""

class FalseEvaluatingException(Exception):
    """
    Exception instances that evaluates as False.

    Typically used to define subclasses:
    ```
        class SomeRuntimeError(FalseEvaluatingException, RuntimeError):
            pass
    ```
    """
    def __bool__(self)->bool:
        return False
    __nonzero__ = __bool__