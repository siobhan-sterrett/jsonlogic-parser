import operator as py_op

from functools import reduce
from typing import (
    # Types
    Any, Mapping, Sequence, Type,
    # functions
    cast, overload
)

from .evaluate import maybe_evaluate
from .json import JSON, JSONArray, JSONPath, json_type
from .jsonlogic import is_jsonlogic
from .op_function import do_ops, op_fn, type_check

class _Missing:
    """
    A sentinel class.
    """
    pass

def _has_var(data: object, key: int | str) -> bool:
    try:
        if isinstance(key, str):
            keys = '.'.split(key)
            for key in keys:
                data = getattr(data, key, None)
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
def op_var(data: object, path: JSONPath, key: int | str, default: JSON | Type[_Missing] = _Missing) -> Any | None:
    data = cast(Mapping[int | str, Any], data)

    try:
        if isinstance(key, str):
            if not key:
                return data
            
            key, *key_path = key.split('.', maxsplit=1)

            try:
                key = int(key)
            except ValueError:
                pass

            if key_path:
                return op_var(data[key], path, key_path[0], default)
            else:
                return data[key]
        else:
            return data[key]
    except (KeyError, IndexError):
        if default is not _Missing:
            return default
        else:
            return None

@op_fn('missing', pass_data=True)
@type_check
def op_missing(data: object, path: JSONPath, *args: str) -> list[str]:
    return [
        arg for arg in args
        if not _has_var(data, arg)
    ]

@op_fn('missing_some', pass_data=True)
@type_check
def op_missing_some(data: object, path: JSONPath, count: int, args: list[str]) -> list[str]:
    missing = op_missing(data, path, *args)
    if len(args) - len(missing) < count:
        return missing
    return []

@op_fn('if', evaluate_args=False, pass_data=True)
def op_if(data: object, path: JSONPath, if_arg: JSON, then_arg: JSON, *elses: JSON) -> Any | None:
    offset = 0

    if_arg = maybe_evaluate(data, path.append(offset), if_arg)

    while True:
        if if_arg:
            return maybe_evaluate(data, path.append(1 + offset), then_arg)
        else:
            match len(elses):
                case 0: return None
                case 1: return maybe_evaluate(data, path.append(2 + offset), elses[0])
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
    if isinstance(left, bool) or isinstance(right, bool):
        return left is right
    
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
def op_and(data: object, path: JSONPath, *args: JSON) -> Any | None:
    for i, arg in enumerate(args):
        if not (value := maybe_evaluate(data, path.append(i), arg)):
            return value
    
    return True

@op_fn('or', evaluate_args=False, pass_data=True)
def op_or(data: object, path: JSONPath, *args: JSON) -> Any | None:
    for i, arg in enumerate(args):
        if value := maybe_evaluate(data, path.append(i), arg):
            return value
    
    return False

@op_fn('<')
def op_lt(left: int | float, right: int | float, *args: int | float) -> bool:
    if args:
        return left < right and op_lt(right, *args)
    else:
        return left < right

@op_fn('<=')
def op_lte(left: int | float, right: int | float, *args: int | float) -> bool:
    if args:
        return left <= right and op_lte(right, *args)
    else:
        return left <= right

@op_fn('>')
def op_gt(left: int | float, right: int | float, *args: int | float) -> bool:
    if args:
        return left > right and op_gt(right, *args)
    else:
        return left > right

@op_fn('>=')
def op_gte(left: int | float, right: int | float, *args: int | float) -> bool:
    if args:
        return left >= right and op_gte(right, *args)
    else:
        return left >= right

@op_fn('max')
def op_max(arg: int | float, *args: int | float) -> int | float:
    return max(arg, *args)

