"""
A very lite version of stdout for a little bit of colours only, without any Formatters and the like.
"""

def colour_factory(colour_code:int)->str:
    def _wrapper(text:str)->str:
        return f"\033[1m\033[{colour_code}m{text}\033[39m\033[22m"
    return _wrapper

black	= colour_factory(30)
red	    = colour_factory(31)
green	= colour_factory(32)
yellow	= colour_factory(33)
blue	= colour_factory(34)
magenta	= colour_factory(35)
cyan	= colour_factory(36)
white	= colour_factory(37)
# reset	= colour_factory(39)