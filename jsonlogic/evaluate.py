from typing import Any, NewType, TypeVar, ParamSpec

from .json import JSON, JSONPath
from .jsonlogic import JSONLogic, is_jsonlogic
from .op_function import do_ops
    
Data = NewType('Data', object)
"""
Data is what JSONLogic operates on. Data is a container,
indexable by either integers (list) or strings (dict).

Data is accessed using the "var" operator, which takes
an index and returns the value at that index in Data.
For more details, see the 'var_op' function below.
"""

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

def evaluate(data: Data, jsonlogic: JSONLogic) -> Any:
    """
    Initializes a base JSONPath, and forwards to _evaluate().
    """
    return do_ops(data, JSONPath('$'), jsonlogic)

def maybe_evaluate(data: Data, path: JSONPath, json: Any) -> Any:
    """
    A convenience function.
    """
    if is_jsonlogic(json):
        return do_ops(data, path, json)
    return json

def pure_evaluate(jsonlogic: JSONLogic) -> JSON:
    """
    Allows for evaluation of "pure" JSONLogic -- logic
    which does not reference the data object.

    Raises NullDataAccess if the jsonlogic attempts to
    access the data object.
    """
    return evaluate(Data(NullData()), jsonlogic)
