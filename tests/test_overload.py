import pytest
from multimethod import DispatchError, isa, overload


def test_overloads():
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
