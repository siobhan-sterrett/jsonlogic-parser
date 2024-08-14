import re

from typing import ClassVar, Iterator, Mapping, Sequence

JSONAtom = None | bool | int | float | str
JSONArray = Sequence['JSON']
JSONObject = Mapping[str, 'JSON']
JSON = JSONAtom | JSONArray | JSONObject
"""
Definitions of JSON types in Python.
"""

class JSONPath:
    """
    JSONPath implementation.
    
    A JSONPath identifies a specific place in a JSON object or array. Each JSONPath
    starts with the root element '$', followed by any number of dot elements or
    index elements.

    A dot element takes the form '.{key}', where 'key' is a key of the JSON object
    referred to by the preceding part of the path.

    An index element takes the form '[{index}]', where 'index' is a positive integer
    index into the JSON array referred to by the preceding part of the path.
    """

    path: str

    DOT_ELEMENT: ClassVar[re.Pattern[str]] = re.compile(r'\.(?P<KEY>[^.\[]+)')
    INDEX_ELEMENT: ClassVar[re.Pattern[str]] = re.compile(r'\[(?P<IDX>\d+)\]')
    ELEMENT: ClassVar[re.Pattern[str]] = re.compile(f'{DOT_ELEMENT.pattern}|{INDEX_ELEMENT.pattern}')

    def __init__(self, path: str):
        self._check_path(path)
        self.path = path
    
    @classmethod
    def _check_path(cls, path: str):
        if path.startswith('$'):
            path = path[1:]
            while path:
                if match := cls.ELEMENT.match(path):
                    path = path[match.end():]
                else:
                    raise ValueError("Invalid JSONPath")
        else:
            raise ValueError("Invalid JSONPath: must start with '$'")
        
    @property
    def parts(self) -> Iterator[str | int]:
        path = self.path[1:]
        
        while path:
            if match := self.ELEMENT.match(path):
                path = path[match.end():]
                if match.lastgroup == 'KEY':
                    yield match['KEY']
                else:
                    yield int(match['IDX'])
    
    def append(self, part: str | int) -> 'JSONPath':
        if isinstance(part, str):
            return JSONPath(f"{self.path}.{part}")
        else:
            return JSONPath(f"{self.path}[{part}]")
    
    def __getitem__(self, idx: str | int) -> 'JSONPath':
        return self.append(idx)

    def __getattr__(self, idx: str) -> 'JSONPath':
        return self.append(idx)
