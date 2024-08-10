from .json import JSONPath

class EvaluationError(RuntimeError):
    where: JSONPath

class NullDataAccess(EvaluationError):
    pass

class UnrecognizedOperand(EvaluationError):
    pass
