import types

import pytest

from multimethod import multimethod


@pytest.mark.parametrize("annotation", ["Deferred", "namespace.Deferred"])
def test_failed_forward_reference_can_be_retried(annotation, monkeypatch):
    def method(value):
        return value + 1

    method.__annotations__ = {"value": annotation}
    namespace = types.SimpleNamespace()
    monkeypatch.setitem(method.__globals__, "namespace", namespace)
    dispatch = multimethod(method)

    for _ in range(2):
        with pytest.raises((NameError, AttributeError)):
            dispatch(1)
        assert method in dispatch.pending

    monkeypatch.setitem(method.__globals__, "Deferred", int)
    namespace.Deferred = int
    assert dispatch(1) == 2
    assert dispatch[int,] is method
    assert not dispatch.pending
