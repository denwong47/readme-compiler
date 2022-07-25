from tqdm import tqdm
from readme_compiler import describe

import pandas as pd

_modules = []

import ailsa_core
_modules.append(ailsa_core)
import ailsa_database
_modules.append(ailsa_database)
import ailsa_study
_modules.append(ailsa_study)
import ailsa_webcrawl
_modules.append(ailsa_webcrawl)
import forestreet_cache
_modules.append(forestreet_cache)
import forestreet_core
_modules.append(forestreet_core)
import forestreet_database
_modules.append(forestreet_database)
import forestreet_http_host
_modules.append(forestreet_http_host)
import forestreet_job_monitor
_modules.append(forestreet_job_monitor)
import forestreet_language
_modules.append(forestreet_language)
import forestreet_log
_modules.append(forestreet_log)
import forestreet_phrases
_modules.append(forestreet_phrases)
import forestreet_presentation
_modules.append(forestreet_presentation)
import forestreet_proxy
_modules.append(forestreet_proxy)
import forestreet_webcrawl
_modules.append(forestreet_webcrawl)

def tree_module(module):

    _module = describe.ModuleDescription(module)

    _return = [("Module", _module.qualname)]
    
    # for _attr in _module.classes:
    #     _return += [("Class", describe.ObjectDescription(_attr).qualname)]

    # for _attr in _module.functions:
    #     _return += [("Function", describe.ObjectDescription(_attr).qualname)]

    for _attr in _module.modules:
        if ("settings" not in _attr.__name__):
            _return += tree_module(_attr)
    
    return _return


if (__name__ == "__main__"):
    _return = []
    for _module in tqdm(_modules):
        _return += tree_module(_module)

    _df = pd.DataFrame(_return, columns=["type", "qualname"])
    _df.drop_duplicates(inplace=True)
    _df["description"] = _df.apply(lambda row: "Write Documentation for '" + " ".join(row.to_list()) + "'", axis=1)
    _df["sprint"] = 49 #"Forestreet Backlog"
    _df["parent"] = "DF-291"
    _df["type"] = "Task"

    print (_df)

    _df.to_csv("~/Desktop/jobs.csv")