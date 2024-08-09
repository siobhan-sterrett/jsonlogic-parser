"""
Implementation of JSONLogic: https://jsonlogic.com
"""

# mypy: ignore-errors

import operator as py_op

from dataclasses import dataclass
from functools import reduce, wraps
from inspect import signature, Signature, Parameter
from types import UnionType
from typing import (
    # Types
    Any, Callable, Literal, Mapping, MutableMapping, NewType, Self, Sequence, Type,
    # Generics
    ClassVar, Concatenate, ParamSpec, TypeGuard, TypeVar,
    # functions
    cast, get_args, get_origin, get_overloads, overload
)


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

Operator = NewType('Operator', str)
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

def op_args(jsonlogic: JSONLogic) -> tuple[Operator, JSONArray]:
    op, arg = next(iter(jsonlogic.items()))
    if isinstance(arg, list):
        return op, arg
    else:
        return op, [arg]

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

Data = Any
"""
Data is what JSONLogic operates on. Data is a container,
indexable by either integers (list) or strings (dict).

Data is accessed using the "var" operator, which takes
an index and returns the value at that index in Data.
For more details, see the 'var_op' function below.
"""

class NullDataAccess(RuntimeError):
    pass

class NullData(Mapping[str, Any]):
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
OpFunction = Callable[Concatenate[Data, JSONPath, P], T]
"""
An OpFunction is a function that's called during
evaluation of a data object. Each operator is associated
with a specific OpFunction that tells it how to operate
on the given data.
"""

_op_fns: MutableMapping[Operator, OpFunction[..., Any]] = {}
"""
_op_fns is a global dict that maps each supported operator
to the function that implements it.
"""

def evaluate(data: Data, jsonlogic: JSONLogic) -> Any:
    """
    Initializes a base JSONPath, and forwards to _evaluate().
    """
    return _evaluate(data, JSONPath('$'), jsonlogic)

def eval(jsonlogic: JSONLogic) -> JSON:
    """
    Allows for evaluation of "pure" JSONLogic -- logic
    which does not reference the data object.

    Raises NullDataAccess if the jsonlogic attempts to
    access the data object.
    """
    return evaluate(NullData(), jsonlogic)

@dataclass
class EvaluationError(RuntimeError):
    where: JSONPath

@dataclass
class UnrecognizedOperand(EvaluationError):
    op: str

def _evaluate(data: Data, path: JSONPath, jsonlogic: JSONLogic) -> Any:
    """
    The main evaluation logic.

    This function selects the appropriate OpFunction, and passes it
    the appropriate args. OpFunctions, in turn, recursively call
    _evaluate().

    The path parameter is used to track the current position within
    the JSONLogic object, for error reporting.
    """
    op, args = op_args(jsonlogic)

    if op_fn := _op_fns.get(op):
        return op_fn(data, path, *args)
    else:
        raise UnrecognizedOperand(where=path, op=op)

def maybe_evaluate(data: Data, path: JSONPath, json: Any) -> Any:
    """
    A convenience function.
    """
    if is_jsonlogic(json):
        return _evaluate(data, path, json)
    return json

def type_check(fn: Callable[P, T]) -> Callable[P, T]:
    """
    type_check is a meta-programming decorator that adds
    runtime type-checking behavior to the decorated function.

    When the decorated function is called, this decorator checks
    the args being passed in against the type annotations in
    the function definition. If all types pass this check, the
    function is called; otherwise, a TypeError is raised.

    This decorator also works on overloaded functions, checking
    against the type annotations in each overload declaration.
    """

    fn_sigs: list[Signature]
    if fn_overloads := get_overloads(fn):
        fn_sigs = [signature(fn_overload) for fn_overload in fn_overloads]
    else:
        fn_sigs = [signature(fn)]

    @wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        for fn_sig in fn_sigs:
            bound = fn_sig.bind(*args, **kwargs)

            for identifier, value in bound.arguments.items():
                parameter = fn_sig.parameters[identifier]
                annotation = parameter.annotation

                if isinstance(annotation, type) or \
                    get_origin(annotation) is UnionType and all([isinstance(ann, type) for ann in get_args(annotation)]):
                    match parameter.kind:
                        case Parameter.POSITIONAL_ONLY | Parameter.POSITIONAL_OR_KEYWORD | Parameter.KEYWORD_ONLY:
                            if not isinstance(value, annotation):
                                break
                        case Parameter.VAR_POSITIONAL:
                            for arg in value:
                                if not isinstance(arg, annotation):
                                    break
                        case Parameter.VAR_KEYWORD:
                            for arg in value.values():
                                if not isinstance(arg, annotation):
                                    break

            else:
                # If we're here, this loop didn't break,
                # which means all annotations passed the
                # type-check!
                return fn(*bound.args, **bound.kwargs)

        # If we're here, then there was no overload for which
        # all annotations passed the type-check.
        raise TypeError('No matching overload found for args')

    return wrapper

