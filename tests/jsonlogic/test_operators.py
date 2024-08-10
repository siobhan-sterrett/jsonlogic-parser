import pytest

from jsonlogic.evaluate import evaluate
from jsonlogic.operators import *

obj = {"a": 1, "b": 2, "c": 3}
arr = ["d", "e", "f"]

def test_op_var():
    assert evaluate({"var": "a"}, obj) == 1
    assert evaluate({"var": 2}, arr)   == 'f'

    assert evaluate({"var": "d"}, obj) is None
    assert evaluate({"var": 6}, arr)   is None

    assert evaluate({"var": ["d", "default"]}, obj) == "default"
    assert evaluate({"var": [6, "default"]}, arr)   == "default"

def test_op_var_path():
    obj = {
        'a': ['b', 'c', 'd'],
        'e': { 'f': 4 }
    }
    arr = [[1, 2, 3], [4, 5, 6]]

    assert evaluate({"var": ""}, obj) == obj
    assert evaluate({"var": "a.1"}, obj) == 'c'
    assert evaluate({"var": "e.f"}, obj) == 4
    assert evaluate({"var": "1.2"}, arr) == 6

def test_op_var_err():
    with pytest.raises(TypeError):
        evaluate({"var": 2.5}, obj)

    with pytest.raises(TypeError):
        evaluate({"var": ["a", "b", "c"]}, obj)

# TODO: op_missing
# TODO: op_missing_some

def test_op_if():
    assert evaluate({"if": [True, "a"]}) == "a"
    assert evaluate({"if": [False, "a"]}) == None

    assert evaluate({"if": [True, "a", "b"]}) == "a"
    assert evaluate({"if": [False, "a", "b"]}) == "b"

    assert evaluate({"if": [2.5, "a", "b"]}) == "a"
    assert evaluate({"if": ["", "a", "b"]}) == "b"

    assert evaluate({"if": [False, "a", True, "b", "c"]}) == "b"
    assert evaluate({"if": [False, "a", False, "b", False, "c", "d"]}) == "d"

def test_op_if_err():
    with pytest.raises(TypeError):
        evaluate({"if": []})

    with pytest.raises(TypeError):
        evaluate({"if": [True]})

def test_op_eq():
    assert evaluate({"==": ["abc", "abc"]}) is True
    assert evaluate({"==": ["abc", "def"]}) is False

    assert evaluate({"==": [1, 1]}) is True
    assert evaluate({"==": [1, "1"]}) is True
    assert evaluate({"==": [1, "10"]}) is False
    assert evaluate({"==": [1.5, "1.5"]}) is True

    assert evaluate({"==": [True, 1]}) is True
    assert evaluate({"==": [False, 0]}) is True

    assert evaluate({"==": [1, 1.5]}) is False
    assert evaluate({"==": ["1", 1.5]}) is False
    assert evaluate({"==": [True, "true"]}) is False

def test_op_eq_err():
    with pytest.raises(TypeError):
        evaluate({"==": []})

    with pytest.raises(TypeError):
        evaluate({"==": [1, 2, 3]})

# TODO: test_op_neq

def test_op_eq_eq():
    assert evaluate({"===": ["abc", "abc"]}) is True
    assert evaluate({"===": ["abc", "def"]}) is False

    assert evaluate({"===": [1, 1]}) is True
    assert evaluate({"===": [1, "1"]}) is False
    assert evaluate({"===": [1, "10"]}) is False
    assert evaluate({"===": [1.5, "1.5"]}) is False

    assert evaluate({"===": [True, 1]}) is False
    assert evaluate({"===": [False, 0]}) is False

    assert evaluate({"===": [1, 1.5]}) is False
    assert evaluate({"===": ["1", 1.5]}) is False
    assert evaluate({"===": [True, "true"]}) is False


# TODO: test_op_neq_eq

