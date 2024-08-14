"""
Implementation of JSONLogic: https://jsonlogic.com
"""

from typing import Self

from .json import JSON, JSONPath

class JSONLogic:
    op: str
    args: list['JSON | JSONLogic']
    loc: JSONPath

    def __init__(self, json: JSON, loc: JSONPath = JSONPath('$')):
        self.loc = loc
        if isinstance(json, dict):
            if len(json) == 1:
                op, arg = next(iter(json.items()))
                if arg is not None:
                    self.op = op
                    self.args = []
                    if isinstance(arg, list):
                        for i, _arg in enumerate(arg):
                            self.args.append(self.maybe_parse(_arg, loc[op][i]))
                    else:
                        self.args.append(self.maybe_parse(arg, loc[op]))
                    
                    return
                
        raise ValueError('Invalid JSONLogic')

    @classmethod
    def maybe_parse(cls, json: JSON, loc: JSONPath) -> Self | JSON:
        try:
            return cls(json, loc)
        except ValueError:
            return json