@overload
def op_fn(_op: str, *, evaluate_args: bool = True, pass_data: Literal[False] = False) -> Callable[[Callable[P, T]], Callable[P, T]]:
    ...
@overload
def op_fn(_op: str, *, evaluate_args: bool = True, pass_data: Literal[True]) -> Callable[[OpFunction[P, T]], OpFunction[P, T]]:
    ...
def op_fn(_op: str, *, evaluate_args: bool = True, pass_data: bool = False) -> Callable[[Callable[P, T]], Callable[P, T]] | Callable[[OpFunction[P, T]], OpFunction[P, T]]:
    """
    This decorator marks the decorated function as an OpFunction, and
    associates it with the given operator.

    If evaluate_args is True, if any of the OpFunction's args are themselves
    jsonlogic, they will be evaluated, and their result will be passed into
    the function instead.

    If pass_data is True, the decorated function will be passed references
    to the data and path objects passed into _evaluate(). Otherwise, the
    decorated function only receives the operator args.
    """
    op = Operator(_op)

    @overload
    def to_op_fn(fn: OpFunction[P, T]) -> OpFunction[P, T]:
        ...
    @overload
    def to_op_fn(fn: Callable[P, T]) -> OpFunction[P, T]:
        ...
    def to_op_fn(fn: OpFunction[P, T] | Callable[P, T]) -> OpFunction[P, T]:
        if pass_data:
            return cast(OpFunction[P, T], fn)
        else:
            _fn = cast(Callable[P, T], fn)
            @wraps(_fn)
            def op_fn(data: Data, path: JSONPath, *args: P.args, **kwargs: P.kwargs):
                return _fn(*args, **kwargs)
            return op_fn

    @overload
    def decorator(fn: OpFunction[P, T]) -> OpFunction[P, T]:
        ...
    @overload
    def decorator(fn: Callable[P, T]) -> Callable[P, T]:
        ...
    def decorator(fn: Callable[P, T] | OpFunction[P, T]) -> Callable[P, T] | OpFunction[P, T]:
        op_fn = to_op_fn(fn)
        
        @wraps(op_fn)
        def wrapper(data: Data, path: JSONPath, *_args: P.args, **kwargs: P.kwargs) -> T:
            if evaluate_args:
                args = tuple(
                    maybe_evaluate(data, path.join_path(op).join_path(i), arg)
                    for i, arg in enumerate(_args))
            else:
                args = _args

            return op_fn(data, path, *args, **kwargs)

        if op in _op_fns:
            raise RuntimeError(f"Op '{op}' assigned to multiple op functions")
        else:
            _op_fns[op] = wrapper

        return fn

    return decorator

class Missing:
    """
    A sentinel class.
    """
    pass

def _has_var(data: Data, key: int | str) -> bool:
    try:
        if isinstance(key, str):
            value: Any = data
            key_path = JSONPath(key)
            for part in key_path:
                value = value[part]
        elif isinstance(data, Sequence):
            data[key]
        else:
            return False
    except (KeyError, IndexError):
        return False
    else:
        return True

@op_fn('var', pass_data=True)
@type_check
def op_var(data: Data, path: JSONPath, key: int | str, default: JSON | Type[Missing] = Missing) -> Any | None:
    try:
        if isinstance(key, str):
            value: Any = data
            key_path = JSONPath(key)
            for part in key_path:
                value = value[part]
            return data
        elif isinstance(data, Sequence):
            data[key]
        else:
            raise KeyError
    except (KeyError, IndexError):
        if default is not Missing:
            return default
        else:
            return None

@op_fn('missing', pass_data=True)
@type_check
def op_missing(data: Data, path: JSONPath, *args: str) -> list[str]:
    return [
        arg for arg in args
        if not _has_var(data, arg)
    ]

@op_fn('missing_some', pass_data=True)
@type_check
def op_missing_some(data: Data, path: JSONPath, count: int, args: list[str]) -> list[str]:
    missing = op_missing(data, path, *args)
    if len(args) - len(missing) < count:
        return missing
    return []

