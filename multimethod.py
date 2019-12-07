import collections
import functools
import inspect
import itertools
import types
import warnings

typing = None
try:
    from future_builtins import map, zip
    from collections import Iterable, Iterator, Mapping
except ImportError:
    import typing
    from collections.abc import Iterable, Iterator, Mapping

__version__ = '1.2'


def groupby(func, values):
    """Return mapping of key function to values."""
    groups = collections.defaultdict(list)
    for value in values:
        groups[func(value)].append(value)
    return groups


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


class subtype(type):
    """A normalized generic type which checks subscripts."""

    def __new__(cls, tp, *args):
        if typing is None:
            return tp
        if tp is typing.Any or isinstance(tp, typing.TypeVar):
            return object
        origin = getattr(tp, '__extra__', getattr(tp, '__origin__', tp))
        args = tuple(map(cls, getattr(tp, '__args__', None) or args))
        if set(args) <= {object} and not (origin is tuple and args):
            return origin
        bases = (origin,) if isinstance(origin, type) else ()
        namespace = {'__origin__': origin, '__args__': args}
        return type.__new__(cls, str(tp), bases, namespace)

    def __init__(self, tp, *args):
        pass

    def __getstate__(self):
        return self.__origin__, self.__args__

    def __eq__(self, other):
        return isinstance(other, subtype) and self.__getstate__() == other.__getstate__()

    def __hash__(self):
        return hash(self.__getstate__())

    def __subclasscheck__(self, subclass):
        origin = getattr(subclass, '__extra__', getattr(subclass, '__origin__', subclass))
        args = getattr(subclass, '__args__', ())
        if origin is typing.Union:
            return all(issubclass(cls, self) for cls in args)
        if self.__origin__ is typing.Union:
            return issubclass(subclass, self.__args__)
        return (
            issubclass(origin, self.__origin__)
            and len(args) == len(self.__args__)
            and all(map(issubclass, args, self.__args__))
        )


class signature(tuple):
    """A tuple of types that supports partial ordering."""

    def __new__(cls, types):
        return tuple.__new__(cls, map(subtype, types))

    def __le__(self, other):
        return len(self) <= len(other) and all(map(issubclass, other, self))

    def __lt__(self, other):
        return self != other and self <= other

    def __sub__(self, other):
        """Return relative distances, assuming self >= other."""
        mros = (subclass.mro() for subclass in self)
        return tuple(mro.index(cls if cls in mro else object) for mro, cls in zip(mros, other))


class multimethod(dict):
    """A callable directed acyclic graph of methods."""

    def __new__(cls, func, strict=None):
        namespace = inspect.currentframe().f_back.f_locals
        self = functools.update_wrapper(dict.__new__(cls), func)
        self.pending = set()
        self.get_type = type  # default type checker
        return namespace.get(func.__name__, self)

    def __init__(self, func, strict=None):
        try:
            self[get_types(func)] = func
        except NameError:
            self.pending.add(func)
        if strict is not None:
            self.strict = strict

    def strict(*args):
        warnings.warn("no longer in use; dispatch resolution is strict", DeprecationWarning)

    strict = property(fset=strict)

    def register(self, *args):
        """Decorator for registering a function.

        Optionally call with types to return a decorator for unannotated functions.
        """
        if len(args) == 1 and hasattr(args[0], '__annotations__'):
            return overload.register(self, *args)
        return lambda func: self.__setitem__(args, func) or func

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
        if any(isinstance(cls, subtype) for cls in types):
            self.get_type = get_type  # switch to slower generic type checker
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
        groups = groupby(signature(types).__sub__, self.parents(types))
        keys = groups[min(groups)] if groups else []
        funcs = {self[key] for key in keys}
        if len(funcs) == 1:
            return self.setdefault(types, *funcs)
        raise DispatchError("{}: {} methods found".format(self.__name__, len(keys)), types, keys)

    def __call__(self, *args, **kwargs):
        """Resolve and dispatch to best method."""
        return self[tuple(map(self.get_type, args))](*args, **kwargs)

    def evaluate(self):
        """Evaluate any pending forward references.

        It is recommended to call this explicitly when using forward references,
        otherwise cache misses will be forced to evaluate.
        """
        while self.pending:
            func = self.pending.pop()
            self[get_types(func)] = func


class multidispatch(multimethod):
    """Provisional wrapper for future compatibility with `functools.singledispatch`."""


get_type = multimethod(type)
get_type.__doc__ = """Return a generic `subtype` which checks subscripts."""
get_type.register(Iterator)(type)


@get_type.register(tuple)
def _(arg):
    """Return generic type checking all values."""
    return subtype(type(arg), *map(get_type, arg))


@get_type.register(Mapping)
def _(arg):
    """Return generic type checking first item."""
    return subtype(type(arg), *map(get_type, next(iter(arg.items()), ())))


@get_type.register(Iterable)
def _(arg):
    """Return generic type checking first value."""
    return subtype(type(arg), *map(get_type, itertools.islice(arg, 1)))


def isa(*types):
    """Partially bound `isinstance`."""
    return lambda arg: isinstance(arg, types)


class overload(collections.OrderedDict):
    """Ordered functions which dispatch based on their annotated predicates."""

    __get__ = multimethod.__get__

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

    def register(self, func):
        """Decorator for registering a function."""
        self.__init__(func)
        return self if self.__name__ == func.__name__ else func


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
