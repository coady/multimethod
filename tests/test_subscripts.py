import asyncio
import inspect
import sys
import typing
from array import array
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Generic, Literal, TypeVar, Union

import pytest

from multimethod import DispatchError, multimethod, parametric, subtype


def matches(instance, cls):
    origins = tuple(subtype.origins(cls)) or cls
    return isinstance(instance, cls) and issubclass(type(instance), origins)


def test_literals():
    assert issubclass(subtype(Literal["a", "b"]), str)
    assert not issubclass(subtype(Literal["a"]), subtype(list[int]))
    assert issubclass(Literal[[0]], subtype(Iterable[int]))
    tp = subtype(Literal["a", 0])
    assert matches("a", tp)
    assert matches(0, tp)
    assert not issubclass(Literal["a", 0.0], tp)
    assert not issubclass(tuple[str, int], tp)
    assert issubclass(tp, subtype(str | int))

    @multimethod
    def func(arg: Literal["a", 0]):
        return arg

    assert func(0) == 0
    with pytest.raises(DispatchError):
        func(1)
    with pytest.raises(DispatchError):
        func(0.0)


def test_union():
    if sys.version_info < (3, 14):
        assert issubclass(int, subtype(Union[int, float]))
    assert issubclass(int, subtype(int | float))
    assert issubclass(subtype(int | float), subtype(int | float | None))
    assert subtype(Iterable | Mapping | Sequence) is Iterable
    assert not issubclass(Union, subtype(type[int]))
    assert matches(bool, subtype(type[int] | type[float]))
    assert matches(bool | float, subtype(type[int | float]))

    # Test nested subtype with UnionType base
    tp = subtype(int | float)
    assert subtype(tp) is tp
    assert tp is not type(int | float)


@pytest.mark.skipif(sys.version_info < (3, 12), reason="Type aliases added in 3.12")
def test_type_alias():
    Point = typing.TypeAliasType(name="Point", value=tuple[int, int])
    assert matches((0, 0), subtype(Point))


def test_type():
    @multimethod
    def func(arg: type[list]): ...

    @func.register
    def _(arg: type[list[str]]):
        return str

    assert func(list) is func(list[int]) is None
    assert func(list[str]) is str
    assert not matches([], subtype(type[list]))
    with pytest.raises(DispatchError):
        func(tuple)
    with pytest.raises(DispatchError):
        func(list | tuple)


def test_new():
    Str = typing.NewType("", str)
    assert subtype(Str) is str
    tp = subtype(type[Str])
    assert typing.NewType in subtype.origins(tp)
    assert not matches(str, tp)
    assert matches(Str, tp)
    assert matches(typing.NewType("", Str), tp)
    assert not matches(typing.NewType("", str), tp)
    assert matches(Str, subtype(Literal[Str]))


def test_generic():
    class cls(Generic[TypeVar("T")]): ...

    @multimethod
    def func(_: cls[int]): ...

    @func.register
    def _(_: cls):
        return Generic

    @func.register
    def _(_: type[cls[int]]):
        return int

    @func.register
    def _(_: type[cls]):
        return type

    assert func(cls[int]()) is None
    assert func(cls()) is Generic
    assert func(cls[int]) is int
    assert func(cls) is type


def test_tuple():
    assert subtype(tuple) is tuple
    assert not issubclass(tuple[int], subtype(tuple[()]))
    assert not matches(tuple[int], subtype(type[tuple[()]]))
    assert matches((), subtype(tuple[()]))
    assert not matches((0,), subtype(tuple[()]))
    assert issubclass(tuple[int], subtype(tuple[int, ...]))
    assert issubclass(tuple[bool, ...], subtype(tuple[int, ...]))
    assert matches(tuple[int], subtype(type[tuple[int, ...]]))
    assert not issubclass(tuple[int, float], subtype(tuple[int, ...]))


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

    def h(arg: float) -> bool: ...

    @multimethod
    def func(arg: Callable[[bool], bool]):
        return arg.__name__

    @func.register
    def _(arg: Callable[..., bool]):
        return ...

    @func.register
    def _(arg: int):
        return "int"

    @func.register
    def _(arg: Sequence[Callable[[bool], bool]]):
        return arg[0].__name__ + "0"

    with pytest.raises(DispatchError):
        func(f)
    assert func(g) == "g"
    assert func([g]) == "g0"
    assert func(h) is ...
    assert issubclass(Callable[[int], int], subtype(Callable[..., int]))
    assert not issubclass(Callable[..., int], subtype(Callable[[int], int]))


def test_final():
    tp = subtype(Iterable[str])
    d = {"": 0}
    assert matches(d, subtype(Mapping[str, int]))
    assert matches(d.keys(), tp)


def test_args():
    tp = type("", (), {"__args__": None})
    assert subtype(tp) is tp
    assert not issubclass(tp, subtype(list[int]))
    assert subtype(typing.Callable) is Callable


@pytest.mark.benchmark
def test_parametric():
    coro = parametric(Callable, inspect.iscoroutinefunction)
    assert issubclass(coro, Callable)
    assert not issubclass(Callable, coro)
    assert not issubclass(parametric(object, inspect.iscoroutinefunction), coro)
    assert matches(asyncio.sleep, coro)
    assert not matches(lambda: None, coro)
    assert list(subtype.origins(coro)) == [Callable]

    ints = parametric(array, typecode="i")
    assert issubclass(ints, array)
    assert not issubclass(array, ints)
    sized = parametric(array, itemsize=4)
    assert issubclass(sized & ints, ints)
    assert not issubclass(ints, sized & ints)
    assert not issubclass(parametric(object, typecode="i"), array)
    assert matches(array("i"), ints)
    assert not matches(array("l"), ints)
    assert list(subtype.origins(ints)) == [array]
