"""
Implementation of JSONLogic: https://jsonlogic.com
"""

from typing import Self

from .json import JSON

class JSONLogic:
    op: str
    args: list['JSON | JSONLogic']

    def __init__(self, json: JSON):
        if isinstance(json, dict):
            if len(json) == 1:
                op, arg = next(iter(json.items()))
                if arg is not None:
                    self.op = op
                    self.args = []
                    if isinstance(arg, list):
                        for _arg in arg:
                            self.args.append(self.maybe_parse(_arg))
                    else:
                        self.args.append(self.maybe_parse(arg))
                    
                    return
                
        raise ValueError('Invalid JSONLogic')

    @classmethod
    def maybe_parse(cls, json: JSON) -> Self | JSON:
        try:
            return cls(json)
        except ValueError:
            return json
