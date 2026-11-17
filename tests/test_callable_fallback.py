import typing
from collections.abc import Callable

import pytest

from multimethod import multidispatch, multimethod, subtype


@pytest.mark.parametrize("plain", [Callable, typing.Callable])
@pytest.mark.parametrize("specialized", [Callable[[int], str], Callable[..., str]])
def test_bare_callable_is_not_a_specialized_subtype(plain, specialized):
    assert not issubclass(subtype(plain), subtype(specialized))
    assert issubclass(subtype(specialized), subtype(plain))


@pytest.mark.parametrize("decorator", [multimethod, multidispatch])
@pytest.mark.parametrize("plain", [Callable, typing.Callable])
@pytest.mark.parametrize("generic_first", [False, True])
def test_callable_fallback_with_specialized_dispatch(decorator, plain, generic_first):
    def default(value):
        return "default"

    def fallback(value: plain):
        return "fallback"

    def specialized(value: Callable[[int], str]):
        return "specialized"

    route = decorator(default)
    registrations = [fallback, specialized] if generic_first else [specialized, fallback]
    for implementation in registrations:
        route.register(implementation)

    def matches(value: int) -> str:
        return str(value)

    def does_not_match(value: int) -> int:
        return value

    assert route(matches) == "specialized"
    assert route(does_not_match) == "fallback"
    assert route(42) == "default"
