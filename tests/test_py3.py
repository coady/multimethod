import sys
import pytest
from multimethod import multimethod, DispatchError
type_hints = sys.version_info >= (3, 5)


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
