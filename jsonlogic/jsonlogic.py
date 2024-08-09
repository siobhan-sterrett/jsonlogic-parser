"""
Implementation of JSONLogic: https://jsonlogic.com
"""

from typing import TypeGuard

from .json import JSON
from .op_function import Operator

JSONLogic = dict[Operator, JSON]
"""
JSONLogic is just a JSON that we've confirmed follows the syntactic rules
of JSONLogic. These are very simple:
- The JSON must be a JSONObject (i.e. a dict[str, JSON | None]).
- The JSONObject must have exactly one key.
- The value associated with that key cannot be None.
"""

def is_jsonlogic(json: JSON) -> TypeGuard[JSONLogic]:
    """
    Returns True if json is syntactically-correct JSONLogic,
    False otherwise.

    Note that this function only asserts that json can be
    _parsed_ as JSONLogic. The JSONLogic itself may have
    semantic or logical errors, such as referring to an
    operator that doesn't exist.

    'TypeGuard[JSONLogic]' means that if this function
    returns True, the type-checker knows that json is
    JSONLogic.
    """

    if isinstance(json, dict):
        if len(json) == 1:
            value = next(iter(json.values()))
            if value is not None:
                return True

    return False
