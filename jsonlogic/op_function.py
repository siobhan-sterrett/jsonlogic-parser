from dataclasses import dataclass
from functools import wraps
from inspect import signature, Signature, Parameter
from types import UnionType
from typing import (
    # Types
    Any, Callable, Literal, MutableMapping, NewType,
    # Generics
    Concatenate, ParamSpec, TypeVar,
    # functions
    cast, get_args, get_origin, get_overloads, overload
)

from .evaluate import maybe_evaluate
from .json import JSONArray, JSONPath
from .jsonlogic import JSONLogic
from .op_function import Operator
    
@dataclass
class EvaluationError(RuntimeError):
    where: JSONPath

@dataclass
class UnrecognizedOperand(EvaluationError):
    op: str

def op_args(jsonlogic: JSONLogic) -> tuple[Operator, JSONArray]:
    op, arg = next(iter(jsonlogic.items()))
    if isinstance(arg, list):
        return op, arg
    else:
        return op, [arg]

def do_ops(data: object, path: JSONPath, jsonlogic: JSONLogic) -> Any:
    """
    The main evaluation logic.

    This function selects the appropriate OpFunction, and passes it
    the appropriate args. OpFunctions, in turn, recursively call
    _evaluate().

    The path parameter is used to track the current position within
    the JSONLogic object, for error reporting.
    """
    op, args = op_args(jsonlogic)

    if op_fn := op_fns.get(op):
        return op_fn(data, path, *args)
    else:
        raise UnrecognizedOperand(where=path, op=op)

Operator = NewType('Operator', str)

T = TypeVar('T')
P = ParamSpec('P')

OpFunction = Callable[Concatenate[object, JSONPath, P], T]
"""
An OpFunction is a function that's called during
evaluation of a data object. Each operator is associated
with a specific OpFunction that tells it how to operate
on the given data.
"""

op_fns: MutableMapping[Operator, OpFunction[..., Any]] = {}
"""
_op_fns is a global dict that maps each supported operator
to the function that implements it.
"""

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
            def op_fn(data: object, path: JSONPath, *args: P.args, **kwargs: P.kwargs):
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
        def wrapper(data: object, path: JSONPath, *_args: P.args, **kwargs: P.kwargs) -> T:
            if evaluate_args:
                args = tuple(
                    maybe_evaluate(data, path.join_path(op).join_path(i), arg)
                    for i, arg in enumerate(_args))
            else:
                args = _args

            return op_fn(data, path, *args, **kwargs)

        if op in op_fns:
            raise RuntimeError(f"Op '{op}' assigned to multiple op functions")
        else:
            op_fns[op] = wrapper

        return fn

    return decorator
