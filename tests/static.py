"""Fixture for static analysis."""

from multimethod import multidispatch


class cls:
    @multidispatch
    def method(self) -> int:
        return 0


reveal_type(cls().method())  # noqa: F821
