{{ git.repo | remarks }}

{{ 'def something(myname:Union[str,int], mybool:bool, *args, **kwargs) -> None: \n    """\nMy Doc\n"""\n    return myname' | code | quote }}

{{ globals.dunder.name | repr | code }}