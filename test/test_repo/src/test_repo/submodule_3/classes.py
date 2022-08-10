from typing import Callable

class MySubModule3Class():
    """
    # Useless class MySubModule3Class

    This is a useless class containing one decorator only.
    """
    id:int
    nothing:bool = None
    
    def my_decorator(self, func:Callable)->Callable:
        return func