import pytest
from typing import Literal, Optional
from multimethod import DispatchError, isa, overload


def test_predicates():
    @overload
    def func(x):
        return x

    @overload
    def func(x: isa(int, float)):
        return -x

    @func.register
    def _(x: isa(str)) -> str:
        return x.upper()

    assert func(None) is None
    assert func(1) == -1
    assert func('hi') == 'HI'
    with pytest.raises(DispatchError):
        func('', None)
    del func[next(iter(func))]
    with pytest.raises(DispatchError):
        func(None)


def test_signatures():
    @overload
    def func(a: int, c: str = ''):
        return 1

    @overload
    def func(a: int, b: int, c: str = ''):
        return 2

    assert func(0) == func(a=0) == 1
    assert func(0, 1) == func(0, b=1) == func(a=0, b=0) == 2


def test_generic():
    pred = isa(list[int], Literal[0.0])
    assert pred([0])
    assert not pred([0.0])
    assert pred(0.0)
    assert not pred(1.0)

    @overload
    def func(arg: Optional[str]):
        return arg

    assert func('') == ''
    assert func(None) is None
    with pytest.raises(DispatchError):
        func(0)


class cls:
    @overload
    def method(self: 'cls'):
        return type(self)


def test_annotations():
    assert cls().method() is cls
