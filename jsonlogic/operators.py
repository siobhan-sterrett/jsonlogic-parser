import operator as py_op

from functools import reduce
from typing import (
    # Types
    Mapping, Sequence, Type,
    # functions
    cast, overload
)

from .evaluate import Evaluator
from .json import JSON, JSONArray
from .jsonlogic import JSONLogic

op_fn = Evaluator.op_fn

class _Missing:
    """
    A sentinel class.
    """
    pass

def _has_var(data: object, key: int | str) -> bool:
    try:
        if isinstance(key, str):
            keys = key.split('.')
            for key in keys:
                data = getattr(data, '__getitem__')(key)
        elif isinstance(data, Sequence):
            data[key]
        else:
            return False
    except (AttributeError, KeyError, IndexError):
        return False
    else:
        return True

@op_fn('var', pass_data=True)
def op_var(data: object, key: int | str, default: JSON | Type[_Missing] = _Missing) -> object:
    data = cast(Mapping[int | str, object], data)

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
                return op_var(data[key], key_path[0], default)
            else:
                return data[key]
        else:
            return data[key]
    except (KeyError, IndexError, TypeError):
        if default is not _Missing:
            return default
        else:
            return None

@op_fn('missing', pass_data=True)
def op_missing(data: object, *args: str) -> list[str]:
    return [
        arg for arg in args
        if not _has_var(data, arg)
    ]

@op_fn('missing_some', pass_data=True)
def op_missing_some(data: object, count: int, args: list[str]) -> list[str]:
    missing = op_missing(data, *args)
    if len(args) - len(missing) < count:
        return missing
    return []

@op_fn('if', pass_evaluator=True, pass_data=True, evaluate_args=False)
def op_if(evaluator: Evaluator, data: object, if_arg: JSONLogic | JSON, then_arg: JSONLogic | JSON, *elses: JSONLogic | JSON) -> object:
    cond = evaluator.maybe_evaluate(if_arg, data)

    if cond:
        return evaluator.maybe_evaluate(then_arg, data)
    else:
        match len(elses):
            case 0: return None
            case 1: return evaluator.maybe_evaluate(elses[0], data)
            case _: return op_if(evaluator, data, *elses)

@op_fn('==')
def op_eq(left: object, right: object) -> bool:
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
def op_eq_eq(left: object, right: object) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return left is right
    
    return left == right

@op_fn('!=')
def op_neq(left: object, right: object) -> bool:
    return not op_eq(left, right)

@op_fn('!==')
def op_neq_eq(left: object, right: object) -> bool:
    return not op_eq_eq(left, right)

@op_fn('!')
def op_not(arg: object) -> bool:
    return not arg

@op_fn('!!')
def op_not_not(arg: object) -> bool:
    return not not arg

@op_fn('and', pass_evaluator=True, pass_data=True, evaluate_args=False)
def op_and(evaluator: Evaluator, data: object, *args: JSON) -> object:
    for arg in args:
        if not (value := evaluator.maybe_evaluate(arg, data)):
            return value
    
    return True

@op_fn('or', pass_evaluator=True, pass_data=True, evaluate_args=False)
def op_or(evaluator: Evaluator, data: object, *args: JSON) -> object:
    for arg in args:
        if value := evaluator.maybe_evaluate(arg, data):
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

@op_fn('map', pass_evaluator=True, pass_data=True, evaluate_args=False)
def op_map(evaluator: Evaluator, data: object, argument: JSON | JSONLogic, map_fn: JSONLogic) -> list[object]:
    args = evaluator.maybe_evaluate(argument, data)

    if not isinstance(args, Sequence):
        raise TypeError(f"Op 'map' expected array as first parameter, got {type(args)}")

    return [evaluator.evaluate(map_fn, arg) for arg in cast(Sequence[object], args)]

@op_fn('filter', pass_evaluator=True, pass_data=True, evaluate_args=False)
def op_filter(evaluator: Evaluator, data: object, argument: JSON | JSONLogic, filter_fn: JSONLogic) -> list[object]:
    args = evaluator.maybe_evaluate(argument, data)

    if not isinstance(args, Sequence):
        raise TypeError(f"Op 'map' expected array as first parameter, got {type(args)}")

    return [
        arg
        for arg in cast(Sequence[object], args)
        if evaluator.evaluate(filter_fn, arg)
    ]

@op_fn('reduce', pass_evaluator=True, pass_data=True, evaluate_args=False)
def op_reduce(evaluator: Evaluator, data: object, argument: JSON | JSONLogic, reduce_fn: JSONLogic, initial: JSON | JSONLogic) -> object:
    args = evaluator.maybe_evaluate(argument, data)
    init = evaluator.maybe_evaluate(initial, data)

    if not isinstance(args, Sequence):
        raise TypeError(f"Op 'reduce' expected array as first parameter, got {type(args)}")

    acc = {
        "current": None,
        "accumulator": init
    }

    for arg in cast(Sequence[object], args):
        acc["current"] = arg
        acc["accumulator"] = evaluator.evaluate(reduce_fn, acc)

    return acc["accumulator"]

@op_fn('all', pass_evaluator=True, pass_data=True, evaluate_args=False)
def op_all(evaluator: Evaluator, data: object, argument: JSON | JSONLogic, test_fn: JSONLogic) -> bool:
    args = evaluator.maybe_evaluate(argument, data)

    if not isinstance(argument, Sequence):
        raise TypeError(f"Op 'all' expected array as first parameter, got {type(args)}")

    return all([
        evaluator.evaluate(test_fn, arg)
        for arg in cast(Sequence[object], args)
    ])

@op_fn('none', pass_evaluator=True, pass_data=True, evaluate_args=False)
def op_none(evaluator: Evaluator, data: object, argument: JSON | JSONLogic, test_fn: JSONLogic) -> bool:
    args = evaluator.maybe_evaluate(argument, data)

    if not isinstance(args, Sequence):
        raise TypeError(f"Op 'none' expected array as first parameter, got {type(args)}")

    return not any([
        evaluator.evaluate(test_fn, arg)
        for arg in cast(Sequence[object], args)
    ])

@op_fn('some', pass_evaluator=True, pass_data=True, evaluate_args=False)
def op_some(evaluator: Evaluator, data: object, argument: JSON | JSONLogic, test_fn: JSONLogic) -> bool:
    args = evaluator.maybe_evaluate(argument, data)

    if not isinstance(args, Sequence):
        raise TypeError(f"Op 'none' expected array as first parameter, got {type(args)}")

    return any([
        evaluator.evaluate(test_fn, arg)
        for arg in cast(Sequence[object], args)
    ])

@op_fn('merge')
def op_merge(*args: object) -> list[object]:
    result: list[object] = []

    for arg in args:
        if isinstance(arg, list):
            result += arg
        else:
            result += [arg]

    return result

@overload
def op_in(needle: str, haystack: str) -> bool:
    ...
@overload
def op_in(needle: JSON, haystack: JSONArray) -> bool:
    ...
@op_fn('in')
def op_in(needle: JSON, haystack: str | JSONArray) -> bool:
    if isinstance(haystack, str):
        if isinstance(needle, str):
            return needle in haystack
        else:
            raise TypeError(f"Expected str as first argument, got {type(needle)}")
    else:
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
