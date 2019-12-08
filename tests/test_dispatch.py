from collections.abc import Iterable
import pytest
from multimethod import multidispatch, signature, DispatchError


def test_signature():
    with pytest.raises(TypeError):
        signature([list]) <= signature([None])


# roshambo
rock, paper, scissors = (type('', (), {}) for _ in range(3))


@multidispatch
def roshambo(left, right):
    return 'tie'


@roshambo.register(scissors, rock)
@roshambo.register(rock, scissors)
def _(left, right):
    return 'rock smashes scissors'


@roshambo.register(paper, scissors)
@roshambo.register(scissors, paper)
def _(left, right):
    return 'scissors cut paper'


@roshambo.register(rock, paper)
@roshambo.register(paper, rock)
def _(left, right):
    return 'paper covers rock'


def test_roshambo():
    assert roshambo.__name__ == 'roshambo'
    r, p, s = rock(), paper(), scissors()
    assert len(roshambo) == 7
    assert roshambo(r, p) == 'paper covers rock'
    assert roshambo(p, r) == 'paper covers rock'
    assert roshambo(r, s) == 'rock smashes scissors'
    assert roshambo(p, s) == 'scissors cut paper'
    assert roshambo(r, r) == 'tie'
    assert len(roshambo) == 8
    del roshambo[()]
    del roshambo[rock, paper]
    assert len(roshambo) == 5
    with pytest.raises(DispatchError, match="0 methods"):
        roshambo(r, r)


# methods
class cls(object):
    method = multidispatch(lambda self, other: None)

    @method.register(Iterable, object)
    def _(self, other):
        return 'left'

    @method.register(object, Iterable)
    def _(self, other):
        return 'right'


def test_cls():
    obj = cls()
    assert obj.method(None) is cls.method(None, None) is None
    assert obj.method('') == 'right'
    assert cls.method('', None) == 'left'
    with pytest.raises(DispatchError, match="2 methods"):
        cls.method('', '')
    cls.method[object, Iterable] = cls.method[Iterable, object]
    assert cls.method('', '') == 'left'
