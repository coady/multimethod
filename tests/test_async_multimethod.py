import asyncio
import inspect
import pytest
from unittest.mock import patch
from multimethod import DispatchError, async_multimethod, _called_from_async


class TestBasicDispatch:
    @async_multimethod
    def method(self, x: str):
        return f"sync:{x}"

    @method.register
    async def _(self, x: str):
        await asyncio.sleep(0)
        return f"async:{x}"


def test_basic_sync_async():
    obj = TestBasicDispatch()

    result = obj.method("hello")
    assert result == "sync:hello"
    assert not inspect.iscoroutine(result)

    async def run_async():
        return await obj.method("world")

    result = asyncio.run(run_async())
    assert result == "async:world"


class TestOnlySync:
    @async_multimethod
    def method(self, x: float):
        return f"only_sync:{x}"


def test_only_sync():
    obj = TestOnlySync()
    result = obj.method(3.14)
    assert result == "only_sync:3.14"
    assert not inspect.iscoroutine(result)


class TestOnlyASync:
    @async_multimethod
    async def method(self, x: float):
        await asyncio.sleep(0)
        return f"only_async:{x}"


def test_only_async():
    obj = TestOnlyASync()

    async def run():
        return await obj.method(3.14)

    result = asyncio.run(run())
    assert not inspect.iscoroutine(result)


class TestOverloadTypes:
    @async_multimethod
    def process(self, x: str):
        return f"sync_str:{x}"

    @async_multimethod
    def process(self, x: int):
        return f"sync_int:{x}"

    @process.register
    async def _(self, x: str):
        await asyncio.sleep(0)
        return f"async_str:{x}"

    @process.register
    async def _(self, x: int):
        await asyncio.sleep(0)
        return f"async_int:{x}"


def test_overload_types():
    obj = TestOverloadTypes()

    # Sync
    assert obj.process("a") == "sync_str:a"
    assert obj.process(1) == "sync_int:1"

    # Async
    async def run():
        r1 = await obj.process("b")
        r2 = await obj.process(2)
        return r1, r2

    r1, r2 = asyncio.run(run())
    assert r1 == "async_str:b"
    assert r2 == "async_int:2"


class TestStaticmethod:
    @async_multimethod
    def method(x: str):
        return f"sync_static:{x}"

    @method.register
    async def _(x: str):
        await asyncio.sleep(0)
        return f"async_static:{x}"

    method = staticmethod(method)


def test_staticmethod():
    # Sync
    assert TestStaticmethod.method("sync") == "sync_static:sync"

    # Async
    async def run():
        return await TestStaticmethod.method("async")

    assert asyncio.run(run()) == "async_static:async"


class TestFallback:
    @async_multimethod
    def func(self, x: int):
        return "int"

    @func.register
    async def _(self, x: str):
        return "str"


class TestSyncMethods:
    @async_multimethod
    def method(self, name: str):
        return f"sync:{name}"

    @method.register
    def _(self):
        return "sync"


def test_sync_methods_assignment():
    obj = TestSyncMethods()
    result = obj.method("test")
    assert result == "sync:test", "Expected the sync method to handle the input correctly"

    result_no_args = obj.method()
    assert result_no_args == "sync", "Expected the no-arg sync method to be called correctly"


def test_fallback_and_error():
    obj = TestFallback()

    assert obj.func(1) == "int"

    async def run_str():
        return await obj.func("a")

    assert asyncio.run(run_str()) == "str"

    with pytest.raises(DispatchError):
        obj.func(3.14)

    with pytest.raises(DispatchError):

        async def run_float():
            return await obj.func(3.14)

        asyncio.run(run_float())


def test_register_with_types():
    @async_multimethod
    def func(x: str):
        return "sync_str"

    @func.register
    async def _(x: str):
        await asyncio.sleep(0)
        return "async_str"

    # Sync
    assert func("test") == "sync_str"

    # Async
    async def run():
        return await func("test")

    assert asyncio.run(run()) == "async_str"


class TestAsyncioRunDirect:
    @async_multimethod
    def method(self, x: str):
        return f"sync_direct:{x}"

    @method.register
    async def _(self, x: str):
        await asyncio.sleep(0)
        return f"async_direct:{x}"


def test_asyncio_run_direct():
    obj = TestAsyncioRunDirect()

    assert obj.method("ok") == "sync_direct:ok"

    async def _call():
        return await obj.method("async_ok")

    assert asyncio.run(_call()) == "async_direct:async_ok"


class TestKwargs:
    @async_multimethod
    def method(self, x: str, y: int = 10):
        return f"sync:x={x},y={y}"

    @method.register
    async def _(self, x: str, y: int = 20):
        await asyncio.sleep(0)
        return f"async:x={x},y={y}"


def test_kwargs():
    obj = TestKwargs()

    # Sync
    assert obj.method("a") == "sync:x=a,y=10"
    assert obj.method("b", 5) == "sync:x=b,y=5"

    # Async
    async def run():
        r1 = await obj.method("c")
        r2 = await obj.method("d", 7)
        return r1, r2

    r1, r2 = asyncio.run(run())
    assert r1 == "async:x=c,y=20"
    assert r2 == "async:x=d,y=7"


class TestDispatchErrorCases:
    @async_multimethod
    def method(self, x: int):
        return f"sync:{x}"

    @method.register
    async def _(self, x: str):
        return f"async:{x}"


def test_dispatch_error_sync():
    obj = TestDispatchErrorCases()

    with pytest.raises(DispatchError, match="no sync method found"):
        obj.method("test")


def test_dispatch_error_async():
    obj = TestDispatchErrorCases()

    async def run():
        return await obj.method(42)

    with pytest.raises(DispatchError, match="no async method found"):
        asyncio.run(run())


def test_called_from_async():
    sync_result = _called_from_async(2)
    assert sync_result is False, (
        "Expected _called_from_async to return False when called from a sync context"
    )


def test_called_from_async_raises_exceptions():
    # Patch sys._getframe to raise ValueError
    with patch("sys._getframe", side_effect=ValueError):
        result = _called_from_async()

        assert result is False, (
            "Expected _called_from_async to return False when sys._getframe raises an exception"
        )