@op_fn('if', evaluate_args=False, pass_data=True)
def op_if(data: Data, path: JSONPath, if_arg: JSON, then_arg: JSON, *elses: JSON) -> Any | None:
    offset = 0

    if_arg = maybe_evaluate(data, path.join_path(offset), if_arg)

    while True:
        if if_arg:
            return maybe_evaluate(data, path.join_path(1 + offset), then_arg)
        else:
            match len(elses):
                case 0: return None
                case 1: return maybe_evaluate(data, path.join_path(2 + offset), then_arg)
                case _:
                    return op_if(data, path, *elses)

@op_fn('==')
def op_eq(left: Any, right: Any) -> bool:
    # https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Equality
    if isinstance(left, type(right)) or isinstance(right, type(left)):
        return left == right

    if (
        isinstance(left, int) and isinstance(right, float) or
        isinstance(left, float) and isinstance(right, int)
    ):
        return left == right

    if left is None or right is None:
        return left == right

    if isinstance(left, bool) or isinstance(right, bool):
        # 0 == False and 1 == True in Python
        return left == right

    if isinstance(right, str):
        left, right = right, left

    if isinstance(left, str):
        if isinstance(right, (int, float)):
            try:
                left = type(right)(left)
            except ValueError:
                pass

            return left == right

    return left == right

@op_fn('===')
def op_eq_eq(left: Any, right: Any) -> bool:
    return left == right

@op_fn('!=')
def op_neq(left: Any, right: Any) -> bool:
    return not op_eq(left, right)

@op_fn('!==')
def op_neq_eq(left: Any, right: Any) -> bool:
    return left != right

@op_fn('!')
def op_not(arg: Any) -> bool:
    return not arg

@op_fn('!!')
def op_not_not(arg: Any) -> bool:
    return not not arg

@op_fn('and', evaluate_args=False, pass_data=True)
def op_and(data: Data, path: JSONPath, left: JSON, right: JSON, *args: JSON) -> Any | None:
    args = (left, right, *args)
    idx = 0

    while len(args) > 1:
        if not (value := maybe_evaluate(data, path.join_path(idx), args[0])):
            return value
        args = args[1:]
        idx += 1

    return maybe_evaluate(data, path.join_path(idx), args[0])

@op_fn('or', evaluate_args=False, pass_data=True)
def op_or(data: Data, path: JSONPath, left: JSON, right: JSON, *args: JSON) -> Any | None:
    args = (left, right, *args)
    idx = 0

    while len(args) > 1:
        if value := maybe_evaluate(data, path.join_path(idx), args[0]):
            return value
        args = args[1:]
        idx += 1

    return maybe_evaluate(data, path.join_path(idx), args[0])

@op_fn('<')
def op_lt(left: int | float, right: int | float, righter: int | float | Type[Missing] = Missing) -> bool:
    if righter is Missing:
        return left < right
    else:
        return left < right < cast(int | float, righter)

@op_fn('<=')
def op_lte(left: int | float, right: int | float, righter: int | float | Type[Missing] = Missing) -> bool:
    if righter is Missing:
        return left <= right
    else:
        return left <= right <= cast(int | float, righter)

@op_fn('>')
def op_gt(left: int | float, right: int | float, righter: int | float | Type[Missing] = Missing) -> bool:
    if righter is Missing:
        return left > right
    else:
        return left > right > cast(int | float, righter)

@op_fn('>=')
def op_gte(left: int | float, right: int | float, righter: int | float | Type[Missing] = Missing) -> bool:
    if righter is Missing:
        return left >= right
    else:
        return left >= right >= cast(int | float, righter)

@op_fn('max')
def op_max(*args: int | float) -> int | float:
    return max(args)

@op_fn('min')
def op_min(*args: int | float) -> int | float:
    return min(args)

@overload
def op_add(arg: str) -> float:
    ...
@overload
def op_add(*args: int | float) -> int | float:
    ...
@op_fn('+')
def op_add(*args: int | float | str) -> int | float:
    if len(args) == 1 and type(args[0]) == str:
        return float(args[0])

    return reduce(py_op.add, args, 0)

@op_fn('-')
def op_sub(left: int | float, right: int | float | Type[Missing] = Missing) -> int | float:
    if right is Missing:
        return -left
    return left - cast(int | float, right)

@op_fn('*')
def op_mul(*args: int | float) -> int | float:
    return reduce(py_op.mul, args, 1)

@op_fn('/')
def op_div(left: int | float, right: int | float) -> int | float:
    return left / right

@op_fn('%')
def op_mod(left: int | float, right: int | float) -> int | float:
    return left % right

