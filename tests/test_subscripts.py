import asyncio
import inspect
import sys
import typing
import pytest
from array import array
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Generic, Literal, Type, TypeVar, Union
from multimethod import multimethod, parametric, subtype, DispatchError


def test_literals():
    assert issubclass(subtype(Literal['a', 'b']), str)
    assert not issubclass(subtype(Literal['a']), subtype(list[int]))
    assert issubclass(Literal[[0]], subtype(Iterable[int]))
    tp = subtype(Literal['a', 0])
    assert isinstance('a', tp)
    assert isinstance(0, tp)
    assert not issubclass(Literal['a', 0.0], tp)
    assert not issubclass(tuple[str, int], tp)
    assert issubclass(tp, subtype(Union[str, int]))

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
    assert subtype(Iterable | Mapping | Sequence) is Iterable


@pytest.mark.skipif(sys.version_info < (3, 12), reason="Type aliases added in 3.12")
def test_type_alias():
    Point = typing.TypeAliasType(name='Point', value=tuple[int, int])
    assert isinstance((0, 0), subtype(Point))


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

    assert func[list[int],]
    assert func([0]) is int
    assert func([False]) is func([]) is bool


def test_callable():
    def f(arg: bool) -> int: ...

    def g(arg: int) -> bool: ...

    def h(arg) -> bool: ...

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

    with pytest.raises(DispatchError):
        func(f)
    assert func(g) == 'g'
    assert func([g]) == 'g0'
    assert func(h) is ...


def test_final():
    tp = subtype(Iterable[str])
    d = {'': 0}
    assert isinstance(d, subtype(Mapping[str, int]))
    assert isinstance(d.keys(), tp)


def test_args():
    tp = type('', (), {'__args__': None})
    assert subtype(tp) is tp
    assert not issubclass(tp, subtype(list[int]))
    assert subtype(typing.Callable) is Callable


@pytest.mark.benchmark
def test_parametric():
    coro = parametric(Callable, inspect.iscoroutinefunction)
    assert issubclass(coro, Callable)
    assert not issubclass(Callable, coro)
    assert not issubclass(parametric(object, inspect.iscoroutinefunction), coro)
    assert isinstance(asyncio.sleep, coro)
    assert not isinstance(lambda: None, coro)
    assert list(subtype.origins(coro)) == [Callable]

    ints = parametric(array, typecode='i')
    assert issubclass(ints, array)
    assert not issubclass(array, ints)
    sized = parametric(array, itemsize=4)
    assert issubclass(sized & ints, ints)
    assert not issubclass(ints, sized & ints)
    assert not issubclass(parametric(object, typecode='i'), array)
    assert isinstance(array('i'), ints)
    assert not isinstance(array('l'), ints)
    assert list(subtype.origins(ints)) == [array]
