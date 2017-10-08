import sys
import types
try:
    from future_builtins import map, zip
except ImportError:
    pass
try:
    from typing import get_type_hints
except ImportError:  # pragma: no cover
    def get_type_hints(func):
        return func.__annotations__

__version__ = '0.6'


def get_types(func):
    """Return evaluated type hints in order."""
    annotations = get_type_hints(func)
    return tuple(map(annotations.__getitem__, func.__code__.co_varnames[:len(annotations)]))


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
        return [left.__mro__.index(right if right in left.__mro__ else object) for left, right in zip(self, other)]


class multimethod(dict):
    """A callable directed acyclic graph of methods."""
    @classmethod
    def new(cls, name='', strict=False):
        """Explicitly create a new multimethod.  Assign to local name in order to use decorator."""
        self = dict.__new__(cls)
        self.__name__, self.strict, self.pending = name, strict, set()
        return self

    def __new__(cls, *types):
        """Return a decorator which will add the function."""
        namespace = sys._getframe(1).f_locals

        def decorator(func):
            if isinstance(func, cls):
                self, func = func, func.last
            else:
                self = namespace.get(func.__name__, cls.new(func.__name__))
            self[types] = self.last = func
            return self
        if not (len(types) == 1 and hasattr(types[0], '__annotations__')):
            return decorator
        func, = types
        self = namespace.get(func.__name__, cls.new(func.__name__))
        try:
            self[get_types(func)] = self.last = func
        except NameError:
            self.pending.add(func)
        return self

    def __init__(self, *types):
        dict.__init__(self)

    def __get__(self, instance, owner):
        self.evaluate()
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
        keys = self.parents(types)
        if (len(keys) == 1 if self.strict else keys):
            return self.setdefault(types, self[min(keys, key=signature(types).__sub__)])
        raise DispatchError("{}{}: {} methods found".format(self.__name__, types, len(keys)))

    def __call__(self, *args, **kwargs):
        """Resolve and dispatch to best method."""
        return self[tuple(map(type, args))](*args, **kwargs)

    def register(self, *types):
        """A decorator for registering in the style of singledispatch."""
        return lambda func: self.__setitem__(types, func) or func

    def evaluate(self):
        """Evaluate any pending forward references.

        It is recommended to call this explicly when using forward references,
        otherwise cache misses will be forced to evaluate.
        """
        while self.pending:
            func = self.pending.pop()
            self[get_types(func)] = func


def multidispatch(func):
    """A decorator which creates a new multimethod from a base function in the style of singledispatch."""
    mm = multimethod.new(func.__name__)
    mm[()] = func
    return mm
