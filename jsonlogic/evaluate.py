from functools import wraps
from inspect import signature, Parameter
from types import UnionType
from typing import Callable, ClassVar, Sequence, Self, Union, cast, get_args, get_origin, get_overloads, overload

from .json import JSON, JSONObject
from .jsonlogic import JSONLogic

class Evaluator:
    _op_fns: ClassVar[dict[str, Callable[[Self, object, Sequence[JSONLogic | JSON]], object]]] = {}

    @overload
    def evaluate(self, jsonlogic: JSONLogic | JSONObject) -> JSON:
        ...
    @overload
    def evaluate(self, jsonlogic: JSONLogic | JSONObject, data: object) -> object:
        ...
    def evaluate(self, jsonlogic: JSONLogic | JSONObject, data: object = None) -> object:
        if not isinstance(jsonlogic, JSONLogic):
            jsonlogic = JSONLogic(jsonlogic)

        return self._evaluate(jsonlogic, data)
    
    def _evaluate(self, jsonlogic: JSONLogic, data: object) -> object:
        op, args = jsonlogic.op, jsonlogic.args

        try:
            op_fn = self._op_fns[op]
        except KeyError:
            raise ValueError(f"Unrecognized operator: '{op}")
        
        return op_fn(self, data, args)
    
    def maybe_evaluate(self, arg: object, data: object) -> object:
        if isinstance(arg, JSONLogic):
            return self._evaluate(arg, data)
        else:
            return arg
        
    @staticmethod
    def _type_check_parameter(arg_value: object, annotation: object):
        if isinstance(annotation, type):
            if not isinstance(arg_value, annotation):
                raise TypeError
        
        # Handle subscripted types
        elif origin := get_origin(annotation):
            # Handle Union or Optional
            if origin in (Union, UnionType):
                for ann in get_args(annotation):
                    try:
                        Evaluator._type_check_parameter(arg_value, ann)
                    except TypeError:
                        continue
                    else:
                        return
                else:
                    raise TypeError
            
            # Handle Sequence, Mapping, etc
            else:
                if not isinstance(arg_value, origin):
                    raise TypeError
        
    @staticmethod
    def _type_check_fn(fn: Callable[..., object], args: Sequence[object]):
        fn_sig = signature(fn)
        bound_args = fn_sig.bind(*args)

        for arg_name, arg_value in bound_args.arguments.items():
            parameter = fn_sig.parameters[arg_name]
            annotation = parameter.annotation

            match parameter.kind:
                case Parameter.POSITIONAL_ONLY | Parameter.POSITIONAL_OR_KEYWORD:
                    try:
                        Evaluator._type_check_parameter(arg_value, annotation)
                    except TypeError:
                        raise TypeError(f"Function {fn} parameter {arg_name} received argument of incorrect type: {arg_value} (expected {annotation})")
                case Parameter.VAR_POSITIONAL:
                    if isinstance(arg_value, tuple):
                        for value in cast(tuple[object, ...], arg_value):
                            try:
                                Evaluator._type_check_parameter(value, annotation)
                            except TypeError:
                                raise TypeError(f"Function {fn} parameter {arg_name} received argument of incorrect type: {value} (expected {annotation})")
                    else:
                        raise TypeError(f"Error in Evaluator._type_check; expected arg_value to be tuple, got {type(arg_value)}")
                case Parameter.KEYWORD_ONLY | Parameter.VAR_KEYWORD:
                    raise TypeError(f"Operator functions cannot take keyword-only arguments!")
    
                
    @staticmethod
    def _type_check(fn: Callable[..., object], args: Sequence[object]):
        # Handle overloaded functions
        if overloads := get_overloads(fn):
            for overload in overloads:
                try:
                    Evaluator._type_check_fn(overload, args)
                except TypeError:
                    continue
                else:
                    return
            
            raise TypeError(f"No matching overload for function {fn} found for args: {args}")
        else:
            Evaluator._type_check_fn(fn, args)
        
    def _evaluate_args(self, args: Sequence[JSONLogic | JSON], data: object) -> list[object]:
        evaluated_args: list[object] = []
        for arg in args:
            if isinstance(arg, JSONLogic):
                evaluated_args.append(self.evaluate(arg, data))
            else:
                evaluated_args.append(arg)

        return evaluated_args

    @classmethod
    def op_fn(cls, op: str, pass_evaluator: bool = False, pass_data: bool = False, evaluate_args: bool = True):
        if op in cls._op_fns:
            raise ValueError(f"Operator 'op' is already registered with evaluator class {cls}")

        def decorator[T](fn: Callable[..., T]) -> Callable[..., T]:
            @wraps(fn)
            def op_fn(self: Self, data: object, args: Sequence[JSONLogic | JSON]) -> T:
                evaluated_args: list[object]
                if evaluate_args:
                    evaluated_args = self._evaluate_args(args, data)
                else:
                    evaluated_args = list(args)
                
                if pass_data:
                    evaluated_args = [data] + evaluated_args
                if pass_evaluator:
                    evaluated_args = [self] + evaluated_args

                self._type_check(fn, evaluated_args)

                return fn(*evaluated_args)

            cls._op_fns[op] = op_fn

            return fn

        return decorator
