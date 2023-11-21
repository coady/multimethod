import sys
import pytest
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Generic, Literal, Type, TypeVar
from multimethod import distance, multimethod, subtype, DispatchError


def test_literals():
    assert issubclass(subtype(Literal['a', 'b']), str)
    assert not issubclass(subtype(Literal['a']), subtype(list[int]))
    assert issubclass(Literal[[0]], subtype(Iterable[int]))
    tp = subtype(Literal['a', 0])
    assert issubclass(tp.get_type('a'), tp)
    assert issubclass(tp.get_type(0), tp)
    assert not issubclass(tp.get_type('b'), tp)
    assert tp.get_type('b') is str
    assert tp.get_type(0.0) is float

    @multimethod
    def func(arg: Literal['a', 0]):
        return arg

    assert func(0) == 0
    with pytest.raises(DispatchError):
        func(1)
    with pytest.raises(DispatchError):
        func(0.0)


@pytest.mark.skipif(sys.version_info < (3, 10), reason="Union syntax added in 3.10")
def test_union():
    assert issubclass(int, subtype(int | float))
    assert issubclass(subtype(int | float), subtype(int | float | None))


def test_type():
    @multimethod
    def func(arg: Type[int]):
        return arg

    assert isinstance(int, subtype(Type[int]))
    assert func(int) is int
    assert func(bool) is bool
    with pytest.raises(DispatchError):
        func(float)
    with pytest.raises(DispatchError):
        func(0)


def test_generic():
    class cls(Generic[TypeVar('T')]):
        pass

    @multimethod
    def func(x: cls[int]):
        pass

    assert distance(object, cls[int])
    obj = cls[int]()
    assert isinstance(obj, subtype(cls[int]))
    assert func(obj) is None


def test_empty():
    @multimethod
    def func(arg: list[int]):
        return int

    @func.register
    def _(arg: list[bool]):
        return bool

    assert func([0]) is int
    assert func([False]) is func([]) is bool


def test_callable():
    def f(arg: bool) -> int:
        ...

    def g(arg: int) -> bool:
        ...

    def h(arg) -> bool:
        ...

    @multimethod
    def func(arg: Callable[[bool], bool]):
        return arg.__name__

    @func.register
    def _(arg: Callable[..., bool]):
        return ...

    @func.register
    def _(arg: int):
        return 'int'

    @func.register
    def _(arg: Sequence[Callable[[bool], bool]]):
        return arg[0].__name__ + "0"

    tp = subtype(func.__annotations__['arg'])
    assert not issubclass(tp.get_type(f), tp.get_type(g))
    assert isinstance(g, tp.get_type(f))
    assert issubclass(tp.get_type(g), tp.get_type(f))
    with pytest.raises(DispatchError):
        func(f)
    assert func(g) == 'g'
    assert func([g]) == 'g0'
    assert func(h) is ...


def test_final():
    tp = subtype(Iterable[str])
    d = {'': 0}
    assert isinstance(d, subtype(Mapping[str, int]))
    assert issubclass(tp.get_type(d), tp)
    assert issubclass(tp.get_type(d.keys()), tp)
