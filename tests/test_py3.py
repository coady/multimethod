import sys
import pytest
from multimethod import isa, multimethod, overload, DispatchError
type_hints = sys.version_info >= (3, 5)
skip34 = pytest.mark.skipif(not type_hints, reason="requires Python >=3.5")


# string join
class tree(list):
    def walk(self):
        for value in self:
            if isinstance(value, type(self)):
                yield from value.walk()
            else:
                yield value


class bracket(tuple):
    def __new__(cls, left, right):
        return tuple.__new__(cls, (left, right))


@multimethod
def join(seq, sep):
    return sep.join(map(str, seq))


@multimethod
def join(seq: object, sep: bracket):
    return sep[0] + join(seq, sep[1] + sep[0]) + sep[1]


@multimethod
def join(seq: tree, sep: object):
    return join(seq.walk(), sep)


def test_join():
    sep = '<>'
    seq = [0, tree([1]), 2]
    assert list(tree(seq).walk()) == list(range(3))
    assert join(seq, sep) == '0<>[1]<>2'
    assert join(tree(seq), sep) == '0<>1<>2'
    assert join(seq, bracket(*sep)) == '<0><[1]><2>'
    assert join(tree(seq), bracket(*sep)) == '<0><1><2>'


# type hints
class cls:
    @multimethod
    def method(x: object, y: int) -> tuple:
        return object, int

    if type_hints:
        @multimethod
        def method(x: 'cls', y: float):
            return type(x), float


def test_annotations():
    obj = cls()
    if type_hints:  # run first to check exact match post-evaluation
        assert obj.method(0.0) == (cls, float)
    else:
        with pytest.raises(DispatchError):
            obj.method(0.0)
    assert obj.method(0) == (object, int)
    assert cls.method(None, 0) == (object, int)
    with pytest.raises(DispatchError):
        cls.method(None, 0.0)


# register out of order
@multimethod
def func(arg: bool):
    return bool


@func.register
def _(arg: object):
    return object


@func.register
def _(arg: int):
    return int


def test_register():
    func.strict = True
    assert func(0.0) is object
    assert func(0) is int
    assert func(False) is bool


@skip34
def test_overloads():
    @overload
    def func(x):
        return x

    @overload
    def func(x: isa(int, float)):
        return -x

    @func.register
    def _(x: isa(str)):
        return x.upper()
    assert func(None) is None
    assert func(1) == -1
    assert func('hi') == 'HI'
    del func[next(iter(func))]
    with pytest.raises(DispatchError):
        func(None)
