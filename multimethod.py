import collections
import functools
import inspect
import types

try:
    from future_builtins import map, zip
except ImportError:
    import typing

__version__ = '1.1'


def get_types(func):
    """Return evaluated type hints in order."""
    if not hasattr(func, '__annotations__'):
        return ()
    annotations = dict(typing.get_type_hints(func))
    annotations.pop('return', None)
    params = inspect.signature(func).parameters
    return tuple(annotations.pop(name, object) for name in params if annotations)


class DispatchError(TypeError):
    pass


class signature(tuple):
    """A tuple of types that supports partial ordering."""

    def __le__(self, other):
        return len(self) <= len(other) and all(map(issubclass, other, self))

    def __lt__(self, other):
        return self != other and self <= other

    def __sub__(self, other):
        """Return relative distances, assuming self >= other."""
        return [
            left.mro().index(right if right in left.mro() else object)
            for left, right in zip(self, other)
        ]


class multimethod(dict):
    """A callable directed acyclic graph of methods."""

    def __new__(cls, func, strict=False):
        namespace = inspect.currentframe().f_back.f_locals
        self = functools.update_wrapper(dict.__new__(cls), func)
        self.strict, self.pending = bool(strict), set()
        return namespace.get(func.__name__, self)

    def __init__(self, func, strict=False):
        try:
            self[get_types(func)] = func
        except NameError:
            self.pending.add(func)

    def register(self, func):
        """Decorator for registering function."""
        self.__init__(func)
        return self if self.__name__ == func.__name__ else func

    def __get__(self, instance, owner):
        return self if instance is None else types.MethodType(self, instance)

    def parents(self, types):
        """Find immediate parents of potential key."""
        parents = {key for key in self if isinstance(key, signature) and key < types}
        return parents - {ancestor for parent in parents for ancestor in parent.parents}

    def clean(self):
        """Empty the cache."""
        for key in list(self):
            if not isinstance(key, signature):
                dict.__delitem__(self, key)

    def __setitem__(self, types, func):
        self.clean()
        types = signature(types)
        parents = types.parents = self.parents(types)
        for key in self:
            if types < key and (not parents or parents & key.parents):
                key.parents -= parents
                key.parents.add(types)
        dict.__setitem__(self, types, func)

    def __delitem__(self, types):
        self.clean()
        dict.__delitem__(self, types)
        for key in self:
            if types in key.parents:
                key.parents = self.parents(key)

    def __missing__(self, types):
        """Find and cache the next applicable method of given types."""
        self.evaluate()
        if types in self:
            return self[types]
        keys = self.parents(types)
        if len(keys) == 1 if self.strict else keys:
            return self.setdefault(types, self[min(keys, key=signature(types).__sub__)])
        raise DispatchError("{}{}: {} methods found".format(self.__name__, types, len(keys)))

    def __call__(self, *args, **kwargs):
        """Resolve and dispatch to best method."""
        return self[tuple(map(type, args))](*args, **kwargs)

    def evaluate(self):
        """Evaluate any pending forward references.

        It is recommended to call this explicitly when using forward references,
        otherwise cache misses will be forced to evaluate.
        """
        while self.pending:
            func = self.pending.pop()
            self[get_types(func)] = func


class multidispatch(multimethod):
    def register(self, *types):
        """Return a decorator for registering in the style of `functools.singledispatch`."""
        return lambda func: self.__setitem__(types, func) or func


def isa(*types):
    """Partially bound `isinstance`."""
    return lambda arg: isinstance(arg, types)


class overload(collections.OrderedDict):
    """Ordered functions which dispatch based on their annotated predicates."""

    __get__ = multimethod.__get__
    register = multimethod.register

    def __new__(cls, func):
        namespace = inspect.currentframe().f_back.f_locals
        self = functools.update_wrapper(super().__new__(cls), func)
        return namespace.get(func.__name__, self)

    def __init__(self, func):
        self[inspect.signature(func)] = func

    def __call__(self, *args, **kwargs):
        """Dispatch to first matching function."""
        for sig, func in reversed(self.items()):
            arguments = sig.bind(*args, **kwargs).arguments
            if all(predicate(arguments[name]) for name, predicate in func.__annotations__.items()):
                return func(*args, **kwargs)
        raise DispatchError("No matching functions found")


class multimeta(type):
    """Convert all callables in namespace to multimethods"""

    class multidict(dict):
        def __setitem__(self, key, value):
            curr = self.get(key, None)

            if callable(value):
                if callable(curr) and hasattr(curr, 'register'):
                    value = curr.register(value)
                else:
                    value = multimethod(value)

            dict.__setitem__(self, key, value)

    @classmethod
    def __prepare__(mcs, name, bases):
        return mcs.multidict()