@op_fn('min')
def op_min(arg: int | float, *args: int | float) -> int | float:
    return min(arg, *args)

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
def op_sub(left: int | float, right: int | float | Type[_Missing] = _Missing) -> int | float:
    if right is _Missing:
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
def op_map(data: object, path: JSONPath, argument: JSON, map_fn: JSON) -> list[Any]:
    argument = maybe_evaluate(data, path.append(0), argument)

    if not isinstance(argument, list):
        raise TypeError(f"Op 'map' expected array as first parameter, got {json_type(argument)}")

    if not is_jsonlogic(map_fn):
        raise TypeError(f"Op 'map' expected jsonlogic object as second parameter, got {json_type(map_fn)}")

    return [do_ops(cast(object, arg), path.append(1), map_fn) for arg in argument]

@op_fn('filter', evaluate_args=False, pass_data=True)
def op_filter(data: object, path: JSONPath, argument: JSON, filter_fn: JSON) -> list[Any]:
    argument = maybe_evaluate(data, path.append(0), argument)

    if not isinstance(argument, list):
        raise TypeError(f"Op 'filter' expected array as first parameter, got {json_type(argument)}")

    if not is_jsonlogic(filter_fn):
        raise TypeError(f"Op 'filter' expected jsonlogic object as second parameter, got {json_type(filter_fn)}")

    results: list[Any] = []

    return [
        arg
        for arg in argument
        if do_ops(cast(object, arg), path.append(1), filter_fn)
    ]

    return results

@op_fn('reduce', evaluate_args=False, pass_data=True)
def op_reduce(data: object, path: JSONPath, argument: JSON, reduce_fn: JSON, initial: JSON) -> Any:
    argument = maybe_evaluate(data, path.append(0), argument)
    initial = maybe_evaluate(data, path.append(2), initial)

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
        acc["accumulator"] = do_ops(acc, path.append(1), reduce_fn)

    return acc["accumulator"]

@op_fn('all', evaluate_args=False, pass_data=True)
def op_all(data: object, path: JSONPath, argument: JSON, test_fn: JSON) -> bool:
    argument = maybe_evaluate(data, path.append(0), argument)

    if not isinstance(argument, list):
        raise TypeError(f"Op 'all' expected array as first parameter, got {json_type(argument)}")

    if not is_jsonlogic(test_fn):
        raise TypeError(f"Op 'all' expected jsonlogic object as second parameter, got {json_type(test_fn)}")

    return all([
        do_ops(cast(object, arg), path.append(i), test_fn)
        for i, arg in enumerate(argument)
    ])

@op_fn('none', evaluate_args=False, pass_data=True)
def op_none(data: object, path: JSONPath, argument: JSON, test_fn: JSON) -> bool:
    argument = maybe_evaluate(data, path.append(0), argument)

    if not isinstance(argument, list):
        raise TypeError(f"Op 'none' expected array as first parameter, got {json_type(argument)}")

    if not is_jsonlogic(test_fn):
        raise TypeError(f"Op 'none' expected jsonlogic object as second parameter, got {json_type(test_fn)}")

    return not any([
        do_ops(cast(object, arg), path.append(i), test_fn)
        for i, arg in enumerate(argument)
    ])

@op_fn('some', evaluate_args=False, pass_data=True)
def op_some(data: object, path: JSONPath, argument: JSON, test_fn: JSON) -> bool:
    argument = maybe_evaluate(data, path.append(0), argument)

    if not isinstance(argument, list):
        raise TypeError(f"Op 'some' expected array as first parameter, got {json_type(argument)}")

    if not is_jsonlogic(test_fn):
        raise TypeError(f"Op 'some' expected jsonlogic object as second parameter, got {json_type(test_fn)}")

    return not any([
        do_ops(cast(object, arg), path.append(i), test_fn)
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
def op_substr(arg: str, start: int, end: int | Type[_Missing] = _Missing) -> str:
    if end is _Missing:
        end = len(arg)
    return arg[start:end]

@op_fn('log')
def op_log(arg: object) -> object:
    print(arg)
    return arg
