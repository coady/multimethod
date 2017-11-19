import sys
import pytest
from multimethod import isa, multimethod, overload, DispatchError
type_hints = sys.version_info >= (3, 5)
skip34 = pytest.mark.skipif(not type_hints, reason="requires Python >=3.5")


class cls:
    @multimethod
    def method(x: object, y: int) -> tuple:
        result = object, int
        return result

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


def test_register():
    @multimethod
    def func(x):
        pass

    @func.register
    def func(x: int):
        pass

    @func.register
    def _(y: float):
        pass
    assert func(0) is func(0.0) is None
    set(func) == {(), (int,), (float,)}


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
