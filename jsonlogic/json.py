from typing import Self, Sequence

JSONAtom = bool | int | float | str
JSONArray = list['JSON | None']
JSONObject = dict[str, 'JSON | None']
JSON = JSONAtom | JSONArray | JSONObject
"""
Definitions of JSON types in Python.
"""

def json_type(json: JSON) -> str:
    if isinstance(json, dict):
        return 'object'
    elif isinstance(json, list):
        return 'array'
    elif isinstance(json, str):
        return 'string'
    elif isinstance(json, float):
        return 'float'
    elif json in (True, False):
        return 'boolean'
    else:
        return 'int'

class JSONPath:
    __slots__ = ('path')

    def __init__(self, path: str):
        if not (path == '$' or path.startswith('$.') or path.startswith('$[')):
            raise ValueError("JSONPath must start with root element '$'")
        
        self.path = path
    
    @classmethod
    def from_parts(cls, parts: Sequence[str | int]) -> Self:
        return cls('.'.join([str(part) for part in parts]))
        
    @property
    def parts(self) -> Sequence[str | int]:
        parts: list[str | int] = []
        for part in self.path.split('.')[1:]:
            try:
                parts.append(int(part))
            except ValueError:
                parts.append(part)

        return parts
    
    def append(self, part: str | int) -> 'JSONPath':
        if isinstance(part, str):
            return JSONPath(f"{self.path}.{part}")
        else:
            return JSONPath(f"{self.path}[{part}]")
    
    def __getindex__(self, idx: str | int) -> 'JSONPath':
        return self.append(idx)

    def __getattr__(self, idx: str | int) -> 'JSONPath':
        return self.append(idx)
