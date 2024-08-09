import operator as py_op

from functools import reduce
from typing import (
    # Types
    Any, Sequence, Type,
    # functions
    cast, overload
)

from .evaluate import Data, maybe_evaluate
from .json import JSON, JSONArray, JSONPath, json_type
from .jsonlogic import is_jsonlogic
from .op_function import do_ops, op_fn, type_check

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

    return [do_ops(cast(Data, arg), path.join_path(1), map_fn) for arg in argument]

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
        if do_ops(cast(Data, arg), path.join_path(1), filter_fn)
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
        acc["accumulator"] = do_ops(Data(acc), path.join_path(1), reduce_fn)

    return acc["accumulator"]

@op_fn('all', evaluate_args=False, pass_data=True)
def op_all(data: Data, path: JSONPath, argument: JSON, test_fn: JSON) -> bool:
    argument = maybe_evaluate(data, path.join_path(0), argument)

    if not isinstance(argument, list):
        raise TypeError(f"Op 'all' expected array as first parameter, got {json_type(argument)}")

    if not is_jsonlogic(test_fn):
        raise TypeError(f"Op 'all' expected jsonlogic object as second parameter, got {json_type(test_fn)}")

    return all([
        do_ops(cast(Data, arg), path.join_path(i), test_fn)
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
        do_ops(cast(Data, arg), path.join_path(i), test_fn)
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
        do_ops(cast(Data, arg), path.join_path(i), test_fn)
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