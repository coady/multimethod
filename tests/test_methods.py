import pytest
from typing import Any, Dict, Iterable, List, Tuple, Union
from multimethod import (
    DispatchError,
    get_type,
    isa,
    multimeta,
    multimethod,
    overload,
    signature,
    subtype,
)


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
def test_subtype():
    assert len({subtype(List[int]), subtype(List[int])}) == 1
    assert len({subtype(List[bool]), subtype(List[int])}) == 2
    assert issubclass(int, subtype(Union[int, float]))
    assert issubclass(Union[float, int], subtype(Union[int, float]))
    assert issubclass(List[bool], subtype(List[int]))
    assert not issubclass(Tuple[int], subtype(Tuple[int, float]))
    assert issubclass(Iterable[bool], subtype(Iterable[int]))
    assert issubclass(subtype(Iterable[int]), subtype(Iterable))
    assert issubclass(subtype(List[int]), subtype(Iterable))

    assert get_type(0) is int
    assert not isinstance(get_type(iter('')), subtype)
    assert get_type(()) is tuple
    assert get_type((0, 0.0)) == subtype(tuple, int, float)
    assert get_type([]) is list
    assert get_type([0, 0.0]) == subtype(list, int)
    assert get_type({}) is dict
    assert get_type({' ': 0}) == subtype(dict, str, int)


def test_signature():
    assert signature([Any, List]) == (object, list)
    assert signature([List]) <= signature([list])
    assert signature([list]) <= signature([List])
    assert signature([list]) <= signature([List[int]])
    assert signature([List[int]]) - signature([list])
    assert signature([list]) - signature([List[int]]) == (1,)


class cls:
    @multimethod
    def method(x, y: int, z=None) -> tuple:
        return object, int

    @multimethod
    def method(x: 'cls', y: float):
        return type(x), float


def test_annotations():
    obj = cls()
    assert obj.method(0.0) == (cls, float)  # run first to check exact match post-evaluation
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


@func.register
def _(arg: Union[List[int], Tuple[float], Dict[str, int]]):
    return 'union'


def test_register():
    assert func(0.0) is object
    assert func(0) is int
    assert func(False) is bool
    assert func([0]) == func((0.0,)) == func({'': 0}) == 'union'
    assert func([0.0]) == func((0.0, 1.0)) == func({}) == object


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


# multimeta


def test_meta():
    class meta(metaclass=multimeta):
        def method(self, x: str):
            return 'STR'

        def method(self, x: int):
            return 'INT'

        def normal(self, y):
            return 'OBJECT'

        def rebind(self, x: str):
            return 'INITIAL'

        rebind = 2

        def rebind(self, x):
            return 'REBOUND'

    assert isinstance(meta.method, multimethod)
    assert isinstance(meta.normal, multimethod)
    assert isinstance(meta.rebind, multimethod)

    m = meta()

    assert m.method('') == 'STR'
    assert m.method(12) == 'INT'
    assert m.normal('') == 'OBJECT'
    assert m.rebind('') == 'REBOUND'
