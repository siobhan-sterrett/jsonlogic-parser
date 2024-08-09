from typing import Any, TypeVar, ParamSpec

from .json import JSON, JSONObject, JSONPath
from .jsonlogic import is_jsonlogic
from .op_function import do_ops

class NullDataAccess(RuntimeError):
    pass

class NullData(object):
    """
    NullData is something that looks like a Data to the
    type system, but raises an exception if it's accessed.
    This is useful for run-time validation of 'pure' jsonlogic
    -- i.e. jsonlogic that does not use the 'var' keyword to access
    data.
    """
    def __getitem__(self, _):
        raise NullDataAccess()

    def __len__(self):
        raise NullDataAccess()

    def __iter__(self):
        raise NullDataAccess()
    
T = TypeVar('T')
P = ParamSpec('P')

def evaluate(data: object, jsonlogic: JSONObject) -> Any:
    """
    Initializes a base JSONPath, and forwards to _evaluate().
    """
    if is_jsonlogic(jsonlogic):
        return do_ops(data, JSONPath('$'), jsonlogic)
    else:
        raise ValueError('More than one key found in jsonlogic object')

def maybe_evaluate(data: object, path: JSONPath, json: Any) -> Any:
    """
    A convenience function.
    """
    if is_jsonlogic(json):
        return do_ops(data, path, json)
    return json

def pure_evaluate(jsonlogic: JSONObject) -> JSON:
    """
    Allows for evaluation of "pure" JSONLogic -- logic
    which does not reference the data object.

    Raises NullDataAccess if the jsonlogic attempts to
    access the data object.
    """
    return evaluate(NullData(), jsonlogic)
