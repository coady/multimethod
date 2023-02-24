import pytest

from multimethod import signature


def test_signature():
    with pytest.raises(TypeError):
        signature([list]) <= signature([None])
