import sys
import pytest
from multimethod import multimethod, DispatchError
type_hints = sys.version_info >= (3, 5)


class cls:
    @multimethod
    def method(x: object, y: int, z=None):
        return y

    if type_hints:
        @multimethod
        def method(x: 'cls', y: int):
            return type(x)


def test_annotations():
    obj = cls()
    with pytest.raises(DispatchError):
        obj.method(0.0)
    assert cls.method(None, 0) == 0
    assert obj.method(0) == (cls if type_hints else 0)
