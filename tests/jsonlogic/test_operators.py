import pytest

from jsonlogic.evaluate import Evaluator
from jsonlogic.operators import *

obj = {"a": 1, "b": 2, "c": 3}
arr = ["d", "e", "f"]

evaluator = Evaluator()
evaluate = evaluator.evaluate

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

    assert evaluate({"var": ["e.g", "foo"]}, obj) == "foo"
    assert evaluate({"var": ["1.5", "foo"]}, arr) == "foo"

def test_op_var_err():
    with pytest.raises(TypeError):
        evaluate({"var": 2.5}, obj)

    with pytest.raises(TypeError):
        evaluate({"var": ["a", "b", "c"]}, obj)

def test_op_missing():
    assert evaluate({"missing": ["a", "b", "c"]}, obj) == []
    assert evaluate({"missing": ["c", "d", "e"]}, obj) == ["d", "e"]

def test_op_missing_some():
    assert evaluate({"missing_some": [2, ["a", "b", "c"]]}, obj) == []
    assert evaluate({"missing_some": [2, ["b", "c", "d"]]}, obj) == []
    assert evaluate({"missing_some": [2, ["c", "d", "e"]]}, obj) == ["d", "e"]

def test_op_if():
    assert evaluate({"if": [True, "a"]}) == "a"
    assert evaluate({"if": [False, "a"]}) == None

    assert evaluate({"if": [True, "a", "b"]}) == "a"
    assert evaluate({"if": [False, "a", "b"]}) == "b"

    assert evaluate({"if": [2.5, "a", "b"]}) == "a"
    assert evaluate({"if": ["", "a", "b"]}) == "b"

    assert evaluate({"if": [False, "a", True, "b", "c"]}) == "b"
    assert evaluate({"if": [False, "a", False, "b", False, "c", "d"]}) == "d"

    import io
    import contextlib

    with io.StringIO() as output:
        with contextlib.redirect_stdout(output):
            evaluate({"if": [True, "a", {"log": "foo"}]})
            assert len(output.getvalue()) == 0

            evaluate({"if": [False, {"log": "foo"}, "b"]})
            assert len(output.getvalue()) == 0

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

def test_op_neq():
    assert evaluate({"!=": ["abc", "abc"]}) is False
    assert evaluate({"!=": ["abc", "def"]}) is True

    assert evaluate({"!=": [1, 1]}) is False
    assert evaluate({"!=": [1, "1"]}) is False
    assert evaluate({"!=": [1, "10"]}) is True
    assert evaluate({"!=": [1.5, "1.5"]}) is False

    assert evaluate({"!=": [True, 1]}) is False
    assert evaluate({"!=": [False, 0]}) is False

    assert evaluate({"!=": [1, 1.5]}) is True
    assert evaluate({"!=": ["1", 1.5]}) is True
    assert evaluate({"!=": [True, "true"]}) is True

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


def test_op_neq_eq():
    assert evaluate({"!==": ["abc", "abc"]}) is False
    assert evaluate({"!==": ["abc", "def"]}) is True

    assert evaluate({"!==": [1, 1]}) is False
    assert evaluate({"!==": [1, "1"]}) is True
    assert evaluate({"!==": [1, "10"]}) is True
    assert evaluate({"!==": [1.5, "1.5"]}) is True

    assert evaluate({"!==": [True, 1]}) is True
    assert evaluate({"!==": [False, 0]}) is True

    assert evaluate({"!==": [1, 1.5]}) is True
    assert evaluate({"!==": ["1", 1.5]}) is True
    assert evaluate({"!==": [True, "true"]}) is True

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
    assert evaluate({">": [2, 1]}) is True
    assert evaluate({">": [1, 2]}) is False
    assert evaluate({">": [2, 2]}) is False

    assert evaluate({">": [3, 2, 1]}) is True
    assert evaluate({">": [1, 2, 3]}) is False
    assert evaluate({">": [3, 2, 4]}) is False

    assert evaluate({">": [5, 4, 3, 2, 1]}) is True
    assert evaluate({">": [5, 4, 3, 1, 2]}) is False

def test_op_gte():
    assert evaluate({">=": [2, 1]}) is True
    assert evaluate({">=": [1, 2]}) is False
    assert evaluate({">=": [2, 2]}) is True

    assert evaluate({">=": [3, 2, 1]}) is True
    assert evaluate({">=": [3, 3, 1]}) is True
    assert evaluate({">=": [3, 2, 4]}) is False

    assert evaluate({">=": [5, 4, 3, 2, 1]}) is True
    assert evaluate({">=": [5, 4, 3, 1, 2]}) is False

