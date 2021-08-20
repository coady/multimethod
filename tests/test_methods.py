import enum
import sys
import pytest
from typing import Any, AnyStr, Dict, Generic, Iterable, Iterator, List, Tuple, TypeVar, Union
from multimethod import DispatchError, multimeta, multimethod, signature, subtype


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

    assert subtype.get_type(object, 0) is int
    assert not isinstance(subtype.get_type(object, iter('')), subtype)
    assert subtype.get_type(object, ()) is tuple
    tp = subtype(tuple, int, float)
    assert tp.get_type((0, 0.0)) == tp
    assert subtype.get_type(object, []) is list
    tp = subtype(dict, str, int)
    assert tp.get_type({' ': 0}) == tp
    tp = subtype(list, int)
    assert tp.get_type([0, 0.0]) == tp
    assert subtype.get_type(object, {}) is dict
    it = iter('abc')
    assert subtype(Iterator[str]).get_type(it) is type(it)
    tp = subtype(Union, List[int], List[List[int]])
    assert tp.get_type('') is str
    assert tp.get_type([]) is list
    assert tp.get_type([0]) == List[int]
    assert tp.get_type([[]]) == List[list]
    assert tp.get_type([[0]]) == List[List[int]]


def test_signature():
    assert signature([Any, List]) == (object, list)
    assert signature([AnyStr]) == signature([Union[bytes, str]])
    assert signature([TypeVar('T')]) == signature([object])
    assert signature([int]) - signature([Union[int, float]]) == (0,)
    assert signature([List]) <= (list,)
    assert signature([list]) <= signature([List])
    assert signature([list]) <= signature([List[int]])
    assert signature([List[int]]) - signature([list])
    assert signature([list]) - signature([List[int]]) == (1,)

    # with metaclasses:
    assert signature([type]) - (type,) == (0,)
    assert (type,) - signature([object]) == (1,)
    # using EnumMeta because it is a standard, stable, metaclass
    assert signature([enum.EnumMeta]) - signature([object]) == (2,)
    assert signature([Union[type, enum.EnumMeta]]) - signature([object]) == (1,)


def test_get_type():
    method = multimethod(lambda: None)
    assert method.type_checkers == []

    @method.register
    def _(x: Union[int, type(None)]):
        pass

    assert method.type_checkers == [type]

    @method.register
    def _(x: List[int]):
        pass

    (get_type,) = method.type_checkers
    assert get_type([0]) == List[int]
    assert get_type([0.0]) == List[float]
    assert get_type((0,)) is tuple
    method[int, float] = lambda x, y: None
    assert method.type_checkers == [get_type, type]


class namespace:
    pass


class cls:
    @multimethod
    def method(x, y: int, z=None) -> tuple:
        return object, int

    @multimethod
    def method(x: 'cls', y: 'List[float]'):
        return type(x), list

    @multimethod
    def dotted(x: 'namespace.cls'):
        return type(x), float


def test_annotations():
    obj = cls()
    assert obj.method([0.0]) == (cls, list)  # run first to check exact match post-evaluation
    assert obj.method(0) == (object, int)
    assert cls.method(None, 0) == (object, int)
    with pytest.raises(DispatchError):
        cls.method(None, 0.0)
    key = cls, subtype(List[float])
    cls.method.pending.add(cls.method.pop(key))
    assert cls.method[key]


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


def test_ellipsis():
    @multimethod
    def func(arg: Tuple[Tuple[int, int], ...]):
        return arg

    tup = ((0, 1),)
    assert func(tup) == tup
    tup = ((0, 1), (2, 3))
    assert func(tup) == tup
    with pytest.raises(DispatchError):
        func(())
    with pytest.raises(DispatchError):
        func(((0, 1.0),))


def test_meta_types():
    @multimethod
    def f(x):
        return "object"

    @f.register
    def f(x: type):
        return "type"

    @f.register
    def f(x: enum.EnumMeta):
        return "enum"

    @f.register
    def f(x: enum.Enum):
        return "member"

    dummy_enum = enum.Enum("DummyEnum", names="SPAM EGGS HAM")
    assert f(123) == "object"
    assert f(int) == "type"
    assert f(dummy_enum) == "enum"
    assert f(dummy_enum.EGGS) == "member"


def test_name_shadowing():
    # an object with the same name appearing previously in the same namespace
    temp = 123  # noqa

    # a multimethod shadowing that name
    @multimethod
    def temp(x: int):  # noqa
        return "int"

    @multimethod
    def temp(x: float):
        return "float"

    assert isinstance(temp, multimethod)
    assert temp(0) == "int"
    assert temp(0.0) == "float"


def test_dispatch_exception():
    @multimethod
    def temp(x: int, y):
        return "int"

    @multimethod
    def temp(x: int, y: float):
        return "int, float"

    @multimethod
    def temp(x: bool):
        return "bool"

    with pytest.raises(DispatchError, match="test_methods.py"):
        # invalid number of args, check source file is part of the exception args
        temp(1)
    assert temp(1, y=1.0) == "int"
    assert temp(True) == "bool"
    assert temp(True, 1.0) == "int, float"

    @multimethod
    def temp(x: bool, y=0.0):
        return "optional"

    assert temp(True, 1.0) == "optional"


@pytest.mark.skipif(sys.version_info < (3, 8), reason="Literal added in 3.8")
def test_literals():
    from typing import Literal

    assert subtype(Literal['a', 'b']) is str
    assert subtype(Literal['a', 0]) == subtype(Union[str, int])

    @multimethod
    def func(arg: Literal[0]):
        return arg

    assert func(0) == 0
    assert func(1) == 1
    with pytest.raises(DispatchError):
        func(0.0)


def test_generic():
    class cls(Generic[TypeVar('T')]):
        pass

    @multimethod
    def func(x: cls[int]):
        pass

    assert func(cls[int]()) is None
