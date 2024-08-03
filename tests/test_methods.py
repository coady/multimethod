import enum
import types
import pytest
from collections.abc import Collection, Iterable, Mapping, Set
from typing import Annotated, Any, AnyStr, NewType, Protocol, Sized, TypeVar, Union
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
    with pytest.raises(DispatchError):
        assert join(tree(seq), bracket(*sep)) == '<0><1><2>'
    join[tree, bracket] = join[tree, object]
    assert join(tree(seq), bracket(*sep)) == '<0><1><2>'


def subclass(*bases, **kwds):
    return types.new_class('', bases, kwds)


@pytest.mark.benchmark
def test_subtype():
    assert len({subtype(list[int]), subtype(list[int])}) == 1
    assert len({subtype(list[bool]), subtype(list[int])}) == 2
    assert issubclass(int, subtype(Union[int, float]))
    assert issubclass(Union[float, int], subtype(Union[int, float]))
    assert issubclass(list[bool], subtype(list[int]))
    assert isinstance((0, 0.0), subtype(tuple[int, float]))
    assert not isinstance((0,), subtype(tuple[int, float]))
    assert isinstance((0,), subtype(tuple[int, ...]))
    assert not issubclass(tuple[int], subtype(tuple[int, ...]))
    assert not isinstance(iter('-'), subtype(Iterable[str]))
    assert not issubclass(tuple[int], subtype(tuple[int, float]))
    assert issubclass(Iterable[bool], subtype(Iterable[int]))
    assert issubclass(subtype(Iterable[int]), subtype(Iterable))
    assert issubclass(subtype(list[int]), subtype(Iterable))
    assert issubclass(list[bool], subtype(Union[list[int], list[float]]))
    assert issubclass(subtype(Union[bool, int]), int)
    assert issubclass(subtype(Union[Mapping, Set]), Collection)
    base = subclass(metaclass=subclass(type))
    assert subtype(Union[base, subclass(base)])
    assert not list(subtype.origins(subclass(subclass(Protocol))))
    assert not list(subtype.origins(subclass(Sized)))
    assert not list(subtype.origins(subclass(Protocol[TypeVar('T')])))
    assert subtype(Annotated[str, "test"]) is str


@pytest.mark.benchmark
def test_signature():
    assert signature([Any, list, NewType('', int)]) == (object, list, int)
    assert signature([AnyStr]) == signature([Union[bytes, str]])
    assert signature([TypeVar('T')]) == signature([object])
    assert signature([list]) <= (list,)
    assert signature([list]) <= signature([list])
    assert signature([list]) <= signature([list[int]])


class namespace:
    pass


class cls:
    @multimethod
    def method(x, y: int, z=None) -> tuple:
        return object, int

    @multimethod
    def method(x: 'cls', y: 'list[float]'):
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
    key = cls, subtype(list[float])
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
def _(arg: Union[list[int], tuple[float], dict[str, int]]):
    return 'union'


def test_register():
    assert func(0.0) is object
    assert func(0) is int
    assert func(False) is bool
    assert func([0]) == func((0.0,)) == func({'': 0}) == func({}) == 'union'
    assert func([0.0]) is func((0.0, 1.0)) is object


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
    def func(arg: tuple[tuple[int, int], ...]):
        return arg

    tup = ((0, 1),)
    assert func(tup) == tup
    tup = ((0, 1), (2, 3))
    assert func(tup) == tup
    assert func(()) == ()
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
    temp = 123

    # a multimethod shadowing that name
    @multimethod
    def temp(x: int):
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

    @multimethod
    def temp(x: int, y: object):
        return "int, object"

    with pytest.raises(DispatchError, match="test_methods.py"):
        # invalid number of args, check source file is part of the exception args
        temp(1)
    assert temp(1, y=1.0) == "int"
    assert temp(True) == "bool"
    assert temp(True, 1.0) == "int, float"

    @multimethod
    def temp(x: bool, y: float = 0.0):
        return "optional"

    assert temp(True, 1.0) == "optional"