def test_op_not():
    assert evaluate({"!": True}) is False
    assert evaluate({"!": False}) is True

    assert evaluate({"!": 1}) is False
    assert evaluate({"!": 0}) is True

    assert evaluate({"!": 1.5}) is False
    assert evaluate({"!": 0.0}) is True

    assert evaluate({"!": [None]}) is True

    assert evaluate({"!": [["a", "b", "c"]]}) is False
    assert evaluate({"!": [[]]}) is True

    assert evaluate({"!": {"a": 1, "b": 2}}) is False
    assert evaluate({"!": {}}) is True

def test_op_not_not():
    assert evaluate({"!!": True}) is True
    assert evaluate({"!!": False}) is False

    assert evaluate({"!!": 1}) is True
    assert evaluate({"!!": 0}) is False

    assert evaluate({"!!": 1.5}) is True
    assert evaluate({"!!": 0.0}) is False

    assert evaluate({"!!": [None]}) is False

    assert evaluate({"!!": [["a", "b", "c"]]}) is True
    assert evaluate({"!!": [[]]}) is False

    assert evaluate({"!!": {"a": 1, "b": 2}}) is True
    assert evaluate({"!!": {}}) is False

def test_op_and():
    assert evaluate({"and": [True, False]}) is False
    assert evaluate({"and": [True, True]}) is True

    assert evaluate({"and": [1, 0, 2]}) == 0
    assert evaluate({"and": [1, 2, 3]}) is True

    assert evaluate({"and": [1]}) is True
    assert evaluate({"and": [0]}) == 0

    assert evaluate({"and": []}) is True

def test_op_or():
    assert evaluate({"or": [False, False]}) is False
    assert evaluate({"or": [False, True]}) is True

    assert evaluate({"or": [0, 1, 0]}) == 1
    assert evaluate({"or": [0, None, False]}) is False

    assert evaluate({"or": [1]}) is 1
    assert evaluate({"or": [0]}) == 0

    assert evaluate({"or": []}) is False

def test_op_lt():
    assert evaluate({"<": [1, 2]}) is True
    assert evaluate({"<": [2, 1]}) is False
    assert evaluate({"<": [2, 2]}) is False

    assert evaluate({"<": [1, 2, 3]}) is True
    assert evaluate({"<": [1, 1, 3]}) is False
    assert evaluate({"<": [1, 2, 0]}) is False

    assert evaluate({"<": [1, 2, 3, 4, 5]}) is True
    assert evaluate({"<": [1, 2, 3, 5, 4]}) is False

def test_op_lte():
    assert evaluate({"<=": [1, 2]}) is True
    assert evaluate({"<=": [2, 1]}) is False
    assert evaluate({"<=": [2, 2]}) is True

    assert evaluate({"<=": [1, 2, 3]}) is True
    assert evaluate({"<=": [1, 1, 3]}) is True
    assert evaluate({"<=": [1, 2, 0]}) is False

    assert evaluate({"<=": [1, 2, 3, 4, 5]}) is True
    assert evaluate({"<=": [1, 2, 3, 5, 4]}) is False

def test_op_gt():
    assert evaluate({">": [1, 2]}) is True
    assert evaluate({">": [2, 1]}) is False
    assert evaluate({">": [2, 2]}) is False

    assert evaluate({">": [1, 2, 3]}) is True
    assert evaluate({">": [1, 1, 3]}) is False
    assert evaluate({">": [1, 2, 0]}) is False

    assert evaluate({">": [1, 2, 3, 4, 5]}) is True
    assert evaluate({">": [1, 2, 3, 5, 4]}) is False

def test_op_gte():
    assert evaluate({">=": [1, 2]}) is True
    assert evaluate({">=": [2, 1]}) is False
    assert evaluate({">=": [2, 2]}) is True

    assert evaluate({">=": [1, 2, 3]}) is True
    assert evaluate({">=": [1, 1, 3]}) is True
    assert evaluate({">=": [1, 2, 0]}) is False

    assert evaluate({">=": [1, 2, 3, 4, 5]}) is True
    assert evaluate({">=": [1, 2, 3, 5, 4]}) is False
