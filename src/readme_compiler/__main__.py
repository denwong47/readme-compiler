from . import RepositoryDirectory

# If this is run with -m, compile the current directory
def __main__():
    RepositoryDirectory("./").compile()

if (__name__ == "__main__"):
    __main__()