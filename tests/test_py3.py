import pytest
from multimethod import multimethod, DispatchError


@multimethod
def annotated(x: int, y: float, z=None):
    return x * y


def test_annotations():
    with pytest.raises(DispatchError):
        annotated(0, 0)
    assert annotated(1, 2.0) == 2
