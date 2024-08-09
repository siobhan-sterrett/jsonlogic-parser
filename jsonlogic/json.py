from typing import ClassVar, Self, Sequence

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

class JSONPath(str):
    root: ClassVar[Self]

    def __new__(cls, path: str) -> Self:
        json_path = super().__new__(cls, path)
        if not json_path.startswith(f'{cls.root}.'):
            raise ValueError("JSONPath must start with '$.'")
        return json_path
        
    @property
    def parts(self) -> Sequence[str | int]:
        parts: list[str | int] = []
        for part in self.split('.')[1:]:
            try:
                parts.append(int(part))
            except ValueError:
                parts.append(part)

        return parts
    
    def join_path(self, part: str | int) -> 'JSONPath':
        return JSONPath('.'.join([self, str(part)]))

    def __getattr__(self, idx: str | int) -> 'JSONPath':
        return self.join_path(idx)
    
JSONPath.root = JSONPath('$')