@op_fn('map', evaluate_args=False, pass_data=True)
def op_map(data: Data, path: JSONPath, argument: JSON, map_fn: JSON) -> list[Any]:
    argument = maybe_evaluate(data, path.join_path(0), argument)

    if not isinstance(argument, list):
        raise TypeError(f"Op 'map' expected array as first parameter, got {json_type(argument)}")

    if not is_jsonlogic(map_fn):
        raise TypeError(f"Op 'map' expected jsonlogic object as second parameter, got {json_type(map_fn)}")

    return [_evaluate(cast(Data, arg), path.join_path(1), map_fn) for arg in argument]

@op_fn('filter', evaluate_args=False, pass_data=True)
def op_filter(data: Data, path: JSONPath, argument: JSON, filter_fn: JSON) -> list[Any]:
    argument = maybe_evaluate(data, path.join_path(0), argument)

    if not isinstance(argument, list):
        raise TypeError(f"Op 'filter' expected array as first parameter, got {json_type(argument)}")

    if not is_jsonlogic(filter_fn):
        raise TypeError(f"Op 'filter' expected jsonlogic object as second parameter, got {json_type(filter_fn)}")

    results: list[Any] = []

    return [
        arg
        for arg in argument
        if _evaluate(cast(Data, arg), path.join_path(1), filter_fn)
    ]

    return results

@op_fn('reduce', evaluate_args=False, pass_data=True)
def op_reduce(data: Data, path: JSONPath, argument: JSON, reduce_fn: JSON, initial: JSON) -> Any:
    argument = maybe_evaluate(data, path.join_path(0), argument)
    initial = maybe_evaluate(data, path.join_path(2), initial)

    if not isinstance(argument, list):
        raise TypeError(f"Op 'reduce' expected array as first parameter, got {json_type(argument)}")

    if not is_jsonlogic(reduce_fn):
        raise TypeError(f"Op 'reduce' expected jsonlogic object as second parameter, got {json_type(reduce_fn)}")

    acc = {
        "current": None,
        "accumulator": initial
    }

    for arg in argument:
        acc["current"] = arg
        acc["accumulator"] = _evaluate(acc, path.join_path(1), reduce_fn)

    return acc["accumulator"]

@op_fn('all', evaluate_args=False, pass_data=True)
def op_all(data: Data, path: JSONPath, argument: JSON, test_fn: JSON) -> bool:
    argument = maybe_evaluate(data, path.join_path(0), argument)

    if not isinstance(argument, list):
        raise TypeError(f"Op 'all' expected array as first parameter, got {json_type(argument)}")

    if not is_jsonlogic(test_fn):
        raise TypeError(f"Op 'all' expected jsonlogic object as second parameter, got {json_type(test_fn)}")

    return all([
        _evaluate(cast(Data, arg), path.join_path(i), test_fn)
        for i, arg in enumerate(argument)
    ])

@op_fn('none', evaluate_args=False, pass_data=True)
def op_none(data: Data, path: JSONPath, argument: JSON, test_fn: JSON) -> bool:
    argument = maybe_evaluate(data, path.join_path(0), argument)

    if not isinstance(argument, list):
        raise TypeError(f"Op 'none' expected array as first parameter, got {json_type(argument)}")

    if not is_jsonlogic(test_fn):
        raise TypeError(f"Op 'none' expected jsonlogic object as second parameter, got {json_type(test_fn)}")

    return not any([
        _evaluate(cast(Data, arg), path.join_path(i), test_fn)
        for i, arg in enumerate(argument)
    ])

@op_fn('some', evaluate_args=False, pass_data=True)
def op_some(data: Data, path: JSONPath, argument: JSON, test_fn: JSON) -> bool:
    argument = maybe_evaluate(data, path.join_path(0), argument)

    if not isinstance(argument, list):
        raise TypeError(f"Op 'some' expected array as first parameter, got {json_type(argument)}")

    if not is_jsonlogic(test_fn):
        raise TypeError(f"Op 'some' expected jsonlogic object as second parameter, got {json_type(test_fn)}")

    return not any([
        _evaluate(cast(Data, arg), path.join_path(i), test_fn)
        for i, arg in enumerate(argument)
    ])

@op_fn('merge')
def op_merge(*args: JSON) -> list[Any]:
    result: list[Any] = []

    for arg in args:
        if isinstance(arg, list):
            result += arg
        else:
            result += [arg]

    return result

@op_fn('in')
def op_in(needle: Any, haystack: str | JSONArray) -> bool:
    return needle in haystack

@op_fn('cat')
def op_cat(*args: str) -> str:
    return ''.join(args)

@op_fn('substr')
def op_substr(arg: str, start: int, end: int | Type[Missing] = Missing) -> str:
    if end is Missing:
        end = len(arg)
    return arg[start:end]

@op_fn('log', evaluate_args=False)
def op_log(arg: JSON) -> JSON:
    print(arg)
    return arg