def test_op_max():
    assert evaluate({"max": [1, 2, 3]}) == 3

def test_op_min():
    assert evaluate({"min": [1, 2, 3]}) == 1

def test_op_add():
    assert evaluate({"+": "3.5"}) == 3.5
    assert evaluate({"+": []}) == 0
    assert evaluate({"+": [2]}) == 2
    assert evaluate({"+": [2, 3]}) == 5
    assert evaluate({"+": [2, 3, 4]}) == 9

def test_op_sub():
    assert evaluate({"-": 5}) == -5
    assert evaluate({"-": [5, 3]}) == 2

def test_op_mul():
    assert evaluate({"*": []}) == 1
    assert evaluate({"*": [2]}) == 2
    assert evaluate({"*": [2, 3]}) == 6
    assert evaluate({"*": [2, 3, 4]}) == 24

def test_op_div():
    assert evaluate({"/": [5, 2]}) == 2.5

def test_op_mod():
    assert evaluate({"%": [10, 3]}) == 1

def test_op_map():
    assert evaluate({"map": [[1, 2, 3], {"+": [{"var": ""}, 1]}]}) == [2, 3, 4]

def test_op_filter():
    assert evaluate({"filter": [[1, 2, 3, 4, 5], {"==": [{"%": [{"var": ""}, 2]}, 1]}]}) == [1, 3, 5]

def test_op_reduce():
    assert evaluate({"reduce": [[1, 2, 3], {"+": [{"var": "current"}, {"var": "accumulator"}]}, 5]}) == 11

def test_op_all():
    assert evaluate({"all": [[1, 2, 3, 4, 5], {"<": [{"var": ""}, 10]}]}) is True
    assert evaluate({"all": [[1, 2, 3, 4, 5], {"<": [{"var": ""}, 3]}]}) is False
    assert evaluate({"all": [[1, 2, 3, 4, 5], {"<": [{"var": ""}, 0]}]}) is False

def test_op_none():
    assert evaluate({"none": [[1, 2, 3, 4, 5], {"<": [{"var": ""}, 10]}]}) is False
    assert evaluate({"none": [[1, 2, 3, 4, 5], {"<": [{"var": ""}, 3]}]}) is False
    assert evaluate({"none": [[1, 2, 3, 4, 5], {"<": [{"var": ""}, 0]}]}) is True

def test_op_some():
    assert evaluate({"some": [[1, 2, 3, 4, 5], {"<": [{"var": ""}, 10]}]}) is True
    assert evaluate({"some": [[1, 2, 3, 4, 5], {"<": [{"var": ""}, 3]}]}) is True
    assert evaluate({"some": [[1, 2, 3, 4, 5], {"<": [{"var": ""}, 0]}]}) is False

def test_op_merge():
    assert evaluate({"merge": ["a", ["b", "c"], "d"]}) == ["a", "b", "c", "d"]

def test_op_in():
    assert evaluate({"in": ["c", "abcdef"]}) is True
    assert evaluate({"in": ["cde", "abcdef"]}) is True
    assert evaluate({"in": ["x", "abcdef"]}) is False

    assert evaluate({"in": ["c", ["a", "b", "c"]]}) is True
    assert evaluate({"in": ["x", ["a", "b", "c"]]}) is False

def test_op_cat():
    assert evaluate({"cat": ["abc", "def"]}) == "abcdef"
    assert evaluate({"cat": ["abc", ""]}) == "abc"

def test_op_substr():
    assert evaluate({"substr": ["jsonlogic", 4]}) == "logic"
    assert evaluate({"substr": ["jsonlogic", -5]}) == "logic"

    assert evaluate({"substr": ["jsonlogic", 0, 4]}) == "json"
    assert evaluate({"substr": ["jsonlogic", 0, -5]}) == "json"

def test_op_log():
    import contextlib
    import io

    with io.StringIO() as output:
        with contextlib.redirect_stdout(output):
            assert evaluate({"log": "foo"}) == "foo"
            assert output.getvalue() == "foo\n"
    
    with io.StringIO() as output:
        with contextlib.redirect_stdout(output):
            assert evaluate({"log": {"+": [1, 2, 3]}}) == 6
            assert output.getvalue() == "6\n"
